import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# =============================================
# main.py — Punto de entrada de la app admin
# =============================================
import tkinter as tk
from tkinter import messagebox
import sys
import os

# Agrega el directorio raíz al path para importaciones
sys.path.insert(0, os.path.dirname(__file__))

from config import WINDOW_WIDTH, WINDOW_HEIGHT, COLORS, FONTS
from windows.login import LoginWindow


class App(tk.Tk):
    """Ventana raíz de la aplicación de administración."""

    def __init__(self):
        super().__init__()
        self.title("Sistema de Gestión de Ventas e Inventario")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(1024, 600)
        self.configure(bg=COLORS["bg"])

        # Centrar ventana en la pantalla
        self._center_window()

        # Guardar datos del usuario autenticado
        self.current_user = None
        self.access_token = None

        # Mostrar pantalla de login primero
        self._show_login()

    def _center_window(self):
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - WINDOW_WIDTH) // 2
        y = (screen_h - WINDOW_HEIGHT) // 2
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")

    def _show_login(self):
        """Muestra la pantalla de login."""
        # Ocultar ventana principal hasta autenticar
        self.withdraw()
        LoginWindow(self, on_success=self._on_login_success)

    def _on_login_success(self, user, token):
        """Callback ejecutado cuando el login es exitoso."""
        from windows.dashboard import DashboardWindow
        self.current_user = user
        self.access_token = token
        self.deiconify()  # Mostrar ventana principal
        DashboardWindow(self)

    def on_closing(self):
        if messagebox.askokcancel("Salir", "¿Deseas cerrar la aplicación?"):
            self.destroy()


if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
