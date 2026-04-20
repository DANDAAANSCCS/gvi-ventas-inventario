# =============================================
# windows/inventory.py — Gestión de Inventario
# =============================================
# Propósito: Ver stock actual y registrar movimientos
# Tablas: products, inventory_movements
# Operaciones: SELECT, INSERT, UPDATE (stock)
# =============================================
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import COLORS, FONTS
from supabase_client import get_client


class InventoryFrame(tk.Frame):
    """
    Módulo de Inventario.
    - Lista todos los productos con su stock actual
    - Permite registrar entradas, salidas y ajustes
    - Historial completo de movimientos
    - Alerta visual para stock bajo (≤ 5)
    """

    def __init__(self, master, app):
        super().__init__(master, bg=COLORS["bg"])
        self.app = app
        self.pack(fill="both", expand=True)
        self._all_products = []
        self._selected_id  = None
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        stock_tab = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(stock_tab, text="  📦 Stock Actual  ")
        self._build_stock_tab(stock_tab)

        hist_tab = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(hist_tab, text="  📋 Historial  ")
        self._build_history_tab(hist_tab)

    # ── Stock tab ───────────────────────────────────────────────────────────

    def _build_stock_tab(self, parent):
        toolbar = tk.Frame(parent, bg=COLORS["bg"])
        toolbar.pack(fill="x", pady=8, padx=8)

        tk.Label(toolbar, text="Buscar:", font=FONTS["body"],
                 bg=COLORS["bg"]).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._filter_stock())
        ttk.Entry(toolbar, textvariable=self.search_var,
                  width=24, font=FONTS["body"]).pack(side="left", padx=6)

        for text, color, cmd in [
            ("📥 Entrada",    COLORS["success"], lambda: self._open_movement("in")),
            ("📤 Salida",     COLORS["danger"],  lambda: self._open_movement("out")),
            ("⚖️ Ajuste",     COLORS["warning"], lambda: self._open_movement("adjustment")),
            ("🔄 Actualizar", COLORS["primary"], self._load_data),
        ]:
            tk.Button(toolbar, text=text, font=FONTS["button"],
                      bg=color, fg="white", relief="flat",
                      padx=10, cursor="hand2", command=cmd
                      ).pack(side="right", padx=4)

        cols = ("Producto","Categoría","Stock","Estado","Última Actualiz.")
        frame = tk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=8)
        sy = ttk.Scrollbar(frame, orient="vertical")
        self.stock_tree = ttk.Treeview(
            frame, columns=cols, show="headings",
            yscrollcommand=sy.set, height=14
        )
        widths = {"Producto":200,"Categoría":120,"Stock":80,
                  "Estado":120,"Última Actualiz.":140}
        for c in cols:
            self.stock_tree.heading(c, text=c)
            self.stock_tree.column(c, width=widths[c], anchor="center")
        sy.config(command=self.stock_tree.yview)
        sy.pack(side="right", fill="y")
        self.stock_tree.pack(fill="both", expand=True)
        self.stock_tree.bind("<<TreeviewSelect>>", self._on_select)

        self.stock_tree.tag_configure("ok",       background="#F0FFF4",
                                      foreground="#166534")
        self.stock_tree.tag_configure("low",      background="#FFFBEB",
                                      foreground="#92400E")
        self.stock_tree.tag_configure("critical", background="#FFF1F2",
                                      foreground="#991B1B")
        self.stock_tree.tag_configure("zero",     background="#F1F5F9",
                                      foreground="#64748B")

        self.stock_status = tk.StringVar(value="Cargando...")
        tk.Label(parent, textvariable=self.stock_status,
                 font=FONTS["small"], bg=COLORS["bg"],
                 fg=COLORS["text_light"]).pack(anchor="w", padx=8, pady=4)

    # ── Historial tab ───────────────────────────────────────────────────────

    def _build_history_tab(self, parent):
        toolbar = tk.Frame(parent, bg=COLORS["bg"])
        toolbar.pack(fill="x", pady=8, padx=8)

        tk.Label(toolbar, text="Tipo:", font=FONTS["body"],
                 bg=COLORS["bg"]).pack(side="left")
        self.hist_type_var = tk.StringVar(value="Todos")
        ttk.Combobox(
            toolbar, textvariable=self.hist_type_var,
            values=["Todos","in","out","adjustment"],
            width=14, state="readonly"
        ).pack(side="left", padx=8)
        self.hist_type_var.trace_add("write", lambda *_: self._load_history())

        tk.Button(toolbar, text="🔄 Actualizar", font=FONTS["button"],
                  bg=COLORS["primary"], fg="white", relief="flat",
                  command=self._load_history).pack(side="right", padx=8)

        cols = ("Producto","Tipo","Cantidad","Razón","Fecha")
        frame = tk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=8)
        sy = ttk.Scrollbar(frame, orient="vertical")
        self.hist_tree = ttk.Treeview(
            frame, columns=cols, show="headings",
            yscrollcommand=sy.set, height=14
        )
        widths = {"Producto":200,"Tipo":80,"Cantidad":90,
                  "Razón":240,"Fecha":140}
        for c in cols:
            self.hist_tree.heading(c, text=c)
            self.hist_tree.column(c, width=widths[c], anchor="center")
        sy.config(command=self.hist_tree.yview)
        sy.pack(side="right", fill="y")
        self.hist_tree.pack(fill="both", expand=True)

        self.hist_tree.tag_configure("in",         foreground="#166534")
        self.hist_tree.tag_configure("out",        foreground="#991B1B")
        self.hist_tree.tag_configure("adjustment", foreground="#92400E")

        self.hist_status = tk.StringVar(value="")
        tk.Label(parent, textvariable=self.hist_status,
                 font=FONTS["small"], bg=COLORS["bg"],
                 fg=COLORS["text_light"]).pack(anchor="w", padx=8, pady=4)

    # ── Datos ───────────────────────────────────────────────────────────────

    def _load_data(self):
        self.stock_status.set("Cargando...")
        threading.Thread(target=self._fetch_products, daemon=True).start()
        self._load_history()

    def _fetch_products(self):
        try:
            res = get_client().table("products") \
                .select("*").eq("active", True) \
                .order("name").execute()
            self._all_products = res.data
            self.after(0, self._render_stock, res.data)
        except Exception as e:
            self.after(0, lambda e=e: self.stock_status.set(f"Error: {e}"))

    def _render_stock(self, data):
        for row in self.stock_tree.get_children():
            self.stock_tree.delete(row)
        for p in data:
            stock = p.get("stock", 0)
            if stock == 0:
                tag, status = "zero", "Sin stock"
            elif stock <= 3:
                tag, status = "critical", "⚠️ Crítico"
            elif stock <= 10:
                tag, status = "low", "⚡ Bajo"
            else:
                tag, status = "ok", "✅ OK"

            self.stock_tree.insert("","end", iid=p["id"],
                tags=(tag,), values=(
                    p["name"],
                    p.get("category",""),
                    stock,
                    status,
                    p.get("created_at","")[:10]
                ))
        self.stock_status.set(f"{len(data)} productos | "
            f"Sin stock: {sum(1 for p in data if p['stock']==0)} | "
            f"Stock bajo: {sum(1 for p in data if 0 < p['stock'] <= 10)}")

    def _filter_stock(self):
        term = self.search_var.get().lower()
        filtered = [p for p in self._all_products
                    if term in p["name"].lower()
                    or term in (p.get("category") or "").lower()]
        self._render_stock(filtered)

    def _on_select(self, event):
        sel = self.stock_tree.selection()
        self._selected_id = sel[0] if sel else None

    def _load_history(self):
        mov_type = self.hist_type_var.get() \
                   if hasattr(self,"hist_type_var") else "Todos"
        threading.Thread(
            target=self._fetch_history, args=(mov_type,), daemon=True
        ).start()

    def _fetch_history(self, mov_type):
        try:
            sb = get_client()
            q = sb.table("inventory_movements") \
                .select("*, products(name)") \
                .order("created_at", desc=True).limit(300)
            if mov_type != "Todos":
                q = q.eq("type", mov_type)
            res = q.execute()
            self.after(0, self._render_history, res.data)
        except Exception as e:
            self.after(0, lambda e=e: self.hist_status.set(f"Error: {e}"))

    def _render_history(self, data):
        for row in self.hist_tree.get_children():
            self.hist_tree.delete(row)
        for m in data:
            name = (m.get("products") or {}).get("name","N/A")
            self.hist_tree.insert("","end", tags=(m["type"],), values=(
                name, m["type"], m["quantity"],
                m.get("reason",""), m["created_at"][:16]
            ))
        self.hist_status.set(f"{len(data)} movimientos")

    # ── Movimiento ──────────────────────────────────────────────────────────

    def _open_movement(self, mov_type: str):
        if not self._selected_id:
            messagebox.showwarning("Selección",
                "Selecciona un producto de la tabla de stock primero.")
            return
        product = next(
            (p for p in self._all_products if p["id"] == self._selected_id), None
        )
        if product:
            MovementForm(self, product, mov_type, self._load_data)


class MovementForm(tk.Toplevel):
    """Formulario para registrar un movimiento de inventario."""

    TYPE_LABELS = {"in": "Entrada 📥", "out": "Salida 📤",
                   "adjustment": "Ajuste ⚖️"}
    TYPE_COLORS = {"in": COLORS["success"], "out": COLORS["danger"],
                   "adjustment": COLORS["warning"]}

    def __init__(self, parent, product, mov_type, on_save):
        super().__init__(parent)
        self.product  = product
        self.mov_type = mov_type
        self.on_save  = on_save
        self.title(f"{self.TYPE_LABELS[mov_type]} — {product['name']}")
        self.geometry("400x360")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.grab_set()
        self._build()

    def _build(self):
        color = self.TYPE_COLORS[self.mov_type]
        header = tk.Frame(self, bg=color, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=self.TYPE_LABELS[self.mov_type],
                 font=FONTS["subtitle"], bg=color, fg="white"
                 ).pack(expand=True)

        body = tk.Frame(self, bg=COLORS["bg"], padx=30, pady=20)
        body.pack(fill="both", expand=True)

        tk.Label(body, text=f"Producto: {self.product['name']}",
                 font=FONTS["body"], bg=COLORS["bg"]).pack(anchor="w")
        tk.Label(body, text=f"Stock actual: {self.product['stock']}",
                 font=FONTS["body"], bg=COLORS["bg"],
                 fg=COLORS["text_light"]).pack(anchor="w", pady=(0,14))

        # Cantidad
        tk.Label(body, text="Cantidad *", font=FONTS["body"],
                 bg=COLORS["bg"]).pack(anchor="w")
        self.qty_var = tk.StringVar()
        ttk.Entry(body, textvariable=self.qty_var,
                  font=FONTS["body"]).pack(fill="x", pady=(4,14))

        # Razón
        tk.Label(body, text="Razón / Nota", font=FONTS["body"],
                 bg=COLORS["bg"]).pack(anchor="w")
        self.reason_var = tk.StringVar()
        ttk.Entry(body, textvariable=self.reason_var,
                  font=FONTS["body"]).pack(fill="x", pady=(4,14))

        self.error_var = tk.StringVar()
        tk.Label(body, textvariable=self.error_var,
                 font=FONTS["small"], fg=COLORS["danger"],
                 bg=COLORS["bg"]).pack(pady=2)

        btn_frame = tk.Frame(body, bg=COLORS["bg"])
        btn_frame.pack(fill="x")
        tk.Button(btn_frame, text="Confirmar",
                  font=FONTS["button"], bg=color,
                  fg="white", relief="flat", padx=16,
                  command=self._confirm).pack(side="left", padx=6)
        tk.Button(btn_frame, text="Cancelar",
                  font=FONTS["button"], bg=COLORS["border"],
                  fg=COLORS["text"], relief="flat", padx=16,
                  command=self.destroy).pack(side="left")

    def _confirm(self):
        try:
            qty = int(self.qty_var.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            self.error_var.set("Introduce una cantidad válida (entero positivo).")
            return

        # Validar que salida no supere stock
        if self.mov_type == "out" and qty > self.product["stock"]:
            self.error_var.set(
                f"No hay suficiente stock. Disponible: {self.product['stock']}")
            return

        self.error_var.set("")
        try:
            sb = get_client()
            # Calcular nuevo stock
            if self.mov_type == "in":
                new_stock = self.product["stock"] + qty
            elif self.mov_type == "out":
                new_stock = self.product["stock"] - qty
            else:  # adjustment: qty es el nuevo stock directo
                new_stock = qty

            # Actualizar stock del producto
            sb.table("products").update({"stock": new_stock}) \
              .eq("id", self.product["id"]).execute()

            # Registrar movimiento
            sb.table("inventory_movements").insert({
                "product_id": self.product["id"],
                "type":       self.mov_type,
                "quantity":   qty,
                "reason":     self.reason_var.get().strip() or None,
            }).execute()

            messagebox.showinfo("Éxito",
                f"Movimiento registrado. Nuevo stock: {new_stock}")
            self.destroy()
            self.on_save()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo registrar: {e}")
