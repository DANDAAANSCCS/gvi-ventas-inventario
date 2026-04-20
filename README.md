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
├── client/               # SPA estática
│   ├── index.html        # catálogo
│   ├── login.html  register.html  orders.html  history.html  terms.html
│   ├── css/styles.css
│   ├── js/
│   │   ├── config.js         # window.API_URL (inyectado en runtime)
│   │   ├── api-client.js     # wrapper fetch + JWT
│   │   ├── auth.js           # sesión cliente
│   │   ├── catalog.js  cart.js  history.js  utils.js
│   ├── nginx.conf
│   ├── nginx-entrypoint.sh   # escribe js/config.js con API_URL
│   └── Dockerfile
├── db/schema.sql         # DDL PostgreSQL (3FN, FKs, CHECK, índices)
├── docker-compose.yml    # dev local
└── admin/                # app Tkinter (pendiente de migrar a la API)
```

## Dev local

```bash
docker compose up -d --build
docker compose exec backend python seed.py
```

- Frontend: http://localhost:8180
- API: http://localhost:8100/docs
- Admin por defecto: `admin@gvi.com` / `Admin123!`

## Variables de entorno (backend)

Ver `backend/.env.example`. Claves:

- `DATABASE_URL` — `postgresql+asyncpg://user:pass@host:5432/db`
- `JWT_SECRET` — cadena larga y aleatoria (≥32 chars)
- `CORS_ORIGINS` — dominios del frontend separados por coma
- `ADMIN_EMAIL` / `ADMIN_PASSWORD` — credenciales que usa `seed.py`

## Deploy en Coolify

1. Crear recurso **PostgreSQL 16**.
2. Crear servicio backend (build desde `backend/Dockerfile`) apuntando a `api-gvi.namu-li.com`.
   Inyectar `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS=https://gvi.namu-li.com`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`.
3. Crear servicio frontend (build desde `client/Dockerfile`) apuntando a `gvi.namu-li.com`.
   Inyectar `API_URL=https://api-gvi.namu-li.com`.
4. Ejecutar schema en la BD:
   ```bash
   psql $DATABASE_URL < db/schema.sql
   ```
5. Ejecutar seed desde la terminal del backend:
   ```bash
   python seed.py
   ```

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
