"""
Carga inicial de datos: crea usuario admin y productos demo.
Uso: `python seed.py` (dentro del contenedor o con .env local).
Idempotente: no duplica si ya existen.
"""
import asyncio
from decimal import Decimal

from sqlalchemy import select

from auth import hash_password
from config import settings
from database import AsyncSessionLocal, engine
from models import Client, Product, User, UserRole

DEMO_PRODUCTS = [
    ("Laptop Lenovo IdeaPad 3", "Laptop 14'' Ryzen 5 8GB RAM 512GB SSD", "12999.00", 8, "Electronica",
     "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400"),
    ("Mouse Logitech M185", "Mouse inalambrico USB, pilas incluidas", "349.00", 50, "Accesorios",
     "https://images.unsplash.com/photo-1527814050087-3793815479db?w=400"),
    ("Teclado mecanico RK61", "Teclado 60% RGB bluetooth, switches rojos", "899.00", 20, "Accesorios",
     "https://images.unsplash.com/photo-1595044426077-d36d9236d44e?w=400"),
    ("Monitor AOC 24''", "Monitor Full HD 75Hz IPS", "2899.00", 12, "Electronica",
     "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400"),
    ("Silla Gamer", "Silla ergonomica con reposacabezas", "3499.00", 6, "Muebles",
     "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400"),
    ("Audifonos HyperX Cloud", "Audifonos gaming con microfono", "1499.00", 15, "Accesorios",
     "https://images.unsplash.com/photo-1583394838336-acd977736f90?w=400"),
    ("Webcam Logitech C270", "Camara web 720p USB", "749.00", 18, "Electronica",
     "https://images.unsplash.com/photo-1557825835-70d97c4aa567?w=400"),
    ("SSD Kingston 480GB", "Disco solido SATA 2.5''", "699.00", 25, "Almacenamiento",
     "https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?w=400"),
    ("Memoria RAM DDR4 16GB", "RAM 3200MHz UDIMM", "1199.00", 10, "Componentes",
     "https://images.unsplash.com/photo-1541029071515-84cc58f00ab3?w=400"),
    ("Impresora HP Deskjet", "Impresora multifuncional WiFi", "2299.00", 4, "Oficina",
     "https://images.unsplash.com/photo-1612815154858-60aa4c59eaa6?w=400"),
    ("Cable HDMI 2m", "Cable HDMI 2.0 4K 60Hz", "129.00", 100, "Accesorios",
     "https://images.unsplash.com/photo-1558002038-1055907df827?w=400"),
    ("Router TP-Link AC1200", "Router dual band WiFi 5", "899.00", 14, "Redes",
     "https://images.unsplash.com/photo-1606859191213-c4d9b6d8efc5?w=400"),
    ("USB Hub 4 puertos", "Hub USB 3.0 de aluminio", "299.00", 35, "Accesorios",
     "https://images.unsplash.com/photo-1625948515291-69613efd103f?w=400"),
    ("Bocina Bluetooth", "Bocina portatil resistente al agua", "599.00", 22, "Audio",
     "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400"),
    ("Power Bank 20000mAh", "Bateria externa con carga rapida", "499.00", 30, "Accesorios",
     "https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?w=400"),
]


async def seed():
    async with AsyncSessionLocal() as db:
        # Admin
        r = await db.execute(select(User).where(User.email == settings.admin_email.lower()))
        admin = r.scalar_one_or_none()
        if not admin:
            admin = User(
                email=settings.admin_email.lower(),
                password_hash=hash_password(settings.admin_password),
                role=UserRole.admin,
            )
            db.add(admin)
            await db.flush()
            db.add(Client(user_id=admin.id, name="Administrador"))
            print(f"  + admin creado: {settings.admin_email}")
        else:
            print(f"  = admin ya existia: {settings.admin_email}")

        # Productos
        r = await db.execute(select(Product).limit(1))
        if r.scalar_one_or_none():
            print("  = ya hay productos, salto seed de catalogo")
        else:
            for name, desc, price, stock, cat, img in DEMO_PRODUCTS:
                db.add(
                    Product(
                        name=name,
                        description=desc,
                        price=Decimal(price),
                        stock=stock,
                        category=cat,
                        image_url=img,
                    )
                )
            print(f"  + {len(DEMO_PRODUCTS)} productos demo creados")

        await db.commit()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
    print("Seed completado.")
