# =============================================
# windows/reports.py — Reportes y Estadísticas
# =============================================
# Propósito: Generar reportes de ventas, inventario y clientes
# Tablas: orders, order_items, products, clients
# Operaciones: SELECT con filtros de fecha
# =============================================
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from datetime import date, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import COLORS, FONTS
from supabase_client import get_client

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


class ReportsFrame(tk.Frame):
    """
    Módulo de Reportes.
    - Reporte de ventas por rango de fechas
    - Productos más vendidos
    - Estado del inventario
    - Gráfica de ventas diarias (requiere matplotlib)
    """

    def __init__(self, master, app):
        super().__init__(master, bg=COLORS["bg"])
        self.app = app
        self.pack(fill="both", expand=True)
        self._build_ui()

    def _build_ui(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        sales_tab = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(sales_tab, text="  💰 Ventas  ")
        self._build_sales_report(sales_tab)

        top_prod_tab = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(top_prod_tab, text="  🏆 Top Productos  ")
        self._build_top_products(top_prod_tab)

        inv_tab = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(inv_tab, text="  📦 Inventario  ")
        self._build_inventory_report(inv_tab)

    # ── Reporte de Ventas ───────────────────────────────────────────────────

    def _build_sales_report(self, parent):
        # Filtros de fecha
        filter_frame = tk.Frame(parent, bg=COLORS["bg"])
        filter_frame.pack(fill="x", padx=12, pady=10)

        tk.Label(filter_frame, text="Desde:", font=FONTS["body"],
                 bg=COLORS["bg"]).pack(side="left")
        self.date_from = tk.StringVar(
            value=(date.today() - timedelta(days=30)).isoformat())
        ttk.Entry(filter_frame, textvariable=self.date_from,
                  width=12, font=FONTS["body"]).pack(side="left", padx=6)

        tk.Label(filter_frame, text="Hasta:", font=FONTS["body"],
                 bg=COLORS["bg"]).pack(side="left")
        self.date_to = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(filter_frame, textvariable=self.date_to,
                  width=12, font=FONTS["body"]).pack(side="left", padx=6)

        # Filtro rápido
        for label, days in [("Hoy",0),("7 días",7),("30 días",30),("90 días",90)]:
            tk.Button(
                filter_frame, text=label, font=FONTS["small"],
                bg=COLORS["border"], fg=COLORS["text"], relief="flat",
                cursor="hand2", padx=8,
                command=lambda d=days: self._quick_filter(d)
            ).pack(side="left", padx=3)

        tk.Button(filter_frame, text="🔍 Generar Reporte",
                  font=FONTS["button"], bg=COLORS["primary"],
                  fg="white", relief="flat", padx=12,
                  command=self._load_sales_report
                  ).pack(side="right", padx=8)

        # Tarjetas de resumen
        self.sales_summary = tk.Frame(parent, bg=COLORS["bg"])
        self.sales_summary.pack(fill="x", padx=12, pady=6)

        self.s_vars = {k: tk.StringVar(value="—")
                       for k in ["total","count","avg","best_day"]}
        summaries = [
            ("💰 Total Ventas",   "total",    COLORS["success"]),
            ("🧾 Nº Órdenes",     "count",    COLORS["primary"]),
            ("📊 Ticket Promedio","avg",       COLORS["warning"]),
            ("📅 Mejor Día",      "best_day", COLORS["danger"]),
        ]
        for title, key, color in summaries:
            card = tk.Frame(self.sales_summary, bg=COLORS["card"],
                            highlightbackground=COLORS["border"],
                            highlightthickness=1)
            card.pack(side="left", fill="both", expand=True, padx=4)
            tk.Label(card, text=title, font=FONTS["small"],
                     bg=COLORS["card"], fg=COLORS["text_light"]
                     ).pack(pady=(10,2))
            tk.Label(card, textvariable=self.s_vars[key],
                     font=("Segoe UI",16,"bold"),
                     bg=COLORS["card"], fg=color).pack(pady=(0,10))

        # Tabla de ventas por día
        cols = ("Fecha","Nº Órdenes","Total","Promedio")
        frame = tk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=12)
        sy = ttk.Scrollbar(frame, orient="vertical")
        self.sales_tree = ttk.Treeview(
            frame, columns=cols, show="headings",
            yscrollcommand=sy.set, height=10
        )
        for c in cols:
            self.sales_tree.heading(c, text=c)
            self.sales_tree.column(c, width=160, anchor="center")
        sy.config(command=self.sales_tree.yview)
        sy.pack(side="right", fill="y")
        self.sales_tree.pack(fill="both", expand=True)

        # Área para gráfica
        if HAS_MPL:
            self._chart_frame = tk.Frame(parent, bg=COLORS["bg"], height=220)
            self._chart_frame.pack(fill="x", padx=12, pady=8)
        else:
            tk.Label(parent, text="Instala matplotlib para ver gráficas",
                     font=FONTS["small"], bg=COLORS["bg"],
                     fg=COLORS["text_light"]).pack()

    def _quick_filter(self, days: int):
        if days == 0:
            df = dt = date.today().isoformat()
        else:
            df = (date.today() - timedelta(days=days)).isoformat()
            dt = date.today().isoformat()
        self.date_from.set(df)
        self.date_to.set(dt)
        self._load_sales_report()

    def _load_sales_report(self):
        df = self.date_from.get().strip()
        dt = self.date_to.get().strip()
        # Validación básica ISO date
        try:
            date.fromisoformat(df)
            date.fromisoformat(dt)
        except ValueError:
            messagebox.showwarning("Fechas",
                "Formato de fecha inválido (YYYY-MM-DD).")
            return
        if df > dt:
            messagebox.showwarning("Fechas",
                "La fecha inicial no puede ser mayor a la final.")
            return
        threading.Thread(
            target=self._fetch_sales_report, args=(df, dt), daemon=True
        ).start()

    def _fetch_sales_report(self, df, dt):
        try:
            sb = get_client()
            res = sb.table("orders") \
                .select("total, created_at") \
                .eq("status","completed") \
                .gte("created_at",f"{df}T00:00:00") \
                .lte("created_at",f"{dt}T23:59:59") \
                .execute()
            orders = res.data

            # Agrupar por día
            day_map = {}
            for o in orders:
                d = o["created_at"][:10]
                if d not in day_map:
                    day_map[d] = {"count":0,"total":0}
                day_map[d]["count"] += 1
                day_map[d]["total"] += o["total"]

            rows = sorted(day_map.items())
            total = sum(o["total"] for o in orders)
            count = len(orders)
            avg   = total / count if count else 0
            best  = max(rows, key=lambda x: x[1]["total"])[0] if rows else "—"

            self.after(0, self._render_sales_report,
                       rows, total, count, avg, best)
        except Exception as e:
            self.after(0, lambda e=e: messagebox.showerror("Error", str(e)))

    def _render_sales_report(self, rows, total, count, avg, best):
        self.s_vars["total"].set(f"${total:,.2f}")
        self.s_vars["count"].set(str(count))
        self.s_vars["avg"].set(f"${avg:,.2f}")
        self.s_vars["best_day"].set(best)

        for row in self.sales_tree.get_children():
            self.sales_tree.delete(row)
        for d, vals in rows:
            self.sales_tree.insert("","end",values=(
                d, vals["count"],
                f"${vals['total']:,.2f}",
                f"${vals['total']/vals['count']:,.2f}"
            ))

        if HAS_MPL and rows:
            self._draw_chart(rows)

    def _draw_chart(self, rows):
        """Dibuja gráfica de barras con matplotlib."""
        for w in self._chart_frame.winfo_children():
            w.destroy()
        fig = Figure(figsize=(10, 2.8), dpi=90, facecolor=COLORS["bg"])
        ax  = fig.add_subplot(111, facecolor="#F8FAFC")
        dates  = [r[0] for r in rows]
        totals = [r[1]["total"] for r in rows]
        ax.bar(dates, totals, color=COLORS["primary"], alpha=0.8)
        ax.set_title("Ventas por Día", fontsize=11)
        ax.tick_params(axis="x", rotation=45, labelsize=7)
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self._chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # ── Top Productos ───────────────────────────────────────────────────────

    def _build_top_products(self, parent):
        toolbar = tk.Frame(parent, bg=COLORS["bg"])
        toolbar.pack(fill="x", padx=12, pady=10)
        tk.Label(toolbar, text="Top:", font=FONTS["body"],
                 bg=COLORS["bg"]).pack(side="left")
        self.top_n_var = tk.StringVar(value="10")
        ttk.Spinbox(toolbar, from_=5, to=50,
                    textvariable=self.top_n_var, width=6).pack(side="left",padx=6)
        tk.Button(toolbar, text="🔍 Generar",
                  font=FONTS["button"], bg=COLORS["primary"],
                  fg="white", relief="flat", padx=12,
                  command=self._load_top_products).pack(side="left")

        cols = ("Pos.","Producto","Unidades Vendidas","Ingresos Totales","Stock Actual")
        frame = tk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=12)
        sy = ttk.Scrollbar(frame, orient="vertical")
        self.top_tree = ttk.Treeview(
            frame, columns=cols, show="headings",
            yscrollcommand=sy.set, height=16
        )
        widths = {"Pos.":50,"Producto":200,"Unidades Vendidas":140,
                  "Ingresos Totales":140,"Stock Actual":100}
        for c in cols:
            self.top_tree.heading(c, text=c)
            self.top_tree.column(c, width=widths[c], anchor="center")
        sy.config(command=self.top_tree.yview)
        sy.pack(side="right", fill="y")
        self.top_tree.pack(fill="both", expand=True)

        self._load_top_products()

    def _load_top_products(self):
        threading.Thread(target=self._fetch_top, daemon=True).start()

    def _fetch_top(self):
        try:
            sb = get_client()
            # Obtener todos los order_items con producto
            res = sb.table("order_items") \
                .select("quantity, unit_price, products(name, stock)") \
                .execute()
            # Agregar por producto
            agg = {}
            for item in res.data:
                p = item.get("products") or {}
                name = p.get("name","N/A")
                if name not in agg:
                    agg[name] = {"units":0,"revenue":0.0,
                                 "stock": p.get("stock",0)}
                agg[name]["units"]   += item["quantity"]
                agg[name]["revenue"] += item["unit_price"] * item["quantity"]

            rows = sorted(agg.items(),
                          key=lambda x: x[1]["units"], reverse=True)
            try:
                n = int(self.top_n_var.get())
            except ValueError:
                n = 10
            rows = rows[:n]
            self.after(0, self._render_top, rows)
        except Exception as e:
            self.after(0, lambda e=e: messagebox.showerror("Error", str(e)))

    def _render_top(self, rows):
        for row in self.top_tree.get_children():
            self.top_tree.delete(row)
        for i, (name, vals) in enumerate(rows, 1):
            self.top_tree.insert("","end",values=(
                i, name, vals["units"],
                f"${vals['revenue']:,.2f}",
                vals["stock"]
            ))

    # ── Inventario ──────────────────────────────────────────────────────────

    def _build_inventory_report(self, parent):
        toolbar = tk.Frame(parent, bg=COLORS["bg"])
        toolbar.pack(fill="x", padx=12, pady=10)
        tk.Button(toolbar, text="🔄 Actualizar Reporte",
                  font=FONTS["button"], bg=COLORS["primary"],
                  fg="white", relief="flat", padx=12,
                  command=self._load_inv_report).pack(side="left")

        # Tarjetas resumen
        self.inv_summary = tk.Frame(parent, bg=COLORS["bg"])
        self.inv_summary.pack(fill="x", padx=12, pady=6)
        self.inv_vars = {k: tk.StringVar(value="—")
                         for k in ["total_products","low_stock",
                                   "zero_stock","total_value"]}
        summaries = [
            ("📦 Total Productos",  "total_products", COLORS["primary"]),
            ("⚡ Stock Bajo",       "low_stock",       COLORS["warning"]),
            ("🚫 Sin Stock",        "zero_stock",      COLORS["danger"]),
            ("💵 Valor Inventario", "total_value",     COLORS["success"]),
        ]
        for title, key, color in summaries:
            card = tk.Frame(self.inv_summary, bg=COLORS["card"],
                            highlightbackground=COLORS["border"],
                            highlightthickness=1)
            card.pack(side="left", fill="both", expand=True, padx=4)
            tk.Label(card, text=title, font=FONTS["small"],
                     bg=COLORS["card"],fg=COLORS["text_light"]
                     ).pack(pady=(10,2))
            tk.Label(card, textvariable=self.inv_vars[key],
                     font=("Segoe UI",16,"bold"),
                     bg=COLORS["card"], fg=color).pack(pady=(0,10))

        cols = ("Producto","Categoría","Stock","Precio","Valor Total","Estado")
        frame = tk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=12)
        sy = ttk.Scrollbar(frame, orient="vertical")
        self.inv_tree = ttk.Treeview(
            frame, columns=cols, show="headings",
            yscrollcommand=sy.set, height=12
        )
        widths = {"Producto":190,"Categoría":110,"Stock":70,
                  "Precio":90,"Valor Total":100,"Estado":100}
        for c in cols:
            self.inv_tree.heading(c, text=c)
            self.inv_tree.column(c, width=widths[c], anchor="center")
        sy.config(command=self.inv_tree.yview)
        sy.pack(side="right", fill="y")
        self.inv_tree.pack(fill="both", expand=True)

        self.inv_tree.tag_configure("ok",       foreground="#166534")
        self.inv_tree.tag_configure("low",      foreground="#92400E")
        self.inv_tree.tag_configure("zero",     foreground="#991B1B")

        self._load_inv_report()

    def _load_inv_report(self):
        threading.Thread(target=self._fetch_inv, daemon=True).start()

    def _fetch_inv(self):
        try:
            res = get_client().table("products") \
                .select("*").eq("active",True).order("stock").execute()
            data = res.data
            self.after(0, self._render_inv, data)
        except Exception as e:
            self.after(0, lambda e=e: messagebox.showerror("Error",str(e)))

    def _render_inv(self, data):
        for row in self.inv_tree.get_children():
            self.inv_tree.delete(row)

        total_value = 0
        low = zero = 0
        for p in data:
            val = p["price"] * p["stock"]
            total_value += val
            stock = p["stock"]
            if stock == 0:
                tag, status = "zero", "Sin Stock"
                zero += 1
            elif stock <= 10:
                tag, status = "low", "Stock Bajo"
                low += 1
            else:
                tag, status = "ok", "OK"

            self.inv_tree.insert("","end", tags=(tag,), values=(
                p["name"], p.get("category",""),
                stock, f"${p['price']:,.2f}",
                f"${val:,.2f}", status
            ))

        self.inv_vars["total_products"].set(str(len(data)))
        self.inv_vars["low_stock"].set(str(low))
        self.inv_vars["zero_stock"].set(str(zero))
        self.inv_vars["total_value"].set(f"${total_value:,.2f}")
