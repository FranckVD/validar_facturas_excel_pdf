import os
import threading
import queue
from typing import Any, Dict, List

import customtkinter as ctk
from tkinter import filedialog, messagebox

# Importar Backend (lógica de negocio)
from backend import ValidadorFacturas, ValidacionResult, TESSERACT_PATH, POPPLER_PATH

# Importar Frontend (estilos y configuración visual)
from frontend import COLORS, FONT_TITLE, FONT_HEADER, FONT_BODY, FONT_SMALL, FONT_MONO

# WIDGETS PERSONALIZADOS (FRONTEND)
class FileSelectorWidget(ctk.CTkFrame):
    """Selector de archivo/carpeta con icono y botón."""

    def __init__(self, master, label: str, mode: str = "file",
                 filetypes=None, button_text: str = "Cargar", **kwargs):
        super().__init__(master, fg_color=COLORS["bg_card"],
                         corner_radius=10, **kwargs)
        self.mode      = mode
        self.filetypes = filetypes or [("Todos", "*.*")]
        self._var      = ctk.StringVar()

        ctk.CTkLabel(self, text=label, font=FONT_SMALL,
                     text_color=COLORS["text_muted"]).pack(anchor="w", padx=14, pady=(10, 2))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 10))

        icon = "📁" if "Cargar" in button_text else "💾"
        
        self._btn = ctk.CTkButton(
            row, text=icon, width=46, height=42,
            font=("Segoe UI", 16), fg_color=COLORS["accent_dim"],
            hover_color=COLORS["accent"], command=self._browse,
        )
        self._btn.pack(side="right")

        self._entry = ctk.CTkEntry(
            row, textvariable=self._var, font=FONT_MONO,
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"], height=42,
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

    def _browse(self):
        if self.mode == "file":
            path = filedialog.askopenfilename(filetypes=self.filetypes)
        else:
            path = filedialog.askdirectory()
        if path:
            self._var.set(path)

    @property
    def value(self) -> str:
        return self._var.get().strip()

    @value.setter
    def value(self, v: str):
        self._var.set(v)

    def clear(self):
        self._var.set("")


class StatCard(ctk.CTkFrame):
    """Tarjeta de estadística con icono, valor y etiqueta."""

    def __init__(self, master, icon: str, label: str, color: str, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_card"],
                         corner_radius=12, **kwargs)
        self._color = color

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(16, 4))

        self._icon_lbl = ctk.CTkLabel(top, text=icon, font=("Segoe UI", 24),
                                       text_color=color)
        self._icon_lbl.pack(side="left")

        self._val_lbl = ctk.CTkLabel(top, text="—", font=("Segoe UI", 26, "bold"),
                                      text_color=color)
        self._val_lbl.pack(side="right")

        ctk.CTkLabel(self, text=label, font=FONT_SMALL,
                     text_color=COLORS["text_muted"]).pack(anchor="w", padx=16, pady=(0, 14))

    def set_value(self, v):
        self._val_lbl.configure(text=str(v))


class ResultRow(ctk.CTkFrame):
    """Fila de resultado en la tabla de resultados."""

    STATUS_STYLE = {
        "CORRECTO":       (COLORS["success"], "✅"),
        "DIFERENCIA_MONTO": (COLORS["warning"], "⚠️"),
        "ERROR":          (COLORS["error"],   "❌"),
        "SIN_FACTURAS":   (COLORS["text_muted"], "📄"),
    }

    def __init__(self, master, data: Dict, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_card"],
                         corner_radius=8, **kwargs)
        color, icon = self.STATUS_STYLE.get(
            data["estado"], (COLORS["text_muted"], "?"))

        # Barra lateral de color
        indicator = ctk.CTkFrame(self, fg_color=color, width=4, corner_radius=0)
        indicator.pack(side="left", fill="y", padx=(0, 0))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(side="left", fill="both", expand=True, padx=12, pady=10)

        # Línea 1: recepción + estado
        line1 = ctk.CTkFrame(body, fg_color="transparent")
        line1.pack(fill="x")

        ctk.CTkLabel(line1, text=f"{icon}  {data['nro_recepcion']}",
                     font=FONT_HEADER, text_color=COLORS["text_primary"]
                     ).pack(side="left")
        ctk.CTkLabel(line1, text=data["estado"], font=FONT_SMALL,
                     text_color=color).pack(side="right")

        # Línea 2: proveedor
        ctk.CTkLabel(body, text=f"Excel: {data.get('proveedor', '')}",
                     font=FONT_SMALL, text_color=COLORS["text_muted"]
                     ).pack(anchor="w")

        # Línea 3: montos
        monto_excel   = data.get("monto_excel", 0)
        monto_facturas = data.get("monto_facturas", 0)
        diferencia    = monto_facturas - monto_excel

        amounts = ctk.CTkFrame(body, fg_color="transparent")
        amounts.pack(fill="x", pady=(4, 0))

        ctk.CTkLabel(amounts, text=f"Excel: Bs. {monto_excel:,.2f}",
                     font=FONT_SMALL, text_color=COLORS["text_muted"]
                     ).pack(side="left")
        ctk.CTkLabel(amounts, text=f"Facturas: Bs. {monto_facturas:,.2f}",
                     font=FONT_SMALL, text_color=COLORS["text_muted"]
                     ).pack(side="left", padx=20)

        dif_color = COLORS["success"] if abs(diferencia) <= 1 else COLORS["error"]
        ctk.CTkLabel(amounts,
                     text=f"Δ {'+' if diferencia >= 0 else ''}{diferencia:,.2f}",
                     font=FONT_SMALL, text_color=dif_color
                     ).pack(side="right")

        # Línea 4: observaciones (si hay)
        if data.get("observaciones") and data["observaciones"] != "OK":
            ctk.CTkLabel(body, text=data["observaciones"],
                         font=("Segoe UI", 9), text_color=COLORS["error"],
                         wraplength=500, justify="left"
                         ).pack(anchor="w", pady=(2, 0))

# VENTANA PRINCIPAL (FRONTEND + BACKEND ORQUESTACIÓN)
class AppValidador(ctk.CTk):
    """Aplicación principal: validación de facturas."""

    def __init__(self):
        super().__init__()

        self.title("Validador de Facturas")
        self.geometry("1180x780")
        self.minsize(960, 680)
        self.configure(fg_color=COLORS["bg_dark"])

        self._resultados: List[Dict[str, Any]] = []
        self._log_queue  = queue.Queue()
        self._running    = False

        self._build_ui()
        self._poll_log()
        self._check_dependencies()

    def _check_dependencies(self):
        """Verifica si Tesseract y Poppler están configurados correctamente."""
        missing = []
        
        if not os.path.exists(TESSERACT_PATH):
            missing.append(f"Tesseract: {TESSERACT_PATH}")
            self._log_queue.put(f"⚠️  ADVERTENCIA: Tesseract no encontrado en {TESSERACT_PATH}")
            
        if not os.path.exists(POPPLER_PATH):
            missing.append(f"Poppler (bin): {POPPLER_PATH}")
            self._log_queue.put(f"⚠️  ADVERTENCIA: Poppler no encontrado en {POPPLER_PATH}")

        if missing:
            messagebox.showwarning(
                "Dependencias faltantes",
                "No se encontraron las siguientes dependencias:\n\n" + 
                "\n".join(missing) + 
                "\n\nEl OCR no funcionará para facturas escaneadas."
            )
        else:
            self._log_queue.put("✅ Dependencias OCR (Tesseract y Poppler) detectadas.")

    # CONSTRUCCIÓN DE UI

    def _build_ui(self):
        """Construye la interfaz gráfica."""
        # Encabezado
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"],
                              height=64, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="  📋  Validador de Facturas",
            font=FONT_TITLE,
            text_color=COLORS["text_primary"],
        ).pack(side="left", padx=24, pady=16)

        self._status_badge = ctk.CTkLabel(
            header, text="● Listo", font=FONT_SMALL,
            text_color=COLORS["success"],
        )
        self._status_badge.pack(side="right", padx=24)

        # Cuerpo dividido en dos columnas
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=0, pady=0)

        body.columnconfigure(0, weight=0)   # panel izquierdo fijo
        body.columnconfigure(1, weight=1)   # panel derecho flexible
        body.rowconfigure(0, weight=1)

        # Panel izquierdo (configuración)
        left = ctk.CTkFrame(body, fg_color=COLORS["bg_panel"],
                            width=500, corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_propagate(False)
        self._build_left_panel(left)

        # Panel derecho (resultados + log)
        right = ctk.CTkFrame(body, fg_color="transparent", corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        self._build_right_panel(right)

    def _build_left_panel(self, parent):
        """Construye el panel izquierdo (configuración)."""
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=0, pady=0)

        pad = {"padx": 5, "pady": 6}

        # Sección: empresa
        self._section_label(scroll, "🏢  Datos de la Empresa")

        ctk.CTkLabel(scroll, text="NIT de tu empresa",
                     font=FONT_SMALL, text_color=COLORS["text_muted"]
                     ).pack(anchor="w", **pad)
        self._nit_entry = ctk.CTkEntry(
            scroll, placeholder_text="N° de NIT", height=38,
            font=FONT_MONO, fg_color=COLORS["bg_input"],
            border_color=COLORS["border"], text_color=COLORS["text_primary"],
        )
        self._nit_entry.pack(fill="x", **pad)

        ctk.CTkLabel(scroll, text="Razón Social",
                     font=FONT_SMALL, text_color=COLORS["text_muted"]
                     ).pack(anchor="w", **pad)
        self._rs_entry = ctk.CTkEntry(
            scroll, placeholder_text="Nombre de la empresa", height=38,
            font=FONT_BODY, fg_color=COLORS["bg_input"],
            border_color=COLORS["border"], text_color=COLORS["text_primary"],
        )
        self._rs_entry.pack(fill="x", **pad)

        self._sep(scroll)

        # Sección: archivos
        self._section_label(scroll, "📂  Archivos")

        self._excel_sel = FileSelectorWidget(
            scroll, "Registro de compras (.xlsx)",
            mode="file", filetypes=[("Excel", "*.xlsx *.xls")],
        )
        self._excel_sel.pack(fill="x", **pad)

        self._pdf_sel = FileSelectorWidget(
            scroll, "Carpeta de facturas PDF",
            mode="folder",
        )
        self._pdf_sel.pack(fill="x", **pad)

        self._report_sel = FileSelectorWidget(
            scroll, "Guardar reporte en…",
            mode="file", filetypes=[("Excel", "*.xlsx")],
            button_text="Destino",
        )
        self._report_sel.pack(fill="x", **pad)
        self._report_sel.value = "reporte_validacion.xlsx"

        self._sep(scroll)

        # Tolerancia de monto
        self._section_label(scroll, "⚙️  Opciones")

        ctk.CTkLabel(scroll, text="Tolerancia de diferencia (Bs.)",
                     font=FONT_SMALL, text_color=COLORS["text_muted"]
                     ).pack(anchor="w", **pad)
        self._tol_entry = ctk.CTkEntry(
            scroll, placeholder_text="1.00", height=36,
            font=FONT_MONO, fg_color=COLORS["bg_input"],
            border_color=COLORS["border"], text_color=COLORS["text_primary"],
            width=120,
        )
        self._tol_entry.insert(0, "1.00")
        self._tol_entry.pack(anchor="w", **pad)

        self._sep(scroll)

        # Botones de control
        self._run_btn = ctk.CTkButton(
            scroll,
            text="▶  Iniciar Validación",
            height=44, font=("Segoe UI", 14, "bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dim"],
            command=self._start_validation,
            anchor="w",
        )
        self._run_btn.pack(fill="x", padx=5, pady=(6, 4))

        self._stop_btn = ctk.CTkButton(
            scroll,
            text="⏹  Detener",
            height=44, font=FONT_SMALL,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["error"],
            state="disabled",
            command=self._stop_validation,
            anchor="w",
        )
        self._stop_btn.pack(fill="x", padx=5, pady=(6, 4))

        self._export_btn = ctk.CTkButton(
            scroll,
            text="📤  Abrir Reporte Excel",
            height=44, font=FONT_SMALL,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["success"],
            state="disabled",
            command=self._open_report,
            anchor="w",
        )
        self._export_btn.pack(fill="x", padx=5, pady=(6, 4))

        self._reset_btn = ctk.CTkButton(
            scroll,
            text="🔄  Reiniciar Todo",
            height=44, font=FONT_SMALL,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["border_light"],
            state="disabled",
            command=self._reset_app,
            anchor="w",
        )
        self._reset_btn.pack(fill="x", padx=5, pady=(0, 16))

        # Barra de progreso
        ctk.CTkLabel(scroll, text="Progreso", font=FONT_SMALL,
                     text_color=COLORS["text_muted"]
                     ).pack(anchor="w", padx=12)
        self._progress_bar = ctk.CTkProgressBar(
            scroll, height=10,
            fg_color=COLORS["bg_card"],
            progress_color=COLORS["accent"],
        )
        self._progress_bar.set(0)
        self._progress_bar.pack(fill="x", padx=12, pady=(2, 4))

        self._progress_lbl = ctk.CTkLabel(
            scroll, text="", font=FONT_SMALL,
            text_color=COLORS["text_muted"],
        )
        self._progress_lbl.pack(anchor="w", padx=12, pady=(0, 16))

    def _build_right_panel(self, parent):
        """Construye el panel derecho (resultados)."""
        # Tarjetas resumen
        cards_row = ctk.CTkFrame(parent, fg_color="transparent")
        cards_row.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        cards_row.columnconfigure((0, 1, 2, 3), weight=1)

        self._card_ok   = StatCard(cards_row, "✅", "Correctos",   COLORS["success"])
        self._card_dif  = StatCard(cards_row, "⚠️", "Diferencias", COLORS["warning"])
        self._card_err  = StatCard(cards_row, "❌", "Errores",     COLORS["error"])
        self._card_sf   = StatCard(cards_row, "📄", "Sin facturas", COLORS["text_muted"])

        self._card_ok.grid(row=0, column=0, padx=4, sticky="ew")
        self._card_dif.grid(row=0, column=1, padx=4, sticky="ew")
        self._card_err.grid(row=0, column=2, padx=4, sticky="ew")
        self._card_sf.grid(row=0, column=3, padx=4, sticky="ew")

        # Tabs: Resultados / Consola
        self._tabview = ctk.CTkTabview(
            parent,
            fg_color=COLORS["bg_panel"],
            segmented_button_fg_color=COLORS["bg_card"],
            segmented_button_selected_color=COLORS["accent"],
            segmented_button_unselected_color=COLORS["bg_card"],
            segmented_button_selected_hover_color=COLORS["accent_dim"],
        )
        self._tabview.grid(row=1, column=0, sticky="nsew",
                           padx=16, pady=(0, 14))

        tab_res  = self._tabview.add("  Resultados  ")
        tab_log  = self._tabview.add("  Consola  ")

        # Tab Resultados
        filter_bar = ctk.CTkFrame(tab_res, fg_color="transparent")
        filter_bar.pack(fill="x", padx=4, pady=(8, 4))

        ctk.CTkLabel(filter_bar, text="Filtrar:",
                     font=FONT_SMALL, text_color=COLORS["text_muted"]
                     ).pack(side="left", padx=(4, 8))

        self._filter_var = ctk.StringVar(value="TODOS")
        filters = [("Todos", "TODOS"), ("✅ Correctos", "CORRECTO"),
                   ("⚠️ Diferencias", "DIFERENCIA_MONTO"),
                   ("❌ Errores", "ERROR"), ("📄 Sin facturas", "SIN_FACTURAS")]

        for label, value in filters:
            ctk.CTkButton(
                filter_bar, text=label, width=110, height=28,
                font=FONT_SMALL, fg_color=COLORS["bg_card"],
                hover_color=COLORS["accent_dim"],
                command=lambda v=value: self._apply_filter(v),
            ).pack(side="left", padx=2)

        # Buscador
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._render_results())
        search_entry = ctk.CTkEntry(
            filter_bar, textvariable=self._search_var,
            placeholder_text="🔍  Buscar…",
            width=180, height=28, font=FONT_SMALL,
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        search_entry.pack(side="right", padx=4)

        self._results_scroll = ctk.CTkScrollableFrame(
            tab_res, fg_color="transparent",
        )
        self._results_scroll.pack(fill="both", expand=True, padx=4, pady=4)

        self._empty_lbl = ctk.CTkLabel(
            self._results_scroll,
            text="Aún no hay resultados.\nConfigura los parámetros y presiona Iniciar Validación.",
            font=FONT_BODY, text_color=COLORS["text_muted"],
        )
        self._empty_lbl.pack(pady=80)

        # Tab Consola
        self._console = ctk.CTkTextbox(
            tab_log, font=FONT_MONO,
            fg_color=COLORS["bg_dark"],
            text_color=COLORS["text_primary"],
            wrap="none", state="disabled",
        )
        self._console.pack(fill="both", expand=True, padx=4, pady=4)

        btn_clear = ctk.CTkButton(
            tab_log, text="Limpiar consola", height=28,
            font=FONT_SMALL, fg_color=COLORS["bg_card"],
            hover_color=COLORS["border_light"],
            command=self._clear_console,
        )
        btn_clear.pack(anchor="e", padx=6, pady=(0, 4))

    # HELPERS DE UI
    def _section_label(self, parent, text: str):
        """Crea una etiqueta de sección."""
        ctk.CTkLabel(
            parent, text=text,
            font=("Segoe UI", 11, "bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w", padx=18, pady=(14, 2))

    def _sep(self, parent):
        """Crea un separador visual."""
        ctk.CTkFrame(parent, fg_color=COLORS["border"],
                     height=1, corner_radius=0
                     ).pack(fill="x", padx=18, pady=10)

    # LÓGICA DE VALIDACIÓN (ORQUESTACIÓN BACKEND)
    def _start_validation(self):
        """Inicia el proceso de validación en un hilo separado."""
        nit = self._nit_entry.get().strip()
        rs  = self._rs_entry.get().strip()
        excel = self._excel_sel.value
        pdfs  = self._pdf_sel.value
        report = self._report_sel.value or "reporte_validacion.xlsx"

        if not nit or not rs:
            messagebox.showwarning("Faltan datos", "Ingresa NIT y Razón Social.")
            return
        if not excel or not os.path.isfile(excel):
            messagebox.showwarning("Archivo inválido", "Selecciona el archivo Excel.")
            return
        if not pdfs or not os.path.isdir(pdfs):
            messagebox.showwarning("Carpeta inválida", "Selecciona la carpeta de PDFs.")
            return

        self._running = True
        self._resultados = []
        self._run_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._export_btn.configure(state="disabled")
        self._status_badge.configure(text="● Procesando…", text_color=COLORS["warning"])
        self._progress_bar.set(0)
        self._progress_lbl.configure(text="")
        self._clear_console()
        self._clear_results()

        def worker():
            """Ejecuta la validación en segundo plano."""
            def log(msg):
                self._log_queue.put(msg)

            def progress(val, msg):
                if not self._running:
                    raise InterruptedError("Detenido por el usuario")
                self.after(0, lambda: self._progress_bar.set(val))
                self.after(0, lambda: self._progress_lbl.configure(text=msg))

            validador = ValidadorFacturas(nit, rs, log_callback=log)
            try:
                resultados = validador.procesar_todo(
                    excel, pdfs, report, progress_callback=progress
                )
                # Convertir a diccionarios para la visualización
                self._resultados = [
                    r.to_dict() if isinstance(r, ValidacionResult) else r
                    for r in resultados
                ]
                self.after(0, self._on_done)
            except InterruptedError:
                log("\n⛔  Proceso detenido por el usuario.")
                self.after(0, self._on_stopped)
            except Exception as e:
                log(f"\n❌  Error inesperado: {e}")
                self.after(0, self._on_stopped)

        threading.Thread(target=worker, daemon=True).start()

    def _stop_validation(self):
        """Detiene el proceso de validación."""
        self._running = False

    def _on_done(self):
        """Callback cuando la validación termina exitosamente."""
        self._running = False
        self._run_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._export_btn.configure(state="normal")
        self._reset_btn.configure(state="normal")
        self._status_badge.configure(text="● Completado", text_color=COLORS["success"])
        self._progress_bar.set(1)
        self._progress_lbl.configure(text="Validación completada")
        self._update_cards()
        self._apply_filter("TODOS")

    def _on_stopped(self):
        """Callback cuando el proceso se detiene."""
        self._running = False
        self._run_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._status_badge.configure(text="● Detenido", text_color=COLORS["error"])

    # GESTIÓN DE CONSOLA
    def _poll_log(self):
        """Drena la cola de log cada 100ms."""
        try:
            while True:
                msg = self._log_queue.get_nowait()
                self._console.configure(state="normal")
                self._console.insert("end", msg + "\n")
                self._console.see("end")
                self._console.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._poll_log)

    def _clear_console(self):
        """Limpia la consola."""
        self._console.configure(state="normal")
        self._console.delete("1.0", "end")
        self._console.configure(state="disabled")

    # GESTIÓN DE RESULTADOS
    def _update_cards(self):
        """Actualiza las tarjetas de estadísticas."""
        ok   = sum(1 for r in self._resultados if r["estado"] == "CORRECTO")
        dif  = sum(1 for r in self._resultados if r["estado"] == "DIFERENCIA_MONTO")
        err  = sum(1 for r in self._resultados if r["estado"] == "ERROR")
        sf   = sum(1 for r in self._resultados if r["estado"] == "SIN_FACTURAS")
        self._card_ok.set_value(ok)
        self._card_dif.set_value(dif)
        self._card_err.set_value(err)
        self._card_sf.set_value(sf)

    def _apply_filter(self, estado: str):
        """Aplica un filtro a los resultados."""
        self._filter_var.set(estado)
        self._render_results()

    def _render_results(self):
        """Renderiza los resultados filtrados y buscados."""
        estado    = self._filter_var.get()
        search    = self._search_var.get().strip().lower()

        filtered = [
            r for r in self._resultados
            if (estado == "TODOS" or r["estado"] == estado)
            and (not search or search in r["nro_recepcion"].lower()
                 or search in str(r.get("proveedor", "")).lower())
        ]

        self._clear_results()

        if not filtered:
            lbl = ctk.CTkLabel(
                self._results_scroll,
                text="Sin resultados para este filtro.",
                font=FONT_BODY, text_color=COLORS["text_muted"],
            )
            lbl.pack(pady=40)
            return

        for data in filtered:
            row = ResultRow(self._results_scroll, data)
            row.pack(fill="x", pady=3, padx=2)

    def _clear_results(self):
        """Limpia los resultados mostrados."""
        for widget in self._results_scroll.winfo_children():
            widget.destroy()

    # UTILIDADES
    def _open_report(self):
        """Abre el reporte Excel generado."""
        report = self._report_sel.value or "reporte_validacion.xlsx"
        if os.path.isfile(report):
            os.startfile(report)
        else:
            messagebox.showinfo("Reporte", f"Archivo no encontrado:\n{report}")

    def _reset_app(self):
        """Limpia todos los campos, resultados y consola."""
        if self._running:
            messagebox.showwarning("Proceso en curso", "Detén la validación antes de reiniciar.")
            return

        self._nit_entry.delete(0, "end")
        self._rs_entry.delete(0, "end")
        self._excel_sel.clear()
        self._pdf_sel.clear()
        self._report_sel.value = "reporte_validacion.xlsx"
        
        self._resultados = []
        self._clear_results()
        self._update_cards()
        self._clear_console()
        
        self._progress_bar.set(0)
        self._progress_lbl.configure(text="")
        
        self._status_badge.configure(text="● Listo", text_color=COLORS["success"])
        self._export_btn.configure(state="disabled")
        self._reset_btn.configure(state="disabled")
        self._run_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        
        messagebox.showinfo("Reiniciado", "Todos los campos y resultados han sido limpiados.")

# PUNTO DE ENTRADA
if __name__ == "__main__":
    app = AppValidador()
    app.mainloop()
