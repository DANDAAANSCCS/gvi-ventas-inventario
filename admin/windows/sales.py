# =============================================
# windows/sales.py — Módulo de Ventas
# =============================================
# Propósito: Registrar nuevas ventas y listar existentes
# Tablas: orders, order_items, products, clients
# Operaciones: SELECT, INSERT (transaccional manual)
# =============================================
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import COLORS, FONTS
from supabase_client import get_client


class SalesFrame(tk.Frame):
    """
    Módulo de ventas.
    - Lista todas las ventas/pedidos
    - Permite registrar una nueva venta (selección de cliente + productos)
    - Cambia estado del pedido (pendiente → completado → cancelado)
    """

    def __init__(self, master, app):
        super().__init__(master, bg=COLORS["bg"])
        self.app = app
        self.pack(fill="both", expand=True)
        self._selected_id = None
        self._all_orders  = []
        self._build_ui()
        self._load_orders()

    def _build_ui(self):
        # Pestañas
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        # Tab 1: Listado de ventas
        list_tab = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(list_tab, text="  📋 Ventas Registradas  ")
        self._build_list_tab(list_tab)

        # Tab 2: Nueva venta
        new_tab = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(new_tab, text="  ➕ Nueva Venta  ")
        self._build_new_sale_tab(new_tab)

    # ── Tab Listado ─────────────────────────────────────────────────────────

    def _build_list_tab(self, parent):
        # Filtros
        filter_frame = tk.Frame(parent, bg=COLORS["bg"])
        filter_frame.pack(fill="x", pady=(8,4), padx=8)

        tk.Label(filter_frame, text="Estado:", font=FONTS["body"],
                 bg=COLORS["bg"]).pack(side="left")
        self.status_filter = tk.StringVar(value="Todos")
        ttk.Combobox(
            filter_frame, textvariable=self.status_filter,
            values=["Todos","pending","completed","cancelled"],
            width=14, state="readonly"
        ).pack(side="left", padx=8)
        self.status_filter.trace_add("write", lambda *_: self._filter_orders())

        for text, color, cmd in [
            ("✅ Completar",  COLORS["success"], lambda: self._change_status("completed")),
            ("❌ Cancelar",   COLORS["danger"],  lambda: self._change_status("cancelled")),
            ("🔍 Ver Detalle",COLORS["primary"], self._view_detail),
            ("🔄 Actualizar", COLORS["warning"], self._load_orders),
        ]:
            tk.Button(filter_frame, text=text, font=FONTS["button"],
                      bg=color, fg="white", relief="flat",
                      padx=10, cursor="hand2", command=cmd
                      ).pack(side="right", padx=4)

        # Tabla
        cols = ("ID","Cliente","Total","Estado","Pago","Fecha")
        frame_tree = tk.Frame(parent)
        frame_tree.pack(fill="both", expand=True, padx=8)

        sy = ttk.Scrollbar(frame_tree, orient="vertical")
        self.orders_tree = ttk.Treeview(
            frame_tree, columns=cols, show="headings",
            yscrollcommand=sy.set, height=14
        )
        widths = {"ID":75,"Cliente":180,"Total":100,"Estado":100,"Pago":120,"Fecha":100}
        for col in cols:
            self.orders_tree.heading(col, text=col)
            self.orders_tree.column(col, width=widths[col], anchor="center")
        sy.config(command=self.orders_tree.yview)
        sy.pack(side="right", fill="y")
        self.orders_tree.pack(fill="both", expand=True)
        self.orders_tree.bind("<<TreeviewSelect>>", self._on_select)

        # Tags de color por estado
        self.orders_tree.tag_configure("completed", background="#F0FFF4",
                                       foreground="#15803D")
        self.orders_tree.tag_configure("cancelled", background="#FFF1F2",
                                       foreground="#B91C1C")
        self.orders_tree.tag_configure("pending",   background="#FFFBEB",
                                       foreground="#B45309")

        self.orders_status = tk.StringVar(value="Cargando...")
        tk.Label(parent, textvariable=self.orders_status,
                 font=FONTS["small"], bg=COLORS["bg"],
                 fg=COLORS["text_light"]).pack(anchor="w",padx=8,pady=4)

    # ── Tab Nueva Venta ─────────────────────────────────────────────────────

    def _build_new_sale_tab(self, parent):
        """Formulario para crear una nueva venta."""
        left  = tk.Frame(parent, bg=COLORS["bg"])
        right = tk.Frame(parent, bg=COLORS["bg"])
        left.pack(side="left",  fill="both", expand=True, padx=(10,4), pady=10)
        right.pack(side="right", fill="both", expand=True, padx=(4,10), pady=10)

        # ── Panel izquierdo: Selección de sección ──
        tk.Label(left, text="Cliente", font=FONTS["subtitle"],
                 bg=COLORS["bg"]).pack(anchor="w")
        self.client_search_var = tk.StringVar()
        self.client_search_var.trace_add("write",
                                         lambda *_: self._search_clients())
        ttk.Entry(left, textvariable=self.client_search_var,
                  font=FONTS["body"]).pack(fill="x", pady=4)

        self.clients_listbox = tk.Listbox(left, height=5,
                                          font=FONTS["body"],
                                          selectmode="single")
        self.clients_listbox.pack(fill="x", pady=(0,10))
        self.clients_listbox.bind("<<ListboxSelect>>", self._on_client_select)

        self.selected_client_var = tk.StringVar(value="Sin cliente seleccionado")
        tk.Label(left, textvariable=self.selected_client_var,
                 font=FONTS["body"], fg=COLORS["primary"],
                 bg=COLORS["bg"]).pack(anchor="w", pady=4)

        # Productos disponibles
        tk.Label(left, text="Productos disponibles",
                 font=FONTS["subtitle"], bg=COLORS["bg"]).pack(anchor="w",pady=(10,4))

        prod_cols = ("Nombre","Precio","Stock")
        self.prod_tree = ttk.Treeview(left, columns=prod_cols,
                                      show="headings", height=8)
        for c in prod_cols:
            self.prod_tree.heading(c, text=c)
            self.prod_tree.column(c, width=110, anchor="center")
        self.prod_tree.pack(fill="both", expand=True)

        qty_frame = tk.Frame(left, bg=COLORS["bg"])
        qty_frame.pack(fill="x", pady=6)
        tk.Label(qty_frame, text="Cantidad:", font=FONTS["body"],
                 bg=COLORS["bg"]).pack(side="left")
        self.qty_var = tk.StringVar(value="1")
        ttk.Spinbox(qty_frame, from_=1, to=999,
                    textvariable=self.qty_var, width=6).pack(side="left",padx=6)
        tk.Button(qty_frame, text="Agregar al carrito ▶",
                  font=FONTS["button"], bg=COLORS["primary"],
                  fg="white", relief="flat", command=self._add_to_cart
                  ).pack(side="right")

        # ── Panel derecho: Carrito ──
        tk.Label(right, text="Carrito de Venta",
                 font=FONTS["subtitle"], bg=COLORS["bg"]).pack(anchor="w")

        cart_cols = ("Producto","Cant.","P.Unit","Subtotal")
        self.cart_tree = ttk.Treeview(right, columns=cart_cols,
                                      show="headings", height=10)
        for c in cart_cols:
            self.cart_tree.heading(c, text=c)
            self.cart_tree.column(c, width=110, anchor="center")
        self.cart_tree.pack(fill="both", expand=True)

        tk.Button(right, text="🗑️ Quitar seleccionado",
                  font=FONTS["button"], bg=COLORS["danger"],
                  fg="white", relief="flat",
                  command=self._remove_from_cart).pack(anchor="e", pady=4)

        # Total
        total_frame = tk.Frame(right, bg=COLORS["bg"])
        total_frame.pack(fill="x", pady=6)
        tk.Label(total_frame, text="Total:", font=FONTS["subtitle"],
                 bg=COLORS["bg"]).pack(side="left")
        self.total_var = tk.StringVar(value="$0.00")
        tk.Label(total_frame, textvariable=self.total_var,
                 font=("Segoe UI",20,"bold"), fg=COLORS["success"],
                 bg=COLORS["bg"]).pack(side="left", padx=10)

        # Método de pago
        tk.Label(right, text="Método de pago:", font=FONTS["body"],
                 bg=COLORS["bg"]).pack(anchor="w")
        self.payment_var = tk.StringVar(value="Efectivo")
        ttk.Combobox(right, textvariable=self.payment_var,
                     values=["Efectivo","Tarjeta","Transferencia","Otro"],
                     state="readonly", width=18).pack(anchor="w", pady=4)

        tk.Label(right, text="Notas:", font=FONTS["body"],
                 bg=COLORS["bg"]).pack(anchor="w")
        self.notes_text = tk.Text(right, height=3, font=FONTS["body"],
                                  relief="solid", bd=1)
        self.notes_text.pack(fill="x", pady=4)

        tk.Button(right, text="✅ Registrar Venta",
                  font=FONTS["button"], bg=COLORS["success"],
                  fg="white", relief="flat", height=2,
                  command=self._register_sale).pack(fill="x", pady=8)

        # Datos internos del carrito
        self._cart_items = []       # [{"product": {...}, "qty": int}]
        self._selected_client = None
        self._all_products_list = []
        self._all_clients_list  = []

        # Cargar datos iniciales
        threading.Thread(target=self._load_initial_data, daemon=True).start()

    # ── Lógica ──────────────────────────────────────────────────────────────

    def _load_initial_data(self):
        try:
            sb = get_client()
            prods   = sb.table("products").select("*").eq("active",True) \
                       .gt("stock",0).order("name").execute().data
            clients = sb.table("clients").select("*").order("name").execute().data
            self._all_products_list = prods
            self._all_clients_list  = clients
            self.after(0, self._populate_products, prods)
            self.after(0, self._populate_clients, clients)
        except Exception as e:
            self.after(0, lambda e=e: messagebox.showerror("Error",str(e)))

    def _populate_products(self, data):
        for row in self.prod_tree.get_children():
            self.prod_tree.delete(row)
        for p in data:
            self.prod_tree.insert("","end", iid=p["id"], values=(
                p["name"], f"${p['price']:,.2f}", p["stock"]
            ))

    def _populate_clients(self, data):
        self.clients_listbox.delete(0,"end")
        for c in data:
            self.clients_listbox.insert("end", f"{c['name']} — {c['email']}")

    def _search_clients(self):
        term = self.client_search_var.get().lower()
        filtered = [c for c in self._all_clients_list
                    if term in c["name"].lower()
                    or term in c["email"].lower()]
        self.clients_listbox.delete(0,"end")
        for c in filtered:
            self.clients_listbox.insert("end", f"{c['name']} — {c['email']}")
        self._filtered_clients = filtered

    def _on_client_select(self, event):
        idx = self.clients_listbox.curselection()
        if not idx:
            return
        clients = getattr(self, "_filtered_clients", self._all_clients_list)
        if idx[0] < len(clients):
            self._selected_client = clients[idx[0]]
            self.selected_client_var.set(
                f"✅ {self._selected_client['name']}")

    def _add_to_cart(self):
        sel = self.prod_tree.selection()
        if not sel:
            messagebox.showwarning("Selección","Selecciona un producto.")
            return
        prod_id = sel[0]
        product = next((p for p in self._all_products_list
                        if p["id"] == prod_id), None)
        if not product:
            return
        try:
            qty = int(self.qty_var.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Cantidad","Introduce una cantidad válida (≥1).")
            return

        # Verificar stock disponible
        already = sum(i["qty"] for i in self._cart_items
                      if i["product"]["id"] == prod_id)
        if already + qty > product["stock"]:
            messagebox.showwarning("Stock",
                f"Stock insuficiente. Disponible: {product['stock']}, "
                f"ya en carrito: {already}")
            return

        # Agregar o sumar al existente
        for item in self._cart_items:
            if item["product"]["id"] == prod_id:
                item["qty"] += qty
                break
        else:
            self._cart_items.append({"product": product, "qty": qty})

        self._refresh_cart()

    def _remove_from_cart(self):
        sel = self.cart_tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        self._cart_items.pop(idx)
        self._refresh_cart()

    def _refresh_cart(self):
        for row in self.cart_tree.get_children():
            self.cart_tree.delete(row)
        total = 0.0
        for i, item in enumerate(self._cart_items):
            subtotal = item["product"]["price"] * item["qty"]
            total   += subtotal
            self.cart_tree.insert("","end", iid=str(i), values=(
                item["product"]["name"],
                item["qty"],
                f"${item['product']['price']:,.2f}",
                f"${subtotal:,.2f}"
            ))
        self.total_var.set(f"${total:,.2f}")

    def _register_sale(self):
        if not self._selected_client:
            messagebox.showwarning("Cliente","Selecciona un cliente para la venta.")
            return
        if not self._cart_items:
            messagebox.showwarning("Carrito","Agrega productos al carrito.")
            return

        total = sum(i["product"]["price"] * i["qty"]
                    for i in self._cart_items)

        if not messagebox.askyesno(
            "Confirmar Venta",
            f"Cliente: {self._selected_client['name']}\n"
            f"Total: ${total:,.2f}\n"
            f"Pago: {self.payment_var.get()}\n\n"
            "¿Confirmar la venta?"
        ):
            return

        threading.Thread(target=self._do_register_sale,
                         args=(total,), daemon=True).start()

    def _do_register_sale(self, total):
        try:
            sb = get_client()
            notes = self.notes_text.get("1.0","end-1c").strip()

            # 1. Crear orden
            order_res = sb.table("orders").insert({
                "client_id":      self._selected_client["id"],
                "total":          total,
                "status":         "completed",
                "payment_method": self.payment_var.get(),
                "notes":          notes or None,
            }).execute()
            order_id = order_res.data[0]["id"]

            # 2. Insertar artículos de la orden
            items_payload = [
                {
                    "order_id":   order_id,
                    "product_id": item["product"]["id"],
                    "quantity":   item["qty"],
                    "unit_price": item["product"]["price"],
                }
                for item in self._cart_items
            ]
            sb.table("order_items").insert(items_payload).execute()

            # 3. Actualizar stock (reducir)
            for item in self._cart_items:
                new_stock = item["product"]["stock"] - item["qty"]
                sb.table("products") \
                  .update({"stock": new_stock}) \
                  .eq("id", item["product"]["id"]).execute()

                # Registrar movimiento de inventario
                sb.table("inventory_movements").insert({
                    "product_id": item["product"]["id"],
                    "type":       "out",
                    "quantity":   item["qty"],
                    "reason":     f"Venta #{order_id[:8]}",
                }).execute()

            self.after(0, self._sale_success)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error",
                f"No se pudo registrar la venta: {e}"))

    def _sale_success(self):
        messagebox.showinfo("Éxito", "¡Venta registrada correctamente!")
        self._cart_items = []
        self._selected_client = None
        self.selected_client_var.set("Sin cliente seleccionado")
        self._refresh_cart()
        self._load_orders()
        threading.Thread(target=self._load_initial_data, daemon=True).start()

    # ── Órdenes ─────────────────────────────────────────────────────────────

    def _load_orders(self):
        self.orders_status.set("Cargando...")
        threading.Thread(target=self._fetch_orders, daemon=True).start()

    def _fetch_orders(self):
        try:
            res = get_client().table("orders") \
                .select("*, clients(name)") \
                .order("created_at", desc=True).limit(200).execute()
            self._all_orders = res.data
            self.after(0, self._render_orders, res.data)
        except Exception as e:
            self.after(0, lambda e=e: self.orders_status.set(f"Error: {e}"))

    def _render_orders(self, data):
        for row in self.orders_tree.get_children():
            self.orders_tree.delete(row)
        for o in data:
            cn = (o.get("clients") or {}).get("name","N/A")
            tag = o.get("status","pending")
            self.orders_tree.insert("","end", iid=o["id"],
                tags=(tag,), values=(
                    o["id"][:8], cn,
                    f"${o['total']:,.2f}",
                    o["status"],
                    o.get("payment_method",""),
                    o["created_at"][:10]
                ))
        self.orders_status.set(f"{len(data)} órdenes")

    def _filter_orders(self):
        sf = self.status_filter.get()
        filtered = self._all_orders if sf == "Todos" \
                   else [o for o in self._all_orders if o["status"] == sf]
        self._render_orders(filtered)

    def _on_select(self, event):
        sel = self.orders_tree.selection()
        self._selected_id = sel[0] if sel else None

    def _change_status(self, new_status):
        if not self._selected_id:
            messagebox.showwarning("Selección","Selecciona una orden.")
            return
        order = next((o for o in self._all_orders
                      if o["id"] == self._selected_id), None)
        if order and order["status"] == new_status:
            messagebox.showinfo("Info",
                f"La orden ya está en estado '{new_status}'.")
            return
        if messagebox.askyesno("Confirmar",
            f"¿Cambiar estado a '{new_status}'?"):
            try:
                get_client().table("orders") \
                    .update({"status": new_status}) \
                    .eq("id", self._selected_id).execute()
                self._load_orders()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _view_detail(self):
        if not self._selected_id:
            messagebox.showwarning("Selección","Selecciona una orden.")
            return
        OrderDetailWindow(self, self._selected_id)


class OrderDetailWindow(tk.Toplevel):
    """Detalle de una orden: artículos, totales."""

    def __init__(self, parent, order_id):
        super().__init__(parent)
        self.order_id = order_id
        self.title(f"Detalle Orden #{order_id[:8]}")
        self.geometry("600x400")
        self.configure(bg=COLORS["bg"])
        self.grab_set()
        self._build()
        self._load()

    def _build(self):
        tk.Label(self, text=f"Orden #{self.order_id[:8]}",
                 font=FONTS["title"], bg=COLORS["bg"]).pack(pady=14,padx=20,anchor="w")
        cols = ("Producto","Cantidad","P. Unitario","Subtotal")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=130, anchor="center")
        self.tree.pack(fill="both",expand=True,padx=20)
        self.total_label = tk.Label(self, text="Total: ...",
            font=FONTS["subtitle"],bg=COLORS["bg"],fg=COLORS["success"])
        self.total_label.pack(anchor="e",padx=20,pady=8)

    def _load(self):
        threading.Thread(target=self._fetch,daemon=True).start()

    def _fetch(self):
        try:
            res = get_client().table("order_items") \
                .select("*, products(name)") \
                .eq("order_id",self.order_id).execute()
            self.after(0, self._render, res.data)
        except Exception as e:
            self.after(0, lambda e=e: messagebox.showerror("Error",str(e)))

    def _render(self, data):
        total = 0
        for item in data:
            sub = item["unit_price"] * item["quantity"]
            total += sub
            name = (item.get("products") or {}).get("name","N/A")
            self.tree.insert("","end",values=(
                name, item["quantity"],
                f"${item['unit_price']:,.2f}",
                f"${sub:,.2f}"
            ))
        self.total_label.config(text=f"Total: ${total:,.2f}")
