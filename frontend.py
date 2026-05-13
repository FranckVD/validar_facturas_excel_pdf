"""
Frontend: Componentes visuales y estilos.
"""

# TEMA Y CONFIGURACIÓN GLOBAL
import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Paleta personalizada
COLORS = {
    "bg_dark":      "#0D0F14",
    "bg_panel":     "#13161E",
    "bg_card":      "#1A1E2A",
    "bg_input":     "#1F2433",
    "accent":       "#4F9EFF",
    "accent_dim":   "#2D5E9E",
    "success":      "#2DD4A0",
    "warning":      "#F5A623",
    "error":        "#FF5C6E",
    "text_primary": "#E8EBF2",
    "text_muted":   "#6B7590",
    "border":       "#252A3A",
    "border_light": "#2F3650",
}

FONT_TITLE  = ("Segoe UI", 24, "bold")
FONT_HEADER = ("Segoe UI", 15, "bold")
FONT_BODY   = ("Segoe UI", 14)
FONT_SMALL  = ("Segoe UI", 13)
FONT_MONO   = ("Consolas", 13)
