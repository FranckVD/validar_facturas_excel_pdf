import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Callable
import pandas as pd
import PyPDF2
from pdf2image import convert_from_path
import pytesseract

# CONFIGURACIÓN DE RUTAS (Ajustar según instalación)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Tesseract
TESSERACT_PATH = r"F:\teseract\tesseract.exe"
if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# Poppler (Carpeta bin)
# Se busca automáticamente en el proyecto o se usa una ruta fija
POPPLER_PATH = os.path.join(BASE_DIR, "poppler-26.02.0", "Library", "bin")

# MODELOS DE DATOS
@dataclass
class CompraRecord:
    """Registro de compra desde Excel."""
    nro_recepcion: str
    fecha_recepcion: str
    proveedor: str
    almacen: str
    monto: float


@dataclass
class InformacionFactura:
    """Información extraída de una factura PDF."""
    nit: Optional[str] = None
    razon_social: Optional[str] = None
    monto: Optional[float] = None


@dataclass
class ValidacionResult:
    """Resultado de validación de un registro."""
    nro_recepcion: str
    fecha_recepcion: str
    proveedor: str
    almacen: str
    monto_excel: float
    monto_facturas: float
    cantidad_facturas: int
    estado: str  # CORRECTO, DIFERENCIA_MONTO, ERROR, SIN_FACTURAS
    observaciones: str

    def to_dict(self) -> Dict:
        """Convierte el resultado a diccionario."""
        return {
            "nro_recepcion": self.nro_recepcion,
            "fecha_recepcion": self.fecha_recepcion,
            "proveedor": self.proveedor,
            "almacen": self.almacen,
            "monto_excel": self.monto_excel,
            "monto_facturas": self.monto_facturas,
            "cantidad_facturas": self.cantidad_facturas,
            "estado": self.estado,
            "observaciones": self.observaciones,
        }

# EXTRACTOR DE PDFS
class ExtractorPDF:
    """Extrae información de facturas en PDF."""

    def __init__(self, log_callback=None):
        self.log = log_callback or print

    def extraer_texto(self, ruta_pdf: str) -> str:
        """Extrae texto del PDF usando PyPDF2 o OCR si es necesario."""
        texto = ""
        try:
            with open(ruta_pdf, "rb") as f:
                lector = PyPDF2.PdfReader(f)
                for pagina in lector.pages:
                    texto += (pagina.extract_text() or "") + "\n"

            if len(texto.strip()) < 50:
                self.log(f"  📷 Aplicando OCR a {os.path.basename(ruta_pdf)}…")
                texto = self._extraer_con_ocr(ruta_pdf)
        except Exception as e:
            self.log(f"  ⚠️  Error PDF digital, usando OCR: {e}")
            texto = self._extraer_con_ocr(ruta_pdf)
        return texto

    def _extraer_con_ocr(self, ruta_pdf: str) -> str:
        """Extrae texto usando Tesseract OCR."""
        texto = ""
        try:
            # Intentar convertir PDF a imágenes
            try:
                # Usar POPPLER_PATH si está configurado y existe
                kwargs = {"dpi": 300}
                if os.path.exists(POPPLER_PATH):
                    kwargs["poppler_path"] = POPPLER_PATH
                
                imagenes = convert_from_path(ruta_pdf, **kwargs)
            except Exception as e:
                if "poppler" in str(e).lower():
                    self.log(f"  ❌ Error: Poppler no detectado en {POPPLER_PATH}. Verifica la instalación.")
                else:
                    self.log(f"  ❌ Error al convertir PDF a imagen: {e}")
                return ""

            # Aplicar OCR a cada imagen
            for i, imagen in enumerate(imagenes):
                try:
                    # Intentar con español, si falla intentar con inglés
                    try:
                        texto_pag = pytesseract.image_to_string(imagen, lang="spa")
                    except Exception as e:
                        if "spa" in str(e):
                            self.log("  ⚠️ Idioma español (spa) no encontrado en Tesseract, usando inglés (eng)...")
                            texto_pag = pytesseract.image_to_string(imagen, lang="eng")
                        else:
                            raise e
                    
                    texto += texto_pag + "\n"
                    
                    # # DEBUG: Genera y guarda texto extraído para análisis de como extrae los datos el OCR
                    # with open("debug_ocr.txt", "a", encoding="utf-8") as f:
                    #     f.write(f"--- DEBUG OCR: {os.path.basename(ruta_pdf)} (Pág {i+1}) ---\n")
                    #     f.write(texto_pag)
                    #     f.write("\n\n")

                except Exception as e:
                    if "tesseract" in str(e).lower() or "not found" in str(e).lower():
                        self.log(f"  ❌ Error: Tesseract no encontrado en {TESSERACT_PATH}.")
                        return ""
                    else:
                        self.log(f"  ❌ Error en procesamiento OCR: {e}")
                        raise e
        except Exception as e:
            self.log(f"  ❌ Error inesperado en OCR: {e}")
        return texto

    def extraer_informacion(self, texto: str) -> InformacionFactura:
        """Extrae NIT, razón social y monto del texto con múltiples estrategias."""
        info = InformacionFactura()

        # 1. EXTRACCIÓN DE NIT
        for patron in [
            r"NIT/CI/CEX[:\s]+(\d+)", r"N\.I\.T\.?[:\s]+(\d+)",
            r"Número de NIT[:\s]+(\d+)", r"NIT\s+(\d+)",
        ]:
            m = re.search(patron, texto, re.IGNORECASE)
            if m:
                info.nit = m.group(1).strip()
                break

        # 2. EXTRACCIÓN DE RAZÓN SOCIAL
        for patron in [
            r"Razón Social[:\s]+([^\n]+)", r"Señor\(es\)[:\s]+([^\n]+)",
            r"Cliente[:\s]+([^\n]+)", r"A favor de[:\s]+([^\n]+)",
            r"Nombre[:\s]+([^\n]+)",
        ]:
            m = re.search(patron, texto, re.IGNORECASE)
            if m:
                info.razon_social = m.group(1).strip()
                break

        # 3. EXTRACCIÓN DE MONTO (Estrategia de proximidad y palabras clave)
        # Limpiar texto para facilitar búsqueda
        texto_limpio = texto.replace("—", "").replace("_", "")
        
        # Estrategia A: Regex específicas (horizontales - Lo que funcionaba antes)
        for patron in [
            r"TOTAL[:\s]+Bs\.?\s*([\d,\.]+)",
            r"TOTAL GENERAL Bs\.[:\s]+Bs\.?\s*([\d,\.]+)",
            r"Total a pagar[:\s]+Bs\.?\s*([\d,\.]+)",
            r"Importe total[:\s]+Bs\.?\s*([\d,\.]+)",
            r"Monto total[:\s]+Bs\.?\s*([\d,\.]+)",
            r"TOTAL\s+Bs\.?\s*([\d,\.]+)",
            r"Total[:\s]+\$\s*([\d,\.]+)",
            r"TOTAL[:\s]+\$\s*([\d,\.]+)",
            r"(?<!SUB)(?<!\w)TOTAL\b[^\d\n]{0,15}(\d{1,7}[.,]\d{2})\b",
            r"TOTAL\s*\n\s*(\d{1,7}[.,]\d{2})\b",
            r"MONTO A PAGAR Bs\s*[:\s]*([\d,\.]+)",
            r"TOTAL Bs\s*[:\s]*([\d,\.]+)",
            r"SUBTOTAL Bs\s*[:\s]*([\d,\.]+)",
        ]:
            m = re.search(patron, texto, re.IGNORECASE)
            if m:
                val = self._parse_monto(m.group(1))
                if val > 0:
                    info.monto = val
                    break

        # Estrategia B: Búsqueda de palabra clave + primer número siguiente (Vertical/OCR)
        if not info.monto:
            keywords = ["MONTO A PAGAR", "TOTAL Bs", "TOTAL A PAGAR", "SUBTOTAL Bs", "TOTAL"]
            for kw in keywords:
                idx = texto_limpio.upper().find(kw.upper())
                if idx != -1:
                    fragmento = texto_limpio[idx:idx+250]
                    numeros = re.findall(r"(\d{1,7}[.,]\d{2})\b", fragmento)
                    if numeros:
                        val = self._parse_monto(numeros[-1])
                        if val > 0:
                            info.monto = val
                            break

        # Estrategia C: Monto Literal (Ej: "Son: Doscientos...")
        if not info.monto:
            m_literal = re.search(r"Son:\s*([^\n\r]+)", texto, re.IGNORECASE)
            if m_literal:
                texto_monto = m_literal.group(1).upper()
                # Extraer centavos si existen (XX/100)
                m_centavos = re.search(r"(\d+)/100", texto_monto)
                centavos = float(m_centavos.group(1))/100 if m_centavos else 0.0
                
                monto_letra = self._letras_a_numero(texto_monto)
                if monto_letra > 0:
                    info.monto = monto_letra + centavos

        # Estrategia D: El número más grande cerca del final
        if not info.monto:
            numeros = re.findall(r"(\d{1,7}[.,]\d{2})\b", texto_limpio)
            if numeros:
                for n in reversed(numeros[-3:]):
                    val = self._parse_monto(n)
                    if val > 1:
                        info.monto = val
                        break

        return info

    def _letras_a_numero(self, texto: str) -> float:
        """Convierte montos en palabras a número (Estrategia básica)."""
        unidades = {"CERO":0, "UN":1, "UNA":1, "DOS":2, "TRES":3, "CUATRO":4, "CINCO":5, "SEIS":6, "SIETE":7, "OCHO":8, "NUEVE":9, "DIEZ":10, "ONCE":11, "DOCE":12, "TRECE":13, "CATORCE":14, "QUINCE":15, "DIECISEIS":16, "DIECISIETE":17, "DIECIOCHO":18, "DIECINUEVE":19, "VEINTE":20, "VEINTIUN":21, "VEINTIDOS":22, "VEINTITRES":23, "VEINTICUATRO":24, "VEINTICINCO":25, "VEINTISEIS":26, "VEINTISIETE":27, "VEINTIOCHO":28, "VEINTINUEVE":29, "TREINTA":30, "CUARENTA":40, "CINCUENTA":50, "SESENTA":60, "SETENTA":70, "OCHENTA":80, "NOVENTA":90}
        decenas = {"DIEZ":10, "VEINTE":20, "TREINTA":30, "CUARENTA":40, "CINCUENTA":50, "SESENTA":60, "SETENTA":70, "OCHENTA":80, "NOVENTA":90}
        centenas = {"CIEN":100, "CIENTO":100, "DOSCIENTOS":200, "TRESCIENTOS":300, "CUATROCIENTOS":400, "QUINIENTOS":500, "SEISCIENTOS":600, "SETECIENTOS":700, "OCHOCIENTOS":800, "NOVECIENTOS":900}
        
        total = 0
        actual = 0
        palabras = re.findall(r"[A-Z]+", texto)
        
        for p in palabras:
            if p in centenas: actual += centenas[p]
            elif p in decenas: actual += decenas[p]
            elif p in unidades: actual += unidades[p]
            elif p == "MIL":
                if actual == 0: actual = 1
                total += actual * 1000
                actual = 0
            elif p == "Y": continue
            elif p == "BOLIVIANOS": break
            
        return float(total + actual)

    def _parse_monto(self, monto_str: str) -> float:
        """Limpia y convierte un string a float de forma segura."""
        try:
            # Manejar formatos como 1.234,56 o 1,234.56
            s = monto_str.strip()
            if "," in s and "." in s:
                # Si tiene ambos, el último es el decimal
                if s.rfind(",") > s.rfind("."):
                    s = s.replace(".", "").replace(",", ".")
                else:
                    s = s.replace(",", "")
            elif "," in s:
                # Si solo tiene coma, depende del contexto, pero usualmente es decimal en facturas
                s = s.replace(",", ".")
            
            return float(s)
        except:
            return 0.0

# VALIDADOR DE FACTURAS
class ValidadorFacturas:
    """Valida facturas PDF contra registros Excel."""

    def __init__(self, nit_empresa: str, razon_social_empresa: str, log_callback=None):
        self.nit_empresa = nit_empresa.strip()
        self.razon_social_empresa = razon_social_empresa.strip().upper()
        self.log = log_callback or print
        self.extractor = ExtractorPDF(log_callback=self.log)

    def validar_factura(self, info: InformacionFactura, nombre_archivo: str) -> dict:
        """Valida información extraída de una factura priorizando el NIT."""
        problemas = []
        nit_valido = False
        rs_valida = False

        # 1. Validar NIT (Prioridad máxima)
        if info.nit:
            if info.nit == self.nit_empresa:
                nit_valido = True
            else:
                problemas.append(f"NIT incorrecto: {info.nit}")
        else:
            problemas.append("No se encontró NIT")

        # 2. Validar Razón Social (Secundario si el NIT es correcto)
        if info.razon_social:
            # Buscamos si los primeros 10 caracteres de la empresa están en la factura
            # o viceversa, para permitir variaciones menores
            rs_buscada = self.razon_social_empresa[:12].strip()
            if rs_buscada in info.razon_social.upper() or info.razon_social.upper() in self.razon_social_empresa:
                rs_valida = True
            else:
                problemas.append(f"Razón social difiere: {info.razon_social}")
        else:
            problemas.append("No se encontró razón social")

        if not info.monto:
            problemas.append("No se encontró monto total")

        # LÓGICA DE DECISIÓN:
        # Si el NIT es correcto y hay monto, se considera válido aunque la RS varíe.
        es_valida = (nit_valido and info.monto) or (rs_valida and info.monto)
        
        # Si el NIT es correcto pero la RS falló, lo dejamos como aviso pero no bloqueamos el "CORRECTO"
        problemas_criticos = [p for p in problemas if "NIT incorrecto" in p or "monto" in p]
        
        if nit_valido and not rs_valida:
            # Es un aviso, no un error crítico
            pass

        return {
            "archivo": nombre_archivo,
            "nit": info.nit,
            "razon_social": info.razon_social,
            "monto": info.monto or 0,
            "problemas": problemas if not es_valida else [p for p in problemas if "monto" in p],
            "es_valida": es_valida,
            "avisos": [p for p in problemas if "Razón social" in p] if nit_valido else []
        }

    def procesar_registro(
        self,
        registro: pd.Series,
        pdfs_disponibles: List[Path],
        nro_fila: int,
        total_filas: int,
        progress_callback: Optional[Callable] = None,
    ) -> ValidacionResult:
        """Procesa un registro de compra y sus facturas asociadas."""
        nro_recepcion = str(registro["nro_recepcion"]).strip()
        monto_excel = float(registro["monto"])

        self.log(f"\n📄  [{nro_fila}/{total_filas}] {nro_recepcion}  —  Bs. {monto_excel:.2f}")

        if progress_callback:
            progress_callback(nro_fila / total_filas, f"Procesando {nro_recepcion}…")

        # Buscar PDFs relacionados
        pdfs_rel = [p for p in pdfs_disponibles if nro_recepcion in p.stem]

        if not pdfs_rel:
            self.log("  ⚠️  Sin facturas")
            return ValidacionResult(
                nro_recepcion=nro_recepcion,
                fecha_recepcion=registro.get("fecha_recepcion", ""),
                proveedor=registro.get("proveedor", ""),
                almacen=registro.get("almacen", ""),
                monto_excel=monto_excel,
                monto_facturas=0,
                cantidad_facturas=0,
                estado="SIN_FACTURAS",
                observaciones="No se encontraron facturas",
            )

        self.log(f"  📑  {len(pdfs_rel)} factura(s)")
        total_facturas = 0
        problemas_generales = []
        avisos_generales = []

        for pdf in pdfs_rel:
            self.log(f"  🔎  {pdf.name}")
            texto = self.extractor.extraer_texto(str(pdf))
            info = self.extractor.extraer_informacion(texto)
            validacion = self.validar_factura(info, pdf.name)

            if validacion["monto"]:
                total_facturas += validacion["monto"]
                self.log(f"    💰  Bs. {validacion['monto']:.2f}")

            if validacion["problemas"]:
                problemas_generales.extend(
                    [f"{pdf.name}: {p}" for p in validacion["problemas"]]
                )
            
            if validacion.get("avisos"):
                avisos_generales.extend(
                    [f"{pdf.name}: {p}" for p in validacion["avisos"]]
                )

        diferencia = abs(total_facturas - monto_excel)

        if problemas_generales:
            estado = "ERROR"
        elif diferencia > 1:
            estado = "DIFERENCIA_MONTO"
            problemas_generales.append(
                f"Excel Bs.{monto_excel:.2f} vs Facturas Bs.{total_facturas:.2f}"
            )
        else:
            estado = "CORRECTO"

        # Combinar avisos en las observaciones si el estado es CORRECTO
        obs = "OK"
        if problemas_generales:
            obs = " | ".join(problemas_generales)
        elif avisos_generales:
            obs = "⚠️ " + " | ".join(avisos_generales)

        self.log(f"  ✓  Total facturas: Bs. {total_facturas:.2f}  →  {estado}")

        return ValidacionResult(
            nro_recepcion=nro_recepcion,
            fecha_recepcion=registro.get("fecha_recepcion", ""),
            proveedor=registro.get("proveedor", ""),
            almacen=registro.get("almacen", ""),
            monto_excel=monto_excel,
            monto_facturas=total_facturas,
            cantidad_facturas=len(pdfs_rel),
            estado=estado,
            observaciones=obs,
        )

    def procesar_todo(
        self,
        ruta_excel: str,
        carpeta_pdfs: str,
        ruta_reporte: str,
        progress_callback: Optional[Callable] = None,
    ) -> List[ValidacionResult]:
        """Procesa todos los registros y genera reporte."""
        self.log("\n" + "═" * 55)
        self.log("🔍  VALIDADOR DE FACTURAS — INICIO")
        self.log("═" * 55)

        self.log(f"\n📊  Cargando Excel: {ruta_excel}")
        try:
            df_excel = pd.read_excel(ruta_excel)
            self.log(f"✅  {len(df_excel)} registros cargados")
        except Exception as e:
            self.log(f"❌  Error al leer Excel: {e}")
            return []

        self.log(f"\n📁  Buscando PDFs en: {carpeta_pdfs}")
        archivos_pdf = list(Path(carpeta_pdfs).glob("*.pdf"))
        self.log(f"✅  {len(archivos_pdf)} archivos PDF encontrados")

        resultados = []
        total = len(df_excel)

        for fila, (_, registro) in enumerate(df_excel.iterrows(), start=1):
            resultado = self.procesar_registro(
                registro,
                archivos_pdf,
                fila,
                total,
                progress_callback,
            )
            resultados.append(resultado)

        # Guardar reporte
        self.log(f"\n📝  Guardando reporte: {ruta_reporte}")
        df_res = pd.DataFrame([r.to_dict() for r in resultados])
        df_res.to_excel(ruta_reporte, index=False)

        # Resumen
        correctos = len([r for r in resultados if r.estado == "CORRECTO"])
        diferencias = len([r for r in resultados if r.estado == "DIFERENCIA_MONTO"])
        errores = len([r for r in resultados if r.estado == "ERROR"])
        sin_fact = len([r for r in resultados if r.estado == "SIN_FACTURAS"])

        self.log("\n" + "═" * 55)
        self.log("📊  RESUMEN FINAL")
        self.log("═" * 55)
        self.log(f"  ✅  Correctos:        {correctos}")
        self.log(f"  ⚠️   Diferencias:      {diferencias}")
        self.log(f"  ❌  Errores:          {errores}")
        self.log(f"  📄  Sin facturas:     {sin_fact}")
        self.log(f"\n✅  Reporte guardado en: {ruta_reporte}")
        self.log("═" * 55)

        return resultados
