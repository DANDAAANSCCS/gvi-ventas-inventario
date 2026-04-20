# =============================================
# windows/dashboard.py — Panel Principal Admin
# =============================================
# Propósito: Mostrar métricas clave y navegación
# Tablas: orders, products, clients, daily_operations
# Operación: SELECT con agregaciones
# =============================================
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import COLORS, FONTS
from supabase_client import get_client


class DashboardWindow(tk.Frame):
    """
    Panel principal que se monta sobre la ventana raíz.
    Contiene:
    - Barra lateral de navegación
    - Tarjetas de métricas (ventas del día, productos, clientes, stock bajo)
    - Tabla de últimas ventas
    - Accesos rápidos
    """

    MENU_ITEMS = [
        ("🏠  Inicio",           "dashboard"),
        ("📦  Productos",        "products"),
        ("👥  Clientes",         "clients"),
        ("🛒  Ventas",           "sales"),
        ("📊  Inventario",       "inventory"),
        ("📋  Operaciones",      "daily_ops"),
        ("📈  Reportes",         "reports"),
    ]

    def __init__(self, master):
        super().__init__(master, bg=COLORS["bg"])
        self.master = master
        self.pack(fill="both", expand=True)

        self._content_frame = None   # Frame dinámico del contenido
        self._active_btn    = None   # Botón activo en sidebar

        self._build_layout()
        self._show_home()

    # ── Estructura general ──────────────────────────────────────────────────

    def _build_layout(self):
        # Barra lateral izquierda
        self.sidebar = tk.Frame(self, bg=COLORS["sidebar"], width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Zona de contenido
        self.content_area = tk.Frame(self, bg=COLORS["bg"])
        self.content_area.pack(side="left", fill="both", expand=True)

        self._build_sidebar()
        self._build_topbar()

    def _build_sidebar(self):
        # Logo / nombre
        logo_frame = tk.Frame(self.sidebar, bg=COLORS["sidebar"], height=80)
        logo_frame.pack(fill="x")
        logo_frame.pack_propagate(False)
        tk.Label(
            logo_frame, text="🏪 GesVentas",
            font=FONTS["subtitle"], bg=COLORS["sidebar"], fg=COLORS["white"]
        ).pack(expand=True)

        ttk.Separator(self.sidebar, orient="horizontal").pack(fill="x")

        # Botones de navegación
        self._nav_buttons = {}
        for label, key in self.MENU_ITEMS:
            btn = tk.Button(
                self.sidebar, text=label, font=FONTS["body"],
                bg=COLORS["sidebar"], fg=COLORS["white"],
                activebackground=COLORS["sidebar_hover"],
                activeforeground=COLORS["white"],
                relief="flat", anchor="w", padx=20, pady=12,
                cursor="hand2",
                command=lambda k=key: self._navigate(k)
            )
            btn.pack(fill="x")
            self._nav_buttons[key] = btn

        # Botón cerrar sesión al fondo
        tk.Frame(self.sidebar, bg=COLORS["sidebar"]).pack(fill="y", expand=True)
        tk.Button(
            self.sidebar, text="🚪  Cerrar Sesión",
            font=FONTS["body"], bg=COLORS["danger"], fg=COLORS["white"],
            activebackground="#DC2626", relief="flat",
            anchor="w", padx=20, pady=12, cursor="hand2",
            command=self._logout
        ).pack(fill="x", side="bottom", pady=4)

    def _build_topbar(self):
        topbar = tk.Frame(self.content_area, bg=COLORS["white"],
                          height=56, bd=0)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        self.page_title_var = tk.StringVar(value="Panel Principal")
        tk.Label(
            topbar, textvariable=self.page_title_var,
            font=FONTS["title"], bg=COLORS["white"], fg=COLORS["text"]
        ).pack(side="left", padx=20)

        # Usuario autenticado
        user = self.master.current_user
        user_label = user.email if user else "Admin"
        tk.Label(
            topbar, text=f"👤 {user_label}",
            font=FONTS["small"], bg=COLORS["white"], fg=COLORS["text_light"]
        ).pack(side="right", padx=20)

    # ── Navegación ──────────────────────────────────────────────────────────

    def _navigate(self, key: str):
        """Carga el módulo correspondiente al ítem de menú."""
        # Resaltar botón activo
        if self._active_btn:
            self._active_btn.config(bg=COLORS["sidebar"])
        self._active_btn = self._nav_buttons.get(key)
        if self._active_btn:
            self._active_btn.config(bg=COLORS["sidebar_hover"])

        # Destruir contenido anterior
        if self._content_frame:
            self._content_frame.destroy()

        self._content_frame = tk.Frame(self.content_area, bg=COLORS["bg"])
        self._content_frame.pack(fill="both", expand=True, padx=20, pady=16)

        # Importación perezosa para evitar ciclos
        if key == "dashboard":
            self._show_home()
            return
        elif key == "products":
            from windows.products import ProductsFrame
            ProductsFrame(self._content_frame, self.master)
            self.page_title_var.set("Gestión de Productos")
        elif key == "clients":
            from windows.clients import ClientsFrame
            ClientsFrame(self._content_frame, self.master)
            self.page_title_var.set("Gestión de Clientes")
        elif key == "sales":
            from windows.sales import SalesFrame
            SalesFrame(self._content_frame, self.master)
            self.page_title_var.set("Ventas")
        elif key == "inventory":
            from windows.inventory import InventoryFrame
            InventoryFrame(self._content_frame, self.master)
            self.page_title_var.set("Inventario")
        elif key == "daily_ops":
            from windows.daily_ops import DailyOpsFrame
            DailyOpsFrame(self._content_frame, self.master)
            self.page_title_var.set("Operaciones Diarias")
        elif key == "reports":
            from windows.reports import ReportsFrame
            ReportsFrame(self._content_frame, self.master)
            self.page_title_var.set("Reportes")

    def _show_home(self):
        """Muestra las tarjetas de métricas en el dashboard."""
        self.page_title_var.set("Panel Principal")

        if self._content_frame:
            self._content_frame.destroy()

        self._active_btn = self._nav_buttons.get("dashboard")
        if self._active_btn:
            self._active_btn.config(bg=COLORS["sidebar_hover"])

        self._content_frame = tk.Frame(self.content_area, bg=COLORS["bg"])
        self._content_frame.pack(fill="both", expand=True, padx=20, pady=16)

        # Tarjetas de métricas (placeholders con carga asíncrona)
        self.metric_vars = {
            "sales":    tk.StringVar(value="..."),
            "products": tk.StringVar(value="..."),
            "clients":  tk.StringVar(value="..."),
            "low_stock":tk.StringVar(value="..."),
        }
        metrics = [
            ("💰 Ventas Hoy",       self.metric_vars["sales"],    COLORS["primary"]),
            ("📦 Productos",        self.metric_vars["products"], COLORS["success"]),
            ("👥 Clientes",         self.metric_vars["clients"],  COLORS["warning"]),
            ("⚠️ Stock Bajo",       self.metric_vars["low_stock"],COLORS["danger"]),
        ]

        cards_frame = tk.Frame(self._content_frame, bg=COLORS["bg"])
        cards_frame.pack(fill="x", pady=(0, 20))

        for title, var, color in metrics:
            card = tk.Frame(cards_frame, bg=COLORS["card"],
                            relief="flat", bd=0,
                            highlightbackground=COLORS["border"],
                            highlightthickness=1)
            card.pack(side="left", fill="both", expand=True, padx=8)

            tk.Label(card, text=title, font=FONTS["small"],
                     bg=COLORS["card"], fg=COLORS["text_light"]).pack(pady=(14,2))
            tk.Label(card, textvariable=var, font=("Segoe UI", 28, "bold"),
                     bg=COLORS["card"], fg=color).pack(pady=(0, 14))

        # Tabla de últimas ventas
        tk.Label(
            self._content_frame, text="Últimas Ventas",
            font=FONTS["subtitle"], bg=COLORS["bg"], fg=COLORS["text"]
        ).pack(anchor="w", pady=(0,8))

        cols = ("ID", "Cliente", "Total", "Estado", "Fecha")
        self.recent_tree = ttk.Treeview(
            self._content_frame, columns=cols,
            show="headings", height=8
        )
        for col in cols:
            self.recent_tree.heading(col, text=col)
            self.recent_tree.column(col, width=160, anchor="center")
        self.recent_tree.pack(fill="both", expand=True)

        # Cargar datos en hilo secundario
        threading.Thread(target=self._load_metrics, daemon=True).start()

    def _load_metrics(self):
        """Consulta Supabase y actualiza las métricas."""
        try:
            sb = get_client()
            from datetime import date
            today = date.today().isoformat()

            # Ventas del día
            sales_res = sb.table("orders").select("total").eq("status", "completed") \
                .gte("created_at", f"{today}T00:00:00").execute()
            total_sales = sum(r["total"] for r in sales_res.data)

            # Total productos activos
            prod_res = sb.table("products").select("id", count="exact") \
                .eq("active", True).execute()
            total_products = prod_res.count or len(prod_res.data)

            # Total clientes
            cli_res = sb.table("clients").select("id", count="exact").execute()
            total_clients = cli_res.count or len(cli_res.data)

            # Productos con stock bajo (≤ 5)
            low_res = sb.table("products").select("id", count="exact") \
                .lte("stock", 5).eq("active", True).execute()
            low_stock = low_res.count or len(low_res.data)

            # Últimas ventas
            recent_res = sb.table("orders") \
                .select("id, clients(name), total, status, created_at") \
                .order("created_at", desc=True).limit(10).execute()

            self.after(0, self._update_metrics,
                       total_sales, total_products, total_clients,
                       low_stock, recent_res.data)
        except Exception as e:
            self.after(0, lambda: self.metric_vars["sales"].set("Error"))

    def _update_metrics(self, sales, products, clients, low_stock, recent):
        self.metric_vars["sales"].set(f"${sales:,.2f}")
        self.metric_vars["products"].set(str(products))
        self.metric_vars["clients"].set(str(clients))
        self.metric_vars["low_stock"].set(str(low_stock))

        # Poblar tabla de recientes
        for row in self.recent_tree.get_children():
            self.recent_tree.delete(row)
        for r in recent:
            client_name = r.get("clients", {}) or {}
            self.recent_tree.insert("", "end", values=(
                r["id"][:8] + "...",
                client_name.get("name", "N/A"),
                f"${r['total']:,.2f}",
                r["status"],
                r["created_at"][:10]
            ))

    def _logout(self):
        if messagebox.askyesno("Cerrar Sesión", "¿Deseas cerrar sesión?"):
            try:
                get_client().auth.sign_out()
            except Exception:
                pass
            self.pack_forget()
            self.master.withdraw()
            from windows.login import LoginWindow
            LoginWindow(self.master, on_success=lambda u, t: None)
