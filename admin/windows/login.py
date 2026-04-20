# =============================================
# windows/login.py — Ventana de Login Admin
# =============================================
# Propósito: Autenticar al administrador con Supabase Auth
# Tabla: auth.users (gestionado por Supabase)
# Operación: signInWithPassword
# =============================================
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import COLORS, FONTS
from supabase_client import get_client, set_auth_token


class LoginWindow(tk.Toplevel):
    """
    Ventana de inicio de sesión para el administrador.
    - Autentica con Supabase Auth (email + contraseña)
    - Bloquea el botón durante la petición para evitar doble envío
    - Muestra errores descriptivos al usuario
    """

    def __init__(self, master, on_success):
        super().__init__(master)
        self.master = master
        self.on_success = on_success

        self.title("Iniciar Sesión — Administración")
        self.geometry("440x520")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.grab_set()   # Modal
        self.focus_set()

        # Centrar sobre la pantalla
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 440) // 2
        y = (self.winfo_screenheight() - 520) // 2
        self.geometry(f"440x520+{x}+{y}")

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        # ---- Encabezado ----
        header = tk.Frame(self, bg=COLORS["sidebar"], height=120)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header, text="🏪", font=("Segoe UI", 36),
            bg=COLORS["sidebar"], fg=COLORS["white"]
        ).pack(pady=(20, 4))
        tk.Label(
            header, text="Panel de Administración",
            font=FONTS["subtitle"], bg=COLORS["sidebar"], fg=COLORS["white"]
        ).pack()

        # ---- Formulario ----
        form = tk.Frame(self, bg=COLORS["bg"], padx=40, pady=30)
        form.pack(fill="both", expand=True)

        # Email
        tk.Label(form, text="Correo electrónico", font=FONTS["body"],
                 bg=COLORS["bg"], fg=COLORS["text"]).pack(anchor="w")
        self.email_var = tk.StringVar()
        self.email_entry = ttk.Entry(form, textvariable=self.email_var,
                                     font=FONTS["body"], width=32)
        self.email_entry.pack(fill="x", pady=(4, 14))
        self.email_entry.focus()

        # Contraseña
        tk.Label(form, text="Contraseña", font=FONTS["body"],
                 bg=COLORS["bg"], fg=COLORS["text"]).pack(anchor="w")
        self.pass_var = tk.StringVar()
        self.pass_entry = ttk.Entry(form, textvariable=self.pass_var,
                                    font=FONTS["body"], width=32, show="•")
        self.pass_entry.pack(fill="x", pady=(4, 6))
        self.pass_entry.bind("<Return>", lambda e: self._login())

        # Mostrar/ocultar contraseña
        self.show_pass = tk.BooleanVar(value=False)
        tk.Checkbutton(
            form, text="Mostrar contraseña", variable=self.show_pass,
            command=self._toggle_password, bg=COLORS["bg"],
            fg=COLORS["text_light"], font=FONTS["small"]
        ).pack(anchor="w", pady=(0, 20))

        # Mensaje de error
        self.error_var = tk.StringVar()
        self.error_label = tk.Label(
            form, textvariable=self.error_var, font=FONTS["small"],
            bg=COLORS["bg"], fg=COLORS["danger"], wraplength=340
        )
        self.error_label.pack(pady=(0, 10))

        # Botón de login
        self.login_btn = tk.Button(
            form, text="Iniciar Sesión", font=FONTS["button"],
            bg=COLORS["primary"], fg=COLORS["white"],
            activebackground=COLORS["primary_dark"],
            relief="flat", cursor="hand2", height=2,
            command=self._login
        )
        self.login_btn.pack(fill="x")

        # Barra de progreso (oculta por defecto)
        self.progress = ttk.Progressbar(form, mode="indeterminate")

    def _toggle_password(self):
        self.pass_entry.config(show="" if self.show_pass.get() else "•")

    def _validate_inputs(self) -> bool:
        """Valida los campos antes de enviar al servidor."""
        email = self.email_var.get().strip()
        password = self.pass_var.get()

        if not email:
            self.error_var.set("El correo es obligatorio.")
            self.email_entry.focus()
            return False
        if "@" not in email or "." not in email:
            self.error_var.set("Introduce un correo electrónico válido.")
            self.email_entry.focus()
            return False
        if not password:
            self.error_var.set("La contraseña es obligatoria.")
            self.pass_entry.focus()
            return False
        if len(password) < 6:
            self.error_var.set("La contraseña debe tener al menos 6 caracteres.")
            self.pass_entry.focus()
            return False

        self.error_var.set("")
        return True

    def _login(self):
        if not self._validate_inputs():
            return

        # Deshabilitar botón y mostrar progreso
        self.login_btn.config(state="disabled", text="Autenticando...")
        self.progress.pack(fill="x", pady=(8, 0))
        self.progress.start(10)

        # Ejecutar en hilo separado para no bloquear la UI
        threading.Thread(target=self._do_login, daemon=True).start()

    def _do_login(self):
        """Realiza la autenticación en un hilo secundario."""
        try:
            supabase = get_client()
            response = supabase.auth.sign_in_with_password({
                "email": self.email_var.get().strip(),
                "password": self.pass_var.get()
            })

            user  = response.user
            token = response.session.access_token

            # Consultar el rol en la tabla users
            email = self.email_var.get().strip()
            user_row = supabase.table("users").select("role").eq("email", email).single().execute()
            role = None
            if user_row and user_row.data and "role" in user_row.data:
                role = user_row.data["role"]

            if role != "admin":
                self.after(0, self._login_error, "Acceso denegado: solo administradores pueden ingresar.")
                return

            # Guardar token para futuras peticiones autenticadas
            set_auth_token(token)

            # Regresar al hilo principal
            self.after(0, self._login_success, user, token)

        except Exception as e:
            error_msg = self._parse_error(str(e))
            self.after(0, self._login_error, error_msg)

    def _login_success(self, user, token):
        self.progress.stop()
        self.progress.pack_forget()
        self.login_btn.config(state="normal", text="Iniciar Sesión")
        self.destroy()
        self.on_success(user, token)

    def _login_error(self, message):
        self.progress.stop()
        self.progress.pack_forget()
        self.login_btn.config(state="normal", text="Iniciar Sesión")
        self.error_var.set(message)

    def _parse_error(self, error: str) -> str:
        """Convierte mensajes de error de Supabase a texto amigable."""
        if "Invalid login credentials" in error:
            return "Correo o contraseña incorrectos."
        if "Email not confirmed" in error:
            return "Debes confirmar tu correo antes de iniciar sesión."
        if "Too many requests" in error:
            return "Demasiados intentos. Espera unos minutos."
        if "network" in error.lower() or "connection" in error.lower():
            return "Error de conexión. Verifica tu internet."
        return f"Error al iniciar sesión: {error}"

    def _on_close(self):
        self.master.destroy()
