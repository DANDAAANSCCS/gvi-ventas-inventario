import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import auth_router, clients, inventory, orders, products, reports

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="GVI API",
    description="API REST del Sistema de Gestion de Ventas e Inventario",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(products.router)
app.include_router(clients.router)
app.include_router(orders.router)
app.include_router(inventory.router)
app.include_router(reports.router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}


@app.get("/", tags=["health"])
async def root():
    return {"service": "gvi-api", "docs": "/docs"}
