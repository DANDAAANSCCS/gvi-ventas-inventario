# =============================================
# windows/daily_ops.py — Operaciones Diarias
# =============================================
# Propósito: Apertura/cierre de caja y reporte del día
# Tabla: daily_operations
# Operaciones: SELECT, INSERT, UPDATE
# =============================================
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from datetime import date
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import COLORS, FONTS
from supabase_client import get_client


class DailyOpsFrame(tk.Frame):
    """
    Operaciones Diarias.
    - Visualiza y crea el registro de caja del día actual
    - Permite abrir la caja (monto inicial) y cerrarla
    - Muestra resumen de ventas del día
    - Historial de cierres anteriores
    """

    def __init__(self, master, app):
        super().__init__(master, bg=COLORS["bg"])
        self.app = app
        self.pack(fill="both", expand=True)
        self._today_record = None
        self._build_ui()
        self._load_today()

    def _build_ui(self):
        # Panel superior: caja del día
        top = tk.Frame(self, bg=COLORS["bg"])
        top.pack(fill="x", pady=(0,16))

        # Tarjeta estado del día
        self.status_card = tk.Frame(
            top, bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )
        self.status_card.pack(side="left", fill="both",
                              expand=True, padx=(0,10))

        tk.Label(
            self.status_card, text=f"📅 Operaciones — {date.today().strftime('%d/%m/%Y')}",
            font=FONTS["subtitle"], bg=COLORS["card"]
        ).pack(pady=(14,4), padx=20, anchor="w")

        self.day_status_var = tk.StringVar(value="Verificando...")
        tk.Label(
            self.status_card, textvariable=self.day_status_var,
            font=FONTS["body"], bg=COLORS["card"],
            fg=COLORS["text_light"]
        ).pack(padx=20, anchor="w")

        # Formulario apertura/cierre
        form_frame = tk.Frame(self.status_card, bg=COLORS["card"])
        form_frame.pack(fill="x", padx=20, pady=12)

        tk.Label(form_frame, text="Efectivo inicial ($):",
                 font=FONTS["body"], bg=COLORS["card"]).grid(
                     row=0, column=0, sticky="w", pady=4)
        self.opening_var = tk.StringVar(value="0.00")
        self.opening_entry = ttk.Entry(
            form_frame, textvariable=self.opening_var, width=14)
        self.opening_entry.grid(row=0, column=1, padx=10)

        tk.Label(form_frame, text="Efectivo cierre ($):",
                 font=FONTS["body"], bg=COLORS["card"]).grid(
                     row=1, column=0, sticky="w", pady=4)
        self.closing_var = tk.StringVar(value="0.00")
        self.closing_entry = ttk.Entry(
            form_frame, textvariable=self.closing_var, width=14)
        self.closing_entry.grid(row=1, column=1, padx=10)

        tk.Label(form_frame, text="Notas:",
                 font=FONTS["body"], bg=COLORS["card"]).grid(
                     row=2, column=0, sticky="nw", pady=4)
        self.notes_text = tk.Text(form_frame, height=3, width=28,
                                   font=FONTS["body"], relief="solid", bd=1)
        self.notes_text.grid(row=2, column=1, padx=10)

        # Botones
        btn_frame = tk.Frame(self.status_card, bg=COLORS["card"])
        btn_frame.pack(fill="x", padx=20, pady=(0,14))

        self.btn_open = tk.Button(
            btn_frame, text="🔓 Abrir Caja",
            font=FONTS["button"], bg=COLORS["success"],
            fg="white", relief="flat", padx=12,
            command=self._open_day
        )
        self.btn_open.pack(side="left", padx=(0,8))

        self.btn_close = tk.Button(
            btn_frame, text="🔒 Cerrar Caja",
            font=FONTS["button"], bg=COLORS["danger"],
            fg="white", relief="flat", padx=12,
            state="disabled",
            command=self._close_day
        )
        self.btn_close.pack(side="left")

        # Tarjeta resumen del día
        summary_card = tk.Frame(
            top, bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1, width=220
        )
        summary_card.pack(side="right", fill="y")
        summary_card.pack_propagate(False)

        tk.Label(summary_card, text="📊 Resumen del Día",
                 font=FONTS["subtitle"], bg=COLORS["card"]
                 ).pack(pady=(14,6), padx=16, anchor="w")

        self.summary_vars = {
            "total_sales":  tk.StringVar(value="$0.00"),
            "num_orders":   tk.StringVar(value="0"),
            "avg_ticket":   tk.StringVar(value="$0.00"),
        }
        labels = [
            ("Ventas totales",  "total_sales",  COLORS["success"]),
            ("Nº de órdenes",   "num_orders",   COLORS["primary"]),
            ("Ticket promedio", "avg_ticket",   COLORS["warning"]),
        ]
        for label, key, color in labels:
            row = tk.Frame(summary_card, bg=COLORS["card"])
            row.pack(fill="x", padx=16, pady=4)
            tk.Label(row, text=label, font=FONTS["small"],
                     bg=COLORS["card"],
                     fg=COLORS["text_light"]).pack(anchor="w")
            tk.Label(row, textvariable=self.summary_vars[key],
                     font=FONTS["subtitle"], bg=COLORS["card"],
                     fg=color).pack(anchor="w")

        tk.Button(summary_card, text="🔄 Actualizar",
                  font=FONTS["small"], bg=COLORS["border"],
                  fg=COLORS["text"], relief="flat",
                  command=self._load_today
                  ).pack(pady=8)

        # Historial de días anteriores
        tk.Label(self, text="Historial de Operaciones",
                 font=FONTS["subtitle"], bg=COLORS["bg"]
                 ).pack(anchor="w", pady=(0,6))

        cols = ("Fecha","Apertura","Cierre","Total Ventas","Notas")
        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True)
        sy = ttk.Scrollbar(frame, orient="vertical")
        self.hist_tree = ttk.Treeview(
            frame, columns=cols, show="headings",
            yscrollcommand=sy.set, height=8
        )
        widths = {"Fecha":100,"Apertura":100,"Cierre":100,
                  "Total Ventas":120,"Notas":260}
        for c in cols:
            self.hist_tree.heading(c, text=c)
            self.hist_tree.column(c, width=widths[c], anchor="center")
        sy.config(command=self.hist_tree.yview)
        sy.pack(side="right", fill="y")
        self.hist_tree.pack(fill="both", expand=True)

    # ── Datos ───────────────────────────────────────────────────────────────

    def _load_today(self):
        self.day_status_var.set("Verificando...")
        threading.Thread(target=self._fetch_today, daemon=True).start()
        threading.Thread(target=self._fetch_history, daemon=True).start()
        threading.Thread(target=self._fetch_summary, daemon=True).start()

    def _fetch_today(self):
        try:
            today_str = date.today().isoformat()
            res = get_client().table("daily_operations") \
                .select("*").eq("date", today_str).execute()
            record = res.data[0] if res.data else None
            self._today_record = record
            self.after(0, self._update_day_ui, record)
        except Exception as e:
            self.after(0, lambda e=e: self.day_status_var.set(f"Error: {e}"))

    def _update_day_ui(self, record):
        if record is None:
            self.day_status_var.set("Caja NOT abierta hoy. Haz clic en 'Abrir Caja'.")
            self.btn_open.config(state="normal")
            self.btn_close.config(state="disabled")
            self.opening_entry.config(state="normal")
            self.closing_entry.config(state="disabled")
        elif record.get("closing_cash") is None:
            self.day_status_var.set(
                f"✅ Caja ABIERTA — Apertura: ${record['opening_cash']:,.2f}")
            self.opening_var.set(str(record["opening_cash"]))
            self.btn_open.config(state="disabled")
            self.btn_close.config(state="normal")
            self.opening_entry.config(state="disabled")
            self.closing_entry.config(state="normal")
        else:
            self.day_status_var.set(
                f"🔒 Caja CERRADA — "
                f"Apertura: ${record['opening_cash']:,.2f} | "
                f"Cierre: ${record['closing_cash']:,.2f}")
            self.opening_var.set(str(record["opening_cash"]))
            self.closing_var.set(str(record["closing_cash"]))
            self.btn_open.config(state="disabled")
            self.btn_close.config(state="disabled")
            self.opening_entry.config(state="disabled")
            self.closing_entry.config(state="disabled")

    def _fetch_summary(self):
        try:
            today = date.today().isoformat()
            res = get_client().table("orders") \
                .select("total").eq("status","completed") \
                .gte("created_at",f"{today}T00:00:00").execute()
            orders = res.data
            total  = sum(o["total"] for o in orders)
            count  = len(orders)
            avg    = total / count if count else 0
            self.after(0, lambda: [
                self.summary_vars["total_sales"].set(f"${total:,.2f}"),
                self.summary_vars["num_orders"].set(str(count)),
                self.summary_vars["avg_ticket"].set(f"${avg:,.2f}"),
            ])
        except Exception:
            pass

    def _fetch_history(self):
        try:
            res = get_client().table("daily_operations") \
                .select("*").order("date", desc=True).limit(30).execute()
            self.after(0, self._render_history, res.data)
        except Exception as e:
            pass

    def _render_history(self, data):
        for row in self.hist_tree.get_children():
            self.hist_tree.delete(row)
        for r in data:
            self.hist_tree.insert("","end",values=(
                r["date"],
                f"${r.get('opening_cash',0):,.2f}",
                f"${r['closing_cash']:,.2f}" if r.get("closing_cash") else "—",
                f"${r.get('total_sales',0):,.2f}",
                r.get("notes","")
            ))

    # ── Acciones ────────────────────────────────────────────────────────────

    def _open_day(self):
        try:
            opening = float(self.opening_var.get())
            if opening < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Validación",
                "El monto de apertura debe ser un número positivo.")
            return
        notes = self.notes_text.get("1.0","end-1c").strip()
        user  = self.app.current_user
        try:
            get_client().table("daily_operations").insert({
                "date":         date.today().isoformat(),
                "opening_cash": opening,
                "notes":        notes or None,
                "created_by":   user.id if user else None,
            }).execute()
            messagebox.showinfo("Éxito", "Caja abierta correctamente.")
            self._load_today()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir caja: {e}")

    def _close_day(self):
        try:
            closing = float(self.closing_var.get())
            if closing < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Validación",
                "El monto de cierre debe ser un número positivo.")
            return

        if not self._today_record:
            return

        if not messagebox.askyesno("Confirmar Cierre",
            f"¿Cerrar caja del día con ${closing:,.2f}?\n"
            "Esta operación no se puede deshacer."):
            return

        notes = self.notes_text.get("1.0","end-1c").strip()
        try:
            # Obtener total de ventas del día
            today = date.today().isoformat()
            res = get_client().table("orders") \
                .select("total").eq("status","completed") \
                .gte("created_at",f"{today}T00:00:00").execute()
            total_sales = sum(o["total"] for o in res.data)

            get_client().table("daily_operations").update({
                "closing_cash": closing,
                "total_sales":  total_sales,
                "notes": (self._today_record.get("notes","") or "") +
                         (f"\nCierre: {notes}" if notes else ""),
            }).eq("id", self._today_record["id"]).execute()

            messagebox.showinfo("Éxito",
                f"Caja cerrada. Total ventas del día: ${total_sales:,.2f}")
            self._load_today()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cerrar caja: {e}")
