"""Router DB manager estilo Railway.

Exposicion cuidadosa de PostgreSQL solo para rol admin:
  - whitelist de tablas (no se tocan password_reset_tokens ni tablas del sistema),
  - list/paginate/search/insert/update/delete/export genericos por tabla,
  - endpoint SQL arbitrario con bloqueo de DDL destructiva salvo flag explicito.
"""
import csv
import io
import logging
import re
import time
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import require_role
from models import User, UserRole
from schemas import (
    ColumnInfo,
    RowsPage,
    SqlQueryRequest,
    SqlQueryResult,
    TableInfo,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin-db", tags=["admin-db"])

# Whitelist: tablas expuestas al DB manager. NO incluir password_reset_tokens (contiene hashes
# de tokens vivos) ni tablas del sistema.
ALLOWED_TABLES: set[str] = {
    "users",
    "clients",
    "products",
    "orders",
    "order_items",
    "inventory_movements",
    "daily_operations",
}

IDENT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
DESTRUCTIVE_RE = re.compile(
    r"\b(DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE|VACUUM|CLUSTER|REINDEX)\b",
    re.IGNORECASE,
)

AUDIT_PATH = Path("/tmp/gvi_db_queries.log")


def _safe_ident(name: str, kind: str = "identifier") -> str:
    """Valida que un identificador sea seguro para concatenarse en SQL."""
    if not name or not IDENT_RE.match(name):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{kind} invalido: {name!r}")
    return name


def _check_table(table: str) -> str:
    tbl = _safe_ident(table, "tabla")
    if tbl not in ALLOWED_TABLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Tabla no permitida: {table}")
    return tbl


def _jsonify(value: Any) -> Any:
    """Convierte tipos Python no serializables (UUID/Decimal/datetime) a algo JSON-friendly."""
    if value is None:
        return None
    if isinstance(value, (UUID,)):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _log_query(user: User, sql: str, status_str: str, duration_ms: float) -> None:
    """Audit log append (best-effort, no bloquea si falla)."""
    try:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_PATH.open("a", encoding="utf-8") as f:
            f.write(
                f"{datetime.utcnow().isoformat()}\t{user.email}\t{status_str}\t"
                f"{duration_ms:.1f}ms\t{sql[:500]}\n"
            )
    except Exception:
        logger.exception("[admin-db] no se pudo escribir audit log")


@router.get("/tables", response_model=list[TableInfo])
async def list_tables(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    """Lista de tablas expuestas con conteo aproximado de filas."""
    out: list[TableInfo] = []
    for tbl in sorted(ALLOWED_TABLES):
        count = (await db.execute(text(f'SELECT COUNT(*) FROM "{tbl}"'))).scalar_one()
        cols = (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name=:t"
                ),
                {"t": tbl},
            )
        ).scalar_one()
        out.append(TableInfo(name=tbl, row_count=int(count), column_count=int(cols)))
    return out


@router.get("/tables/{table}/columns", response_model=list[ColumnInfo])
async def get_columns(
    table: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    """Metadata de columnas: tipo, nullable, default, si es PK y a qué tabla apunta como FK."""
    tbl = _check_table(table)

    cols_stmt = text(
        """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=:t
        ORDER BY ordinal_position
        """
    )
    pk_stmt = text(
        """
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = :t::regclass AND i.indisprimary
        """
    )
    fk_stmt = text(
        """
        SELECT kcu.column_name, ccu.table_name AS ref_table, ccu.column_name AS ref_column
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name
         AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema='public' AND tc.table_name=:t
        """
    )

    cols = (await db.execute(cols_stmt, {"t": tbl})).all()
    pks = {r[0] for r in (await db.execute(pk_stmt, {"t": tbl})).all()}
    fks = {r[0]: (r[1], r[2]) for r in (await db.execute(fk_stmt, {"t": tbl})).all()}

    return [
        ColumnInfo(
            name=c.column_name,
            type=c.data_type,
            nullable=(c.is_nullable == "YES"),
            default=c.column_default,
            is_pk=c.column_name in pks,
            fk_ref=(
                f"{fks[c.column_name][0]}.{fks[c.column_name][1]}"
                if c.column_name in fks
                else None
            ),
        )
        for c in cols
    ]


async def _text_columns(db: AsyncSession, tbl: str) -> list[str]:
    """Columnas de tipo texto (usadas para busqueda ILIKE)."""
    q = text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name=:t "
        "AND data_type IN ('text','character varying','varchar','character')"
    )
    rows = (await db.execute(q, {"t": tbl})).all()
    return [r[0] for r in rows]


@router.get("/tables/{table}/rows", response_model=RowsPage)
async def list_rows(
    table: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    order_by: str | None = None,
    order_dir: str = Query("desc", pattern="^(asc|desc)$"),
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    """Paginacion + orden + busqueda ILIKE sobre columnas de texto."""
    tbl = _check_table(table)
    order_sql = ""
    if order_by:
        order_col = _safe_ident(order_by, "columna")
        order_sql = f' ORDER BY "{order_col}" {order_dir.upper()}'
    elif "created_at" in (await _text_columns(db, tbl)) or True:
        # preferimos created_at como orden default cuando existe
        exists = (
            await db.execute(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name=:t AND column_name='created_at'"
                ),
                {"t": tbl},
            )
        ).first()
        if exists:
            order_sql = ' ORDER BY "created_at" DESC'

    where_sql = ""
    params: dict[str, Any] = {}
    if search:
        text_cols = await _text_columns(db, tbl)
        if text_cols:
            conds = [f'CAST("{c}" AS TEXT) ILIKE :q' for c in text_cols]
            where_sql = " WHERE " + " OR ".join(conds)
            params["q"] = f"%{search}%"

    count_sql = f'SELECT COUNT(*) FROM "{tbl}"{where_sql}'
    total = (await db.execute(text(count_sql), params)).scalar_one()

    data_sql = f'SELECT * FROM "{tbl}"{where_sql}{order_sql} LIMIT :limit OFFSET :offset'
    params.update({"limit": limit, "offset": offset})
    result = await db.execute(text(data_sql), params)
    columns = list(result.keys())
    rows = [
        {col: _jsonify(val) for col, val in zip(columns, row)}
        for row in result.all()
    ]
    return RowsPage(columns=columns, rows=rows, total=int(total))


@router.post("/tables/{table}/rows", status_code=status.HTTP_201_CREATED)
async def insert_row(
    table: str,
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    """Inserta una fila. Body = dict columna->valor. Excluye claves vacias."""
    tbl = _check_table(table)
    clean = {k: v for k, v in body.items() if v is not None and v != ""}
    if not clean:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cuerpo vacio")
    cols = [_safe_ident(k, "columna") for k in clean.keys()]
    cols_sql = ", ".join(f'"{c}"' for c in cols)
    placeholders = ", ".join(f":{c}" for c in cols)
    sql = f'INSERT INTO "{tbl}" ({cols_sql}) VALUES ({placeholders}) RETURNING *'
    result = await db.execute(text(sql), clean)
    row = result.mappings().first()
    await db.commit()
    return {k: _jsonify(v) for k, v in dict(row).items()} if row else None


@router.patch("/tables/{table}/rows/{pk}")
async def update_row(
    table: str,
    pk: str,
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    """Actualiza fila por PK (columna 'id')."""
    tbl = _check_table(table)
    if not body:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nada que actualizar")
    cols = [_safe_ident(k, "columna") for k in body.keys()]
    set_sql = ", ".join(f'"{c}" = :{c}' for c in cols)
    params = dict(body)
    params["_pk"] = pk
    sql = f'UPDATE "{tbl}" SET {set_sql} WHERE "id" = :_pk RETURNING *'
    result = await db.execute(text(sql), params)
    row = result.mappings().first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fila no encontrada")
    await db.commit()
    return {k: _jsonify(v) for k, v in dict(row).items()}


@router.delete("/tables/{table}/rows/{pk}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_row(
    table: str,
    pk: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    """Elimina fila por PK. Respeta FKs (RESTRICT lanzara error SQL)."""
    tbl = _check_table(table)
    sql = f'DELETE FROM "{tbl}" WHERE "id" = :_pk'
    result = await db.execute(text(sql), {"_pk": pk})
    if result.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fila no encontrada")
    await db.commit()


@router.post("/query", response_model=SqlQueryResult)
async def run_query(
    payload: SqlQueryRequest,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_role(UserRole.admin)),
):
    """Ejecuta SQL arbitrario. DDL destructiva bloqueada salvo allow_destructive=true."""
    sql = payload.sql.strip().rstrip(";")
    if not sql:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "SQL vacio")
    if not payload.allow_destructive and DESTRUCTIVE_RE.search(sql):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Comando destructivo bloqueado. Marca 'allow_destructive=true' si estas seguro.",
        )

    started = time.time()
    status_str = "ok"
    try:
        result = await db.execute(text(sql), payload.params or {})
        if result.returns_rows:
            columns = list(result.keys())
            rows = [
                {col: _jsonify(val) for col, val in zip(columns, row)}
                for row in result.all()
            ]
            rowcount = len(rows)
        else:
            columns, rows = [], []
            rowcount = result.rowcount or 0
        await db.commit()
    except Exception as e:
        await db.rollback()
        status_str = "error"
        _log_query(current, sql, status_str, (time.time() - started) * 1000)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"SQL error: {e}")

    duration_ms = (time.time() - started) * 1000
    _log_query(current, sql, status_str, duration_ms)
    return SqlQueryResult(
        columns=columns, rows=rows, rowcount=int(rowcount), duration_ms=duration_ms
    )


@router.get("/tables/{table}/export.csv")
async def export_csv(
    table: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    """Export CSV streaming (no carga todo en memoria aunque sea grande)."""
    tbl = _check_table(table)
    result = await db.execute(text(f'SELECT * FROM "{tbl}" ORDER BY 1'))
    columns = list(result.keys())

    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(columns)
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)
        for row in result:
            writer.writerow([_jsonify(v) for v in row])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    headers = {"Content-Disposition": f'attachment; filename="{tbl}.csv"'}
    return StreamingResponse(generate(), media_type="text/csv", headers=headers)
