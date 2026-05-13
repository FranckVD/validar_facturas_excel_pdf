# 📋 Validador de Facturas PDF vs Excel

**Solución integral para la validación de registros contables mediante OCR y análisis de datos.**

Esta aplicación de escritorio optimiza los procesos de auditoría contable, permitiendo cruzar automáticamente la información de archivos **Excel** con facturas en formato **PDF** (digitales y escaneadas), garantizando la integridad de los datos de facturación.

---

## 🚀 Características Principales

*   **Doble Motor de Extracción:** Soporte nativo para PDFs digitales y motor **OCR (Tesseract)** para facturas escaneadas o fotos.
*   **Validación Inteligente:** Verificación cruzada de NIT, Razón Social y Montos Totales.
*   **Lógica de Priorización:** Validación prioritaria por NIT para mitigar errores de lectura en nombres largos o complejos.
*   **Conversión Literal:** Capacidad de extraer montos a partir del texto (ej. "Son: Doscientos 00/100...").
*   **Interfaz Moderna:** GUI intuitiva basada en `CustomTkinter` con modo oscuro y feedback en tiempo real.
*   **Reportes Detallados:** Generación automática de informes en Excel con estados de validación y observaciones.

---

## 🛠️ Requisitos e Instalación

### 1. Clonación e Instalación de Dependencias
Este proyecto utiliza [uv](https://github.com/astral-sh/uv) para una gestión de dependencias ultrarrápida y reproducible.

1.  **Instalar uv** (si no lo tienes):
    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral-sh.github.io/install.ps1 | iex"
    ```
2.  **Sincronizar el proyecto**:
    Navega a la carpeta del proyecto y ejecuta el siguiente comando. Esto creará automáticamente un entorno virtual (`.venv`) e instalará todas las librerías necesarias con las versiones exactas:
    ```bash
    uv sync
    ```

### 2. Configuración Inicial de Datos
Para que la aplicación funcione, asegúrate de contar con la siguiente estructura de archivos (se incluyen plantillas vacías en el repositorio):

*   **`registros_compras.xlsx`**: Tu archivo de Excel con los datos a validar.
*   **`Facturas/`**: Carpeta donde debes colocar tus archivos PDF.
*   **`reporte_validacion.xlsx`**: El archivo donde se volcarán los resultados finales.

### 3. Dependencias Externas (Críticas)
Para habilitar el soporte OCR y la conversión de imágenes, es imperativo configurar:

1.  **Poppler:** Motor de renderizado PDF.
    *   Descarga: [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases)
    *   *Nota: El proyecto está configurado para buscarlo en una carpeta local. Verifica la ruta `POPPLER_PATH` en `backend.py`.*
2.  **Tesseract OCR:** Motor de reconocimiento de texto.
    *   Descarga: [Tesseract Installer](https://github.com/UB-Mannheim/tesseract/wiki)
    *   **Importante:** Durante la instalación, en el apartado de "Additional language data", selecciona **Spanish** para descargar el soporte de idioma español (`spa.traineddata`).
    *   *Nota: Verifica la ruta `TESSERACT_PATH` en `backend.py` según tu carpeta de instalación.*

    ![Idioma Español Tesseract](/image/image-6.png)

---

## 📖 Guía de Operación

### 1. Configuración de la Empresa
Ingrese el **NIT** y la **Razón Social** oficial. El sistema utilizará estos datos como base para validar la legitimidad de las facturas recibidas.

### 2. Gestión de Archivos
*   **Registro de Compras:** Archivo Excel (registro_compras.xlsx) con las columnas base (nro_recepcion, monto, etc.).

    ![Archivo de Registro de Compras](/image/image-1.png)

*   **Repositorio PDF:** Carpeta que contiene los documentos digitales a validar.
    *   **⚠️ Importante:** El nombre de cada archivo PDF debe contener el **código de recepción** (columna `nro_recepcion` del Excel) para que el sistema pueda vincular correctamente la factura con su registro.

    ![Carpeta donde Almacenar las Facturas](/image/image-2.png)

*   **Destino del Reporte:** Ruta donde se exportará el análisis final, por defecto se llama (reporte_validacion.xlsx).

    ![Archivo de Reporte Validado](/image/image-3.png)

### 3. Ejecución y Monitoreo
*   **▶ Iniciar:** Ejecuta el algoritmo de validación. La barra de progreso indicará el avance en tiempo real.
*   **⏹ Detener:** Interrupción segura del proceso.
*   **📊 Estadísticas:** Resumen dinámico de estados: **Correctos**, **Diferencias**, **Errores** y **Faltantes**.

    ![Vista Preliminar](/image/image-4.png)

*   **🔄 Reiniciar:** Vuelve los campos vacíos.

    ![Archivo de Registro de Compras](/image/image-5.png)

### 4. Análisis de Resultados
*   **Filtros Inteligentes:** Clasifique resultados por estado para una revisión rápida.
*   **Consola Técnica:** Monitoreo detallado de la extracción. El icono 📷 indica la activación del motor OCR.

---

## 🏗️ Arquitectura del Proyecto

*   `app_main.py`: Punto de entrada de la aplicación.
*   `app_gui_re.py`: Orquestador de la interfaz de usuario y eventos.
*   `backend.py`: Motor lógico (Extracción, Regex, Conversión literal y Validación).
*   `frontend.py`: Definiciones de estilos, paleta de colores y componentes visuales.

---

## 📝 Notas de Versión
*   **Validación Prioritaria:** El sistema prioriza el NIT como identificador único.
*   **Soporte Multilingüe:** OCR optimizado para español con fallback en inglés.
*   **Manejo de Variaciones:** Tolerancia configurable para diferencias mínimas en montos (centavos).

---
*Desarrollado con enfoque en la automatización y eficiencia contable por `FranckVD`.*
