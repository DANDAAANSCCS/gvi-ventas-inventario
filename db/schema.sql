-- =====================================================
-- Schema PostgreSQL — Gestion Ventas e Inventario (GVI)
-- Normalizado a 3FN con FKs, UNIQUE, CHECK e indices.
-- Ejecutar una sola vez en una BD vacia.
-- =====================================================

BEGIN;

-- Extension para UUIDs
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =====================================================
-- ENUMs
-- =====================================================
DO $$ BEGIN
  CREATE TYPE user_role AS ENUM ('admin', 'staff', 'client');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE order_status AS ENUM ('pending', 'completed', 'cancelled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE movement_type AS ENUM ('in', 'out', 'adjustment');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- =====================================================
-- Tabla: users
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email          TEXT NOT NULL UNIQUE,
  password_hash  TEXT NOT NULL,
  role           user_role NOT NULL DEFAULT 'client',
  is_active      BOOLEAN NOT NULL DEFAULT TRUE,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_role  ON users (role) WHERE is_active = TRUE;

-- =====================================================
-- Tabla: clients (perfil asociado a un user)
-- =====================================================
CREATE TABLE IF NOT EXISTS clients (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  phone       TEXT,
  address     TEXT,
  active      BOOLEAN NOT NULL DEFAULT TRUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_clients_user ON clients (user_id);
CREATE INDEX IF NOT EXISTS idx_clients_active ON clients (active);

-- =====================================================
-- Tabla: products
-- =====================================================
CREATE TABLE IF NOT EXISTS products (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,
  description TEXT,
  price       NUMERIC(10,2) NOT NULL CHECK (price >= 0),
  stock       INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
  category    TEXT,
  image_url   TEXT,
  active      BOOLEAN NOT NULL DEFAULT TRUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_products_active_cat ON products (active, category);
CREATE INDEX IF NOT EXISTS idx_products_name ON products (lower(name));

-- =====================================================
-- Tabla: orders (cabecera de pedido)
-- =====================================================
CREATE TABLE IF NOT EXISTS orders (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id      UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
  total          NUMERIC(10,2) NOT NULL CHECK (total >= 0),
  status         order_status NOT NULL DEFAULT 'pending',
  payment_method TEXT,
  notes          TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_orders_client_date ON orders (client_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status);

-- =====================================================
-- Tabla: order_items (detalle)
-- =====================================================
CREATE TABLE IF NOT EXISTS order_items (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id   UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
  quantity   INTEGER NOT NULL CHECK (quantity > 0),
  unit_price NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0),
  UNIQUE (order_id, product_id)
);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items (order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items (product_id);

-- =====================================================
-- Tabla: inventory_movements
-- =====================================================
CREATE TABLE IF NOT EXISTS inventory_movements (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id  UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
  type        movement_type NOT NULL,
  quantity    INTEGER NOT NULL CHECK (quantity > 0),
  reason      TEXT,
  user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_inv_prod_date ON inventory_movements (product_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_inv_type ON inventory_movements (type);

-- =====================================================
-- Tabla: daily_operations (caja diaria)
-- =====================================================
CREATE TABLE IF NOT EXISTS daily_operations (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  date          DATE NOT NULL UNIQUE DEFAULT CURRENT_DATE,
  opening_cash  NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (opening_cash >= 0),
  closing_cash  NUMERIC(10,2) CHECK (closing_cash IS NULL OR closing_cash >= 0),
  total_sales   NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (total_sales >= 0),
  notes         TEXT,
  created_by    UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_operations (date DESC);

-- =====================================================
-- Tabla: password_reset_tokens
-- Almacena el hash (no el token en claro) + expiracion.
-- =====================================================
CREATE TABLE IF NOT EXISTS password_reset_tokens (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash  VARCHAR(128) NOT NULL UNIQUE,
  expires_at  TIMESTAMPTZ NOT NULL,
  used_at     TIMESTAMPTZ,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pwreset_user ON password_reset_tokens (user_id);
CREATE INDEX IF NOT EXISTS idx_pwreset_expires ON password_reset_tokens (expires_at);

COMMIT;
