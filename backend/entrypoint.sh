#!/usr/bin/env bash
# Ejecuta migraciones (schema.sql) y lanza uvicorn.
# Uso opcional cuando se quiera correr todo junto. Por defecto el Dockerfile
# lanza uvicorn directo; si quieres auto-schema, cambia el CMD a ["./entrypoint.sh"].
set -e

if [ -f "/app/db/schema.sql" ]; then
  echo "Aplicando schema.sql..."
  python -c "
import asyncio, os
from sqlalchemy import text
from database import engine
async def run():
    with open('/app/db/schema.sql') as f: sql = f.read()
    async with engine.begin() as c:
        await c.execute(text(sql))
asyncio.run(run())
"
fi

exec uvicorn main:app --host 0.0.0.0 --port 8000
