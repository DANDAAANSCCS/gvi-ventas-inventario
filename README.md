# GVI — Sistema de Gestión de Ventas e Inventario

Portal web del proyecto **Nubia** (Ventas e Inventario) con API REST propia.

## Stack

- **Backend**: FastAPI + SQLAlchemy async + asyncpg + JWT + bcrypt
- **Base de datos**: PostgreSQL 16
- **Frontend**: HTML/CSS/JS vanilla servido por nginx (3 webs en el mismo contenedor)
- **Deploy**: Docker / docker-compose / Coolify

## Estructura

```
Gestion_ventas_inventario/
├── backend/              # API FastAPI
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py         # SQLAlchemy
│   ├── schemas.py        # Pydantic
│   ├── auth.py           # JWT + bcrypt
│   ├── dependencies.py   # get_current_user, require_role
│   ├── routers/          # auth, products, clients, orders, inventory, reports, users, daily_ops, admin_db
│   ├── seed.py           # admin + 15 productos demo
│   ├── Dockerfile
│   └── requirements.txt
├── client/               # SPA publica (catálogo y compra cliente final)
│   ├── index.html  login.html  register.html  orders.html  history.html  terms.html
│   ├── css/  js/
│   ├── nginx.conf        # sirve client + admin-web + db-web en el mismo dominio
│   ├── nginx-entrypoint.sh
│   └── Dockerfile        # build context = raiz del repo (copia las 3 webs)
├── admin-web/            # Panel admin web (staff/admin)
│   ├── login.html  dashboard.html  products.html  clients.html  orders.html
│   ├── inventory.html  daily-ops.html  reports.html  users.html
│   └── css/admin.css  js/(api-client, auth-admin, utils, layout, charts, config).js
├── db-web/               # DB manager estilo Railway (solo admin)
│   ├── login.html  index.html
│   └── css/db.css  js/(api-client, auth-admin, utils, schema-viewer, table-grid, sql-editor, config).js
├── db/schema.sql         # DDL PostgreSQL (3FN, FKs, CHECK, índices)
├── docker-compose.yml    # dev local
└── admin/                # app Tkinter original (legacy, se puede retirar)
```

## Dev local

```bash
docker compose up -d --build
docker compose exec backend python seed.py
```

Rutas (todas bajo el mismo puerto 8180):

- Cliente publico: http://localhost:8180
- Panel admin web: http://localhost:8180/admin/ (login con admin/staff)
- DB manager: http://localhost:8180/db/ (login solo con admin)
- API: http://localhost:8100/docs
- Admin por defecto: `admin@gvi.com` / `Admin123!`

## Variables de entorno (backend)

Ver `backend/.env.example`. Claves:

- `DATABASE_URL` — `postgresql+asyncpg://user:pass@host:5432/db`
- `JWT_SECRET` — cadena larga y aleatoria (≥32 chars)
- `CORS_ORIGINS` — dominios del frontend separados por coma
- `ADMIN_EMAIL` / `ADMIN_PASSWORD` — credenciales que usa `seed.py`

## Deploy en Coolify

Un solo backend alimenta **un único frontend** que sirve las 3 webs bajo el mismo dominio usando subrutas.

| Servicio | Subdominio | Build context | Dockerfile | Env vars |
|----------|-----------|---------------|------------|----------|
| Backend API | `api-gvi.namu-li.com` | `backend/` | `backend/Dockerfile` | `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` |
| Frontend (3 webs) | `gvi.namu-li.com` | **raíz del repo** | `client/Dockerfile` | `API_URL=https://api-gvi.namu-li.com` |

Rutas resultantes:

- `https://gvi.namu-li.com/` → cliente publico
- `https://gvi.namu-li.com/admin/` → panel admin (login rechaza a `client`)
- `https://gvi.namu-li.com/db/` → DB manager (login solo permite `admin`)

### Pasos

1. Crear recurso **PostgreSQL 16**.
2. Crear/editar servicio **backend** apuntando a `api-gvi.namu-li.com`. En `CORS_ORIGINS` basta un único origen:
   ```
   CORS_ORIGINS=https://gvi.namu-li.com
   ```
3. Crear/editar servicio **frontend** apuntando a `gvi.namu-li.com`. **Importante**: build context = raíz del repo y dockerfile = `client/Dockerfile`. Env: `API_URL=https://api-gvi.namu-li.com`.
4. Ejecutar schema en la BD:
   ```bash
   psql $DATABASE_URL < db/schema.sql
   ```
5. Ejecutar seed desde la terminal del backend:
   ```bash
   python seed.py
   ```

### Autobuild en git push
Coolify detecta pushes a la rama configurada y rebuilda el frontend cuando cambia cualquiera de las 3 carpetas (`client/`, `admin-web/`, `db-web/`) porque todas entran al mismo build context.

## Seguridad (checklist requisitos del examen)

- ✅ Contraseñas con **bcrypt** (no texto plano).
- ✅ **JWT** con expiración, secret en env var.
- ✅ **Control de roles** en backend (admin / staff / client).
- ✅ **SQLAlchemy** parametriza queries (anti SQL injection).
- ✅ **CORS** restringido al dominio del frontend.
- ✅ **HTTPS** automático vía Cloudflare Tunnel.
- ✅ Frontend **nunca** toca la BD: todo pasa por la API.
- ✅ Eliminación **lógica** (campo `active`, nunca DELETE físico).
- ✅ Pedido **transaccional** con `SELECT ... FOR UPDATE` (sin race conditions).
