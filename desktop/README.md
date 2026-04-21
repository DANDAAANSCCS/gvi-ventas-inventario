# GVI — Administración (Desktop)

App de escritorio Python que embebe el panel admin web (`admin-web/`) en una ventana nativa usando `pywebview` + motor **Edge WebView2**. Cumple el apartado "Aplicación de Escritorio" del examen Nubia.

## Requisitos

- Windows 10 / 11
- Python 3.11+
- Edge WebView2 Runtime (preinstalado en Windows 10/11 modernos). Si falta: [instalador oficial Microsoft](https://developer.microsoft.com/microsoft-edge/webview2/) (~2 MB).

## Dev

```bash
pip install -r requirements.txt
python main.py
```

Por default apunta a producción: `https://gvi.namu-li.com/admin/`.

Para apuntar a un backend local (docker compose):

```bash
python main.py --url http://localhost:8180/admin/
# o con env var:
set GVI_ADMIN_URL=http://localhost:8180/admin/
python main.py
```

Login por defecto: `admin@gvi.com` / `Admin123!`.

## Build del ejecutable

```bash
python build.py
```

Salida: `dist/GVI-Admin.exe` (portable, un único archivo). Se puede copiar a cualquier Windows con WebView2 y ejecutar con doble-click.

## Comportamiento

- Se abre **maximizada** cubriendo el área útil del monitor (no fullscreen — respeta taskbar, Alt+Tab, DPI nativo).
- Tamaño mínimo `1024×700` para evitar layouts rotos; la web está pensada para ≥1024px.
- Fondo dark match con el tema del admin-web → sin flash blanco al abrir.
- Todo lo que funciona en el navegador funciona aquí (mismo engine Chromium).
- El login rechaza usuarios con rol `client` — solo admin/staff entran.

## Alcance (según PDF Nubia)

La app desktop está restringida a **Administración**. Desde aquí se puede:

- Dashboard con métricas del día
- CRUD productos
- CRUD clientes
- Gestión de pedidos / ventas
- Inventario (stock actual + movimientos + ajustes)
- Daily ops (apertura y cierre de caja)
- Reportes con gráficas
- CRUD usuarios (solo rol admin)
- DB manager (solo rol admin)

Todo pasa por la API REST (`api-gvi.namu-li.com`). El desktop nunca toca la BD directamente.
