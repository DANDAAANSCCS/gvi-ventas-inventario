# GVI — Sistema de Gestión de Ventas e Inventario

Portal web del proyecto **Nubia** (Ventas e Inventario) con API REST propia.

## Stack

- **Backend**: FastAPI + SQLAlchemy async + asyncpg + JWT + bcrypt
- **Base de datos**: PostgreSQL 16
- **Frontend**: HTML/CSS/JS vanilla servido por nginx
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
│   ├── routers/          # auth, products, clients, orders, inventory, reports
│   ├── seed.py           # admin + 15 productos demo
│   ├── Dockerfile
│   └── requirements.txt
├── client/               # SPA publica (catálogo y compra cliente final)
│   ├── index.html  login.html  register.html  orders.html  history.html  terms.html
│   ├── css/  js/  nginx.conf  nginx-entrypoint.sh  Dockerfile
├── admin-web/            # Panel admin web (staff/admin) — reemplaza al tkinter
│   ├── login.html  dashboard.html  products.html  clients.html  orders.html
│   ├── inventory.html  daily-ops.html  reports.html  users.html
│   ├── css/admin.css  js/(api-client, auth-admin, utils, layout, charts, config).js
│   ├── nginx.conf  nginx-entrypoint.sh  Dockerfile
├── db-web/               # DB manager estilo Railway (solo admin)
│   ├── login.html  index.html
│   ├── css/db.css  js/(api-client, auth-admin, utils, schema-viewer, table-grid, sql-editor, config).js
│   ├── nginx.conf  nginx-entrypoint.sh  Dockerfile
├── db/schema.sql         # DDL PostgreSQL (3FN, FKs, CHECK, índices)
├── docker-compose.yml    # dev local
└── admin/                # app Tkinter original (legacy, se puede retirar)
```

## Dev local

```bash
docker compose up -d --build
docker compose exec backend python seed.py
```

- Cliente publico: http://localhost:8180
- Panel admin web: http://localhost:8181 (login con admin/staff)
- DB manager: http://localhost:8182 (login solo con admin)
- API: http://localhost:8100/docs
- Admin por defecto: `admin@gvi.com` / `Admin123!`

## Variables de entorno (backend)

Ver `backend/.env.example`. Claves:

- `DATABASE_URL` — `postgresql+asyncpg://user:pass@host:5432/db`
- `JWT_SECRET` — cadena larga y aleatoria (≥32 chars)
- `CORS_ORIGINS` — dominios del frontend separados por coma
- `ADMIN_EMAIL` / `ADMIN_PASSWORD` — credenciales que usa `seed.py`

## Deploy en Coolify

Un solo backend alimenta 3 frontends desplegados en subdominios distintos.

| Servicio | Subdominio | Build context | Env vars |
|----------|-----------|---------------|----------|
| Backend API | `api-gvi.namu-li.com` | `backend/` | `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` |
| Cliente publico | `gvi.namu-li.com` | `client/` | `API_URL=https://api-gvi.namu-li.com` |
| Panel admin | `admin.gvi.namu-li.com` | `admin-web/` | `API_URL=https://api-gvi.namu-li.com` |
| DB manager | `db.gvi.namu-li.com` | `db-web/` | `API_URL=https://api-gvi.namu-li.com` |

### Pasos

1. Crear recurso **PostgreSQL 16**.
2. Crear servicio backend apuntando a `api-gvi.namu-li.com`. En `CORS_ORIGINS` incluir los 3 origenes separados por coma:
   ```
   CORS_ORIGINS=https://gvi.namu-li.com,https://admin.gvi.namu-li.com,https://db.gvi.namu-li.com
   ```
3. Crear servicio **cliente publico** (build `client/Dockerfile`) con `API_URL=https://api-gvi.namu-li.com`.
4. Crear servicio **admin-web** (build `admin-web/Dockerfile`) con `API_URL=https://api-gvi.namu-li.com`. Apuntar DNS de `admin.gvi.namu-li.com` al servidor.
5. Crear servicio **db-web** (build `db-web/Dockerfile`) con `API_URL=https://api-gvi.namu-li.com`. Apuntar DNS de `db.gvi.namu-li.com` al servidor.
6. Ejecutar schema en la BD:
   ```bash
   psql $DATABASE_URL < db/schema.sql
   ```
7. Ejecutar seed desde la terminal del backend:
   ```bash
   python seed.py
   ```

### Autobuild en git push
Coolify detecta pushes a la rama configurada y rebuilda solo los servicios cuyo `build context` contenga cambios. Mantener las 3 webs como servicios separados evita rebuilds innecesarios.

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
