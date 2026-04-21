"""
GVI — Administración (Desktop App)

App de escritorio Python que embebe el panel admin web en una ventana nativa.
Cumple los requisitos de "Aplicación de Escritorio" del examen Nubia:
- CRUD productos / clientes
- Control de inventario y ajustes de stock
- Consulta de ventas
- Comunicación con API REST (no toca la BD directo)
- Ejecutable .exe (ver build.py)
"""

import argparse
import os
import sys

import webview


DEFAULT_URL = "https://gvi.namu-li.com/admin/"


def parse_args():
    parser = argparse.ArgumentParser(
        description="GVI Admin Desktop — ventana nativa al panel admin",
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("GVI_ADMIN_URL", DEFAULT_URL),
        help="URL del panel admin (default: produccion). Para dev local: http://localhost:8180/admin/",
    )
    parser.add_argument(
        "--no-maximize",
        action="store_true",
        help="No maximizar al abrir (util para depurar layouts en tamano reducido)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Ventana principal: tamano inicial razonable + min_size que garantiza layout legible.
    # El background_color coincide con el tema dark del admin-web para evitar flash blanco.
    window = webview.create_window(
        title="GVI - Administracion",
        url=args.url,
        width=1280,
        height=800,
        min_size=(1024, 700),
        resizable=True,
        background_color="#0f1115",
        confirm_close=True,
    )

    def on_start():
        # Maximizamos despues de crear la ventana para que cubra el area util
        # del monitor (respeta taskbar y DPI nativo, a diferencia de fullscreen).
        if not args.no_maximize:
            try:
                window.maximize()
            except Exception as exc:
                # Fallback silencioso: si el backend no soporta maximize (raro en Win),
                # la ventana queda en 1280x800 que igual es usable.
                print(f"[warn] no se pudo maximizar: {exc}", file=sys.stderr)

    # En Windows el engine por default es EdgeChromium (WebView2), mismo render
    # que Edge/Chrome -> DPI-aware, sin scrolls raros, sin texto borroso.
    webview.start(on_start, gui="edgechromium" if sys.platform == "win32" else None)


if __name__ == "__main__":
    main()
