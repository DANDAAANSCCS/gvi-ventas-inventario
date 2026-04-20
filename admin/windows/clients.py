# =============================================
# windows/clients.py — Gestión de Clientes
# =============================================
# Propósito: CRUD de clientes registrados
# Tabla: clients
# Operaciones: SELECT, INSERT, UPDATE
# =============================================
import tkinter as tk
from tkinter import ttk, messagebox
import threading, re
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import COLORS, FONTS
from supabase_client import get_client


class ClientsFrame(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=COLORS["bg"])
        self.app = app
        self.pack(fill="both", expand=True)
        self._selected_id = None
        self._all_clients = []
        self._build_ui()
        self._load_clients()

    def _build_ui(self):
        # Toolbar
        toolbar = tk.Frame(self, bg=COLORS["bg"])
        toolbar.pack(fill="x", pady=(0,10))

        tk.Label(toolbar, text="Buscar:", font=FONTS["body"],
                 bg=COLORS["bg"]).pack(side="left", padx=(0,6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._filter_table())
        ttk.Entry(toolbar, textvariable=self.search_var,
                  width=30, font=FONTS["body"]).pack(side="left")

        for text, color, cmd in [
            ("➕ Nuevo",     COLORS["success"], self._open_form_new),
            ("✏️ Editar",    COLORS["primary"], self._open_form_edit),
            ("📋 Ver Pedidos",COLORS["warning"], self._view_orders),
            ("🔄 Actualizar",COLORS["border"],  self._load_clients),
        ]:
            tk.Button(toolbar, text=text, font=FONTS["button"],
                      bg=color, fg=COLORS["white"] if color != COLORS["border"] else COLORS["text"],
                      relief="flat", padx=10, cursor="hand2",
                      command=cmd).pack(side="right", padx=4)

        # Tabla
        cols = ("ID", "Nombre", "Email", "Teléfono", "Dirección", "Registro")
        frame_tree = tk.Frame(self)
        frame_tree.pack(fill="both", expand=True)

        sy = ttk.Scrollbar(frame_tree, orient="vertical")
        sx = ttk.Scrollbar(frame_tree, orient="horizontal")

        self.tree = ttk.Treeview(
            frame_tree, columns=cols, show="headings",
            yscrollcommand=sy.set, xscrollcommand=sx.set
        )
        widths = {"ID": 70, "Nombre": 180, "Email": 200,
                  "Teléfono": 120, "Dirección": 220, "Registro": 100}
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=widths[col], anchor="center")

        sy.config(command=self.tree.yview)
        sx.config(command=self.tree.xview)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda e: self._open_form_edit())

        self.status_var = tk.StringVar(value="Cargando clientes...")
        tk.Label(self, textvariable=self.status_var, font=FONTS["small"],
                 bg=COLORS["bg"], fg=COLORS["text_light"]).pack(anchor="w", pady=4)

    def _load_clients(self):
        self.status_var.set("Cargando...")
        threading.Thread(target=self._fetch_clients, daemon=True).start()

    def _fetch_clients(self):
        try:
            sb = get_client()
            res = sb.table("clients").select("*").order("name").execute()
            self._all_clients = res.data
            self.after(0, self._render_table, res.data)
        except Exception as e:
            self.after(0, lambda e=e: self.status_var.set(f"Error: {e}"))

    def _render_table(self, data):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for c in data:
            self.tree.insert("", "end", iid=c["id"], values=(
                c["id"][:8],
                c["name"],
                c["email"],
                c.get("phone", ""),
                c.get("address", ""),
                c.get("created_at", "")[:10]
            ))
        self.status_var.set(f"{len(data)} clientes encontrados")

    def _filter_table(self):
        term = self.search_var.get().lower()
        filtered = [
            c for c in self._all_clients
            if term in c["name"].lower()
            or term in c["email"].lower()
            or term in (c.get("phone") or "").lower()
        ]
        self._render_table(filtered)

    def _on_select(self, event):
        sel = self.tree.selection()
        self._selected_id = sel[0] if sel else None

    def _open_form_new(self):
        ClientForm(self, None, self._load_clients)

    def _open_form_edit(self):
        if not self._selected_id:
            messagebox.showwarning("Selección", "Selecciona un cliente primero.")
            return
        client = next((c for c in self._all_clients
                       if c["id"] == self._selected_id), None)
        if client:
            ClientForm(self, client, self._load_clients)

    def _view_orders(self):
        if not self._selected_id:
            messagebox.showwarning("Selección", "Selecciona un cliente primero.")
            return
        ClientOrdersWindow(self, self._selected_id)


class ClientForm(tk.Toplevel):
    """Formulario modal para crear / editar cliente."""

    def __init__(self, parent, client, on_save):
        super().__init__(parent)
        self.client  = client
        self.on_save = on_save
        self.is_edit = client is not None
        self.title("Editar Cliente" if self.is_edit else "Nuevo Cliente")
        self.geometry("440x460")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.grab_set()
        self._build()
        if self.is_edit:
            self._fill()

    def _build(self):
        tk.Label(self, text="Editar Cliente" if self.is_edit else "Nuevo Cliente",
                 font=FONTS["title"], bg=COLORS["bg"]).pack(pady=20, padx=30, anchor="w")

        self.vars = {}
        defs = [
            ("name",    "Nombre completo *"),
            ("email",   "Correo electrónico *"),
            ("phone",   "Teléfono"),
            ("address", "Dirección"),
        ]
        for key, label in defs:
            tk.Label(self, text=label, font=FONTS["body"],
                     bg=COLORS["bg"]).pack(anchor="w", padx=30)
            v = tk.StringVar()
            ttk.Entry(self, textvariable=v, font=FONTS["body"]).pack(
                fill="x", padx=30, pady=(2, 12))
            self.vars[key] = v

        self.error_var = tk.StringVar()
        tk.Label(self, textvariable=self.error_var, font=FONTS["small"],
                 fg=COLORS["danger"], bg=COLORS["bg"]).pack(pady=2)

        bf = tk.Frame(self, bg=COLORS["bg"])
        bf.pack(padx=30, pady=8, fill="x")
        tk.Button(bf, text="Guardar", font=FONTS["button"],
                  bg=COLORS["success"], fg="white", relief="flat",
                  padx=16, command=self._save).pack(side="left", padx=6)
        tk.Button(bf, text="Cancelar", font=FONTS["button"],
                  bg=COLORS["border"], fg=COLORS["text"], relief="flat",
                  padx=16, command=self.destroy).pack(side="left")

    def _fill(self):
        for key, var in self.vars.items():
            var.set(self.client.get(key, "") or "")

    def _validate(self):
        name  = self.vars["name"].get().strip()
        email = self.vars["email"].get().strip()
        if not name:
            self.error_var.set("El nombre es obligatorio.")
            return None
        if not email:
            self.error_var.set("El correo es obligatorio.")
            return None
        if not re.match(r"^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$", email):
            self.error_var.set("Correo electrónico inválido.")
            return None
        phone = self.vars["phone"].get().strip()
        if phone and not re.match(r"^\+?[\d\s\-]{7,15}$", phone):
            self.error_var.set("Teléfono inválido (solo números, espacios o guiones).")
            return None
        self.error_var.set("")
        return {
            "name":    name,
            "email":   email,
            "phone":   phone or None,
            "address": self.vars["address"].get().strip() or None,
        }

    def _save(self):
        payload = self._validate()
        if payload is None:
            return
        try:
            sb = get_client()
            if self.is_edit:
                sb.table("clients").update(payload) \
                  .eq("id", self.client["id"]).execute()
                messagebox.showinfo("Éxito", "Cliente actualizado.")
            else:
                sb.table("clients").insert(payload).execute()
                messagebox.showinfo("Éxito", "Cliente creado.")
            self.destroy()
            self.on_save()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}")


class ClientOrdersWindow(tk.Toplevel):
    """Muestra los pedidos de un cliente específico."""

    def __init__(self, parent, client_id):
        super().__init__(parent)
        self.client_id = client_id
        self.title("Pedidos del Cliente")
        self.geometry("640x400")
        self.configure(bg=COLORS["bg"])
        self.grab_set()
        self._build()
        self._load()

    def _build(self):
        tk.Label(self, text="Historial de Pedidos", font=FONTS["title"],
                 bg=COLORS["bg"]).pack(pady=14, padx=20, anchor="w")
        cols = ("ID", "Total", "Estado", "Método de Pago", "Fecha")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=110, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=20)
        self.status_var = tk.StringVar(value="Cargando...")
        tk.Label(self, textvariable=self.status_var, font=FONTS["small"],
                 bg=COLORS["bg"]).pack(pady=6)

    def _load(self):
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        try:
            res = get_client().table("orders") \
                .select("*").eq("client_id", self.client_id) \
                .order("created_at", desc=True).execute()
            self.after(0, self._render, res.data)
        except Exception as e:
            self.after(0, lambda e=e: self.status_var.set(f"Error: {e}"))

    def _render(self, data):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for o in data:
            self.tree.insert("", "end", values=(
                o["id"][:8], f"${o['total']:,.2f}",
                o["status"], o.get("payment_method", ""),
                o["created_at"][:10]
            ))
        self.status_var.set(f"{len(data)} pedidos")
