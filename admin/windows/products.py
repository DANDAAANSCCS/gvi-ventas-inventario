# =============================================
# windows/products.py — Gestión de Productos
# =============================================
# Propósito: CRUD completo de productos
# Tabla: products
# Operaciones: SELECT, INSERT, UPDATE, DELETE (soft)
# =============================================
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import COLORS, FONTS
from supabase_client import get_client


class ProductsFrame(tk.Frame):
    """
    Módulo de Gestión de Productos.
    Permite:
    - Listar todos los productos con búsqueda y filtros
    - Agregar nuevo producto
    - Editar producto existente
    - Desactivar producto (eliminación lógica)
    - Ver nivel de stock con alerta visual
    """

    def __init__(self, master, app):
        super().__init__(master, bg=COLORS["bg"])
        self.app = app
        self.pack(fill="both", expand=True)
        self._selected_id = None
        self._build_ui()
        self._load_products()

    # ── UI ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Barra de herramientas superior
        toolbar = tk.Frame(self, bg=COLORS["bg"])
        toolbar.pack(fill="x", pady=(0, 10))

        tk.Label(toolbar, text="Buscar:", font=FONTS["body"],
                 bg=COLORS["bg"]).pack(side="left", padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._filter_table())
        ttk.Entry(toolbar, textvariable=self.search_var,
                  width=28, font=FONTS["body"]).pack(side="left")

        # Filtro por categoría
        tk.Label(toolbar, text="Categoría:", font=FONTS["body"],
                 bg=COLORS["bg"]).pack(side="left", padx=(14,4))
        self.cat_var = tk.StringVar(value="Todas")
        self.cat_combo = ttk.Combobox(toolbar, textvariable=self.cat_var,
                                       width=16, state="readonly")
        self.cat_combo.pack(side="left")
        self.cat_combo.bind("<<ComboboxSelected>>", lambda e: self._filter_table())

        # Botones CRUD
        for text, color, cmd in [
            ("➕ Nuevo",    COLORS["success"],  self._open_form_new),
            ("✏️ Editar",   COLORS["primary"],  self._open_form_edit),
            ("🗑️ Desactivar", COLORS["danger"], self._deactivate),
            ("🔄 Actualizar",COLORS["warning"], self._load_products),
        ]:
            tk.Button(toolbar, text=text, font=FONTS["button"],
                      bg=color, fg=COLORS["white"], relief="flat",
                      padx=10, cursor="hand2", command=cmd
                      ).pack(side="right", padx=4)

        # Tabla
        cols = ("ID", "Nombre", "Categoría", "Precio", "Stock", "Activo")
        frame_tree = tk.Frame(self)
        frame_tree.pack(fill="both", expand=True)

        scroll_y = ttk.Scrollbar(frame_tree, orient="vertical")
        scroll_x = ttk.Scrollbar(frame_tree, orient="horizontal")

        self.tree = ttk.Treeview(
            frame_tree, columns=cols, show="headings",
            yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set
        )
        col_widths = {"ID": 70, "Nombre": 200, "Categoría": 120,
                      "Precio": 90, "Stock": 80, "Activo": 70}
        for col in cols:
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._sort_column(c))
            self.tree.column(col, width=col_widths[col], anchor="center")

        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda e: self._open_form_edit())

        # Tag visual para stock bajo
        self.tree.tag_configure("low_stock", background="#FEF2F2",
                                foreground=COLORS["danger"])
        self.tree.tag_configure("inactive", background="#F8FAFC",
                                foreground=COLORS["text_light"])

        # Barra de estado
        self.status_var = tk.StringVar(value="Cargando productos...")
        tk.Label(self, textvariable=self.status_var, font=FONTS["small"],
                 bg=COLORS["bg"], fg=COLORS["text_light"]).pack(anchor="w", pady=4)

    # ── Datos ───────────────────────────────────────────────────────────────

    def _load_products(self):
        self.status_var.set("Cargando...")
        threading.Thread(target=self._fetch_products, daemon=True).start()

    def _fetch_products(self):
        try:
            sb = get_client()
            res = sb.table("products").select("*").order("name").execute()
            self._all_products = res.data

            # Obtener categorías únicas
            cats = sorted({p["category"] for p in res.data if p.get("category")})
            self.after(0, self._populate_categories, cats)
            self.after(0, self._render_table, res.data)
        except Exception as e:
            self.after(0, lambda e=e: self.status_var.set(f"Error: {e}"))

    def _populate_categories(self, cats):
        self.cat_combo["values"] = ["Todas"] + cats

    def _render_table(self, data):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for p in data:
            tags = []
            if not p.get("active"):
                tags.append("inactive")
            elif p.get("stock", 0) <= 5:
                tags.append("low_stock")

            self.tree.insert("", "end",
                iid=p["id"],
                values=(
                    p["id"][:8],
                    p["name"],
                    p.get("category", ""),
                    f"${p['price']:,.2f}",
                    p["stock"],
                    "✅" if p.get("active") else "❌"
                ),
                tags=tags
            )
        self.status_var.set(f"{len(data)} productos encontrados")

    def _filter_table(self):
        if not hasattr(self, "_all_products"):
            return
        term = self.search_var.get().lower()
        cat  = self.cat_var.get()
        filtered = [
            p for p in self._all_products
            if (term in p["name"].lower() or term in (p.get("category") or "").lower())
            and (cat == "Todas" or p.get("category") == cat)
        ]
        self._render_table(filtered)

    def _sort_column(self, col):
        """Ordenar tabla por columna al hacer clic en el encabezado."""
        if not hasattr(self, "_all_products"):
            return
        key_map = {"Nombre": "name", "Precio": "price",
                   "Stock": "stock", "Categoría": "category"}
        key = key_map.get(col)
        if key:
            self._all_products.sort(key=lambda x: x.get(key) or 0)
            self._filter_table()

    def _on_select(self, event):
        selection = self.tree.selection()
        self._selected_id = selection[0] if selection else None

    # ── CRUD ────────────────────────────────────────────────────────────────

    def _open_form_new(self):
        ProductForm(self, None, self._load_products)

    def _open_form_edit(self):
        if not self._selected_id:
            messagebox.showwarning("Selección", "Selecciona un producto primero.")
            return
        # Buscar datos del producto seleccionado
        product = next(
            (p for p in self._all_products if p["id"] == self._selected_id), None
        )
        if product:
            ProductForm(self, product, self._load_products)

    def _deactivate(self):
        if not self._selected_id:
            messagebox.showwarning("Selección", "Selecciona un producto primero.")
            return
        if not messagebox.askyesno(
            "Confirmar",
            "¿Desactivar este producto? No aparecerá en el catálogo de clientes."
        ):
            return
        try:
            get_client().table("products") \
                .update({"active": False}) \
                .eq("id", self._selected_id).execute()
            messagebox.showinfo("Éxito", "Producto desactivado correctamente.")
            self._load_products()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo desactivar: {e}")


# ── Formulario de Producto ──────────────────────────────────────────────────

class ProductForm(tk.Toplevel):
    """
    Formulario modal para crear o editar un producto.
    Valida todos los campos antes de enviar a Supabase.
    """

    def __init__(self, parent, product: dict | None, on_save):
        super().__init__(parent)
        self.product = product
        self.on_save = on_save
        self.is_edit  = product is not None

        self.title("Editar Producto" if self.is_edit else "Nuevo Producto")
        self.geometry("480x540")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.grab_set()

        self._build_form()
        if self.is_edit:
            self._fill_form()

    def _build_form(self):
        pad = {"padx": 30}
        tk.Label(self, text="Editar Producto" if self.is_edit else "Nuevo Producto",
                 font=FONTS["title"], bg=COLORS["bg"]).pack(pady=20, **pad, anchor="w")

        self.fields = {}
        field_defs = [
            ("name",        "Nombre *",            False),
            ("category",    "Categoría",           False),
            ("price",       "Precio *",            False),
            ("stock",       "Stock inicial *",     False),
            ("description", "Descripción",         True),
            ("image_url",   "URL de imagen",       False),
        ]

        for key, label, multiline in field_defs:
            tk.Label(self, text=label, font=FONTS["body"],
                     bg=COLORS["bg"]).pack(anchor="w", **pad)
            var = tk.StringVar()
            if multiline:
                widget = tk.Text(self, height=3, font=FONTS["body"],
                                 relief="solid", bd=1)
                widget.pack(fill="x", padx=30, pady=(2,10))
                self.fields[key] = widget
            else:
                entry = ttk.Entry(self, textvariable=var, font=FONTS["body"])
                entry.pack(fill="x", **pad, pady=(2,10))
                self.fields[key] = var

        # Activo (solo en edición)
        if self.is_edit:
            self.active_var = tk.BooleanVar(value=True)
            tk.Checkbutton(
                self, text="Producto activo", variable=self.active_var,
                bg=COLORS["bg"], font=FONTS["body"]
            ).pack(anchor="w", padx=30)

        # Error label
        self.error_var = tk.StringVar()
        tk.Label(self, textvariable=self.error_var, font=FONTS["small"],
                 fg=COLORS["danger"], bg=COLORS["bg"]).pack(pady=4)

        # Botones
        btn_frame = tk.Frame(self, bg=COLORS["bg"])
        btn_frame.pack(fill="x", padx=30, pady=10)
        tk.Button(btn_frame, text="Guardar", font=FONTS["button"],
                  bg=COLORS["success"], fg="white", relief="flat",
                  padx=16, command=self._save).pack(side="left", padx=6)
        tk.Button(btn_frame, text="Cancelar", font=FONTS["button"],
                  bg=COLORS["border"], fg=COLORS["text"], relief="flat",
                  padx=16, command=self.destroy).pack(side="left")

    def _fill_form(self):
        """Rellena el formulario con los datos existentes."""
        mapping = {"name": "name", "category": "category",
                   "price": "price", "stock": "stock",
                   "image_url": "image_url"}
        for key, field_key in mapping.items():
            val = self.product.get(field_key, "")
            widget = self.fields.get(key)
            if isinstance(widget, tk.StringVar):
                widget.set(str(val) if val is not None else "")

        # Descripcion (Text widget)
        desc_widget = self.fields.get("description")
        if isinstance(desc_widget, tk.Text):
            desc_widget.delete("1.0", "end")
            desc_widget.insert("1.0", self.product.get("description", "") or "")

        if hasattr(self, "active_var"):
            self.active_var.set(self.product.get("active", True))

    def _get_description(self) -> str:
        widget = self.fields.get("description")
        if isinstance(widget, tk.Text):
            return widget.get("1.0", "end-1c").strip()
        return ""

    def _validate(self) -> dict | None:
        """Valida y retorna el payload o None si hay error."""
        name = self.fields["name"].get().strip()
        price_str = self.fields["price"].get().strip()
        stock_str = self.fields["stock"].get().strip()

        if not name:
            self.error_var.set("El nombre es obligatorio.")
            return None
        if len(name) < 2:
            self.error_var.set("El nombre debe tener al menos 2 caracteres.")
            return None
        if not price_str:
            self.error_var.set("El precio es obligatorio.")
            return None
        try:
            price = float(price_str)
            if price < 0:
                raise ValueError
        except ValueError:
            self.error_var.set("El precio debe ser un número positivo.")
            return None
        if not stock_str:
            self.error_var.set("El stock es obligatorio.")
            return None
        try:
            stock = int(stock_str)
            if stock < 0:
                raise ValueError
        except ValueError:
            self.error_var.set("El stock debe ser un número entero positivo.")
            return None

        self.error_var.set("")
        payload = {
            "name":        name,
            "category":    self.fields["category"].get().strip() or None,
            "price":       price,
            "stock":       stock,
            "description": self._get_description() or None,
            "image_url":   self.fields["image_url"].get().strip() or None,
        }
        if self.is_edit:
            payload["active"] = self.active_var.get()
        return payload

    def _save(self):
        payload = self._validate()
        if payload is None:
            return
        try:
            sb = get_client()
            if self.is_edit:
                sb.table("products").update(payload) \
                  .eq("id", self.product["id"]).execute()
                messagebox.showinfo("Éxito", "Producto actualizado correctamente.")
            else:
                sb.table("products").insert(payload).execute()
                messagebox.showinfo("Éxito", "Producto creado correctamente.")
            self.destroy()
            self.on_save()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}")
