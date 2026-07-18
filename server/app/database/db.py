"""
app/database/db.py — Async SQLAlchemy engine and session factory.
Includes automatic seeding function for categories, products, and FAQs.
"""
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import select, func
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# ── Engine ────────────────────────────────────────────────────────────────────
# Smaller pool + keepalives: faster first queries to remote Supabase
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
    pool_timeout=15,
    connect_args={
        "statement_cache_size": 0,
        "timeout": 10,
        "command_timeout": 10,
    },
)

# ── Session factory ───────────────────────────────────────────────────────────
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── Declarative base ──────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def create_all_tables() -> None:
    """Create all tables defined by ORM models."""
    from app.database import models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database.tables_created")


async def seed_dummy_data() -> None:
    """Seed categories, products, FAQs, sample orders & returns if tables are empty."""
    from app.database import models
    from datetime import date, timedelta
    from decimal import Decimal

    async with AsyncSessionFactory() as session:
        try:
            # Fast path: catalog already populated — skip all seed queries
            stmt = select(func.count()).select_from(models.Product)
            res = await session.execute(stmt)
            if res.scalar_one() > 0:
                logger.info("database.seed_skipped", reason="products_already_present")
                return

            # 1. Seed Categories
            stmt = select(func.count()).select_from(models.Category)
            res = await session.execute(stmt)
            if res.scalar_one() == 0:
                logger.info("database.seeding_categories")
                cats = [
                    models.Category(name="Mobiles", slug="mobiles", icon="📱", product_count=4),
                    models.Category(name="Laptops", slug="laptops", icon="💻", product_count=3),
                    models.Category(name="Fashion", slug="fashion", icon="👕", product_count=2),
                    models.Category(name="Shoes", slug="shoes", icon="👟", product_count=3),
                    models.Category(name="Home & Living", slug="home-living", icon="🏠", product_count=2),
                    models.Category(name="Electronics", slug="electronics", icon="🔌", product_count=3),
                ]
                session.add_all(cats)
                await session.commit()

            # 2. Seed Products
            stmt = select(func.count()).select_from(models.Product)
            res = await session.execute(stmt)
            if res.scalar_one() == 0:
                logger.info("database.seeding_products")
                prods = [
                    models.Product(
                        name="Samsung Galaxy S24",
                        description='Latest Samsung flagship with AI features, 6.2" Dynamic AMOLED, 50MP camera',
                        price=Decimal("85000.00"),
                        original_price=Decimal("95000.00"),
                        category="Mobiles",
                        brand="Samsung",
                        stock_quantity=15,
                        is_featured=True,
                        rating=Decimal("4.70"),
                        review_count=234,
                        image_url="https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?q=80&w=600"
                    ),
                    models.Product(
                        name="iPhone 15 Pro",
                        description="Apple A17 Pro chip, Titanium design, 48MP Main camera with Photonic Engine",
                        price=Decimal("175000.00"),
                        original_price=Decimal("185000.00"),
                        category="Mobiles",
                        brand="Apple",
                        stock_quantity=8,
                        is_featured=True,
                        rating=Decimal("4.90"),
                        review_count=456,
                        image_url="https://images.unsplash.com/photo-1510557880182-3d4d3cba35a5?q=80&w=600"
                    ),
                    models.Product(
                        name="Google Pixel 8",
                        description="Google Tensor G3, best-in-class AI camera, 7 years of OS updates",
                        price=Decimal("125000.00"),
                        original_price=Decimal("140000.00"),
                        category="Mobiles",
                        brand="Google",
                        stock_quantity=12,
                        is_featured=True,
                        rating=Decimal("4.60"),
                        review_count=98,
                        image_url="https://images.unsplash.com/photo-1598327105666-5b89351aff97?q=80&w=600"
                    ),
                    models.Product(
                        name="Xiaomi Redmi Note 13",
                        description="AMOLED display, 108MP camera, long battery — great value mid-range",
                        price=Decimal("45000.00"),
                        original_price=Decimal("52000.00"),
                        category="Mobiles",
                        brand="Xiaomi",
                        stock_quantity=40,
                        is_featured=False,
                        rating=Decimal("4.30"),
                        review_count=210,
                        image_url="https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?q=80&w=600"
                    ),
                    models.Product(
                        name="MacBook Pro M3",
                        description="Apple M3 chip, 16GB RAM, 512GB SSD, 14-inch Liquid Retina XDR",
                        price=Decimal("350000.00"),
                        original_price=Decimal("380000.00"),
                        category="Laptops",
                        brand="Apple",
                        stock_quantity=3,
                        is_featured=True,
                        rating=Decimal("4.80"),
                        review_count=123,
                        image_url="https://images.unsplash.com/photo-1517336714731-489689fd1ca8?q=80&w=600"
                    ),
                    models.Product(
                        name="Dell XPS 15",
                        description="Intel Core i7, 16GB RAM, 512GB SSD, OLED display, thin and light",
                        price=Decimal("185000.00"),
                        original_price=Decimal("200000.00"),
                        category="Laptops",
                        brand="Dell",
                        stock_quantity=6,
                        is_featured=True,
                        rating=Decimal("4.60"),
                        review_count=67,
                        image_url="https://images.unsplash.com/photo-1593642632823-8f785ba67e45?q=80&w=600"
                    ),
                    models.Product(
                        name="HP Pavilion 15",
                        description="Intel Core i5, 16GB RAM, 512GB SSD — reliable everyday laptop",
                        price=Decimal("125000.00"),
                        original_price=Decimal("145000.00"),
                        category="Laptops",
                        brand="HP",
                        stock_quantity=10,
                        is_featured=False,
                        rating=Decimal("4.20"),
                        review_count=55,
                        image_url="https://images.unsplash.com/photo-1496181133206-80ce9b88a853?q=80&w=600"
                    ),
                    models.Product(
                        name="Nike Air Max 270",
                        description="Lightweight running shoe with Max Air cushioning for all-day comfort",
                        price=Decimal("12000.00"),
                        original_price=Decimal("15000.00"),
                        category="Shoes",
                        brand="Nike",
                        stock_quantity=25,
                        is_featured=False,
                        rating=Decimal("4.50"),
                        review_count=89,
                        image_url="https://images.unsplash.com/photo-1542291026-7eec264c27ff?q=80&w=600"
                    ),
                    models.Product(
                        name="Adidas Ultra Boost",
                        description="Boost midsole for ultimate energy return, Primeknit upper",
                        price=Decimal("14000.00"),
                        original_price=Decimal("18000.00"),
                        category="Shoes",
                        brand="Adidas",
                        stock_quantity=20,
                        is_featured=False,
                        rating=Decimal("4.40"),
                        review_count=112,
                        image_url="https://images.unsplash.com/photo-1608231387042-66d1773070a5?q=80&w=600"
                    ),
                    models.Product(
                        name="Puma RS-X Sneakers",
                        description="Chunky retro sneakers with cushioned sole and bold colorways",
                        price=Decimal("11000.00"),
                        original_price=Decimal("13500.00"),
                        category="Shoes",
                        brand="Puma",
                        stock_quantity=18,
                        is_featured=False,
                        rating=Decimal("4.35"),
                        review_count=64,
                        image_url="https://images.unsplash.com/photo-1606107557195-0e29a4b5b4aa?q=80&w=600"
                    ),
                    models.Product(
                        name="Cotton Casual Shirt",
                        description="Breathable cotton shirt for everyday wear, slim fit",
                        price=Decimal("3500.00"),
                        original_price=Decimal("4500.00"),
                        category="Fashion",
                        brand="ShopEase",
                        stock_quantity=50,
                        is_featured=True,
                        rating=Decimal("4.10"),
                        review_count=76,
                        image_url="https://images.unsplash.com/photo-1596755094514-f87e34085b2c?q=80&w=600"
                    ),
                    models.Product(
                        name="Women's Summer Dress",
                        description="Light floral summer dress, soft fabric, available in multiple sizes",
                        price=Decimal("5500.00"),
                        original_price=Decimal("7000.00"),
                        category="Fashion",
                        brand="ShopEase",
                        stock_quantity=35,
                        is_featured=True,
                        rating=Decimal("4.50"),
                        review_count=132,
                        image_url="https://images.unsplash.com/photo-1595777457583-95e059d581b8?q=80&w=600"
                    ),
                    models.Product(
                        name="Minimal Desk Lamp",
                        description="LED desk lamp with adjustable brightness and warm/cool modes",
                        price=Decimal("4500.00"),
                        original_price=Decimal("6000.00"),
                        category="Home & Living",
                        brand="ShopEase Home",
                        stock_quantity=22,
                        is_featured=True,
                        rating=Decimal("4.40"),
                        review_count=41,
                        image_url="https://images.unsplash.com/photo-1507473885765-e6ed057f782c?q=80&w=600"
                    ),
                    models.Product(
                        name="Ceramic Coffee Mug Set",
                        description="Set of 4 matte ceramic mugs — dishwasher safe",
                        price=Decimal("2800.00"),
                        original_price=Decimal("3500.00"),
                        category="Home & Living",
                        brand="ShopEase Home",
                        stock_quantity=60,
                        is_featured=False,
                        rating=Decimal("4.25"),
                        review_count=88,
                        image_url="https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?q=80&w=600"
                    ),
                    models.Product(
                        name="Sony WH-1000XM5",
                        description="Industry-leading noise cancelling headphones with 30-hour battery",
                        price=Decimal("95000.00"),
                        original_price=Decimal("110000.00"),
                        category="Electronics",
                        brand="Sony",
                        stock_quantity=9,
                        is_featured=True,
                        rating=Decimal("4.85"),
                        review_count=320,
                        image_url="https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?q=80&w=600"
                    ),
                    models.Product(
                        name="Anker PowerBank 20000mAh",
                        description="Fast-charge portable power bank with dual USB-C and USB-A ports",
                        price=Decimal("7500.00"),
                        original_price=Decimal("9000.00"),
                        category="Electronics",
                        brand="Anker",
                        stock_quantity=45,
                        is_featured=False,
                        rating=Decimal("4.55"),
                        review_count=190,
                        image_url="https://images.unsplash.com/photo-1609091839311-b48b1f709e43?q=80&w=600"
                    ),
                    models.Product(
                        name="Logitech MX Master 3S",
                        description="Ergonomic wireless mouse with MagSpeed scrolling and quiet clicks",
                        price=Decimal("28000.00"),
                        original_price=Decimal("32000.00"),
                        category="Electronics",
                        brand="Logitech",
                        stock_quantity=14,
                        is_featured=True,
                        rating=Decimal("4.75"),
                        review_count=145,
                        image_url="https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?q=80&w=600"
                    ),
                ]
                session.add_all(prods)
                await session.commit()

            # 3. Seed FAQs
            stmt = select(func.count()).select_from(models.FAQ)
            res = await session.execute(stmt)
            if res.scalar_one() == 0:
                logger.info("database.seeding_faqs")
                faqs = [
                    models.FAQ(
                        question="What is the shipping policy of ShopEase?",
                        answer="Standard shipping is FREE all over Pakistan and takes 3-5 business days. Express shipping takes 1-2 business days and costs Rs. 299.",
                        category="Shipping"
                    ),
                    models.FAQ(
                        question="How do I return an item?",
                        answer="You can request a return for any delivered item within 30 days of delivery. Returns are free of charge. Contact us to schedule a return parcel pickup.",
                        category="Returns"
                    ),
                    models.FAQ(
                        question="What payment options do you support?",
                        answer="We support Cash on Delivery (COD) across Pakistan, EasyPaisa, JazzCash, and all major Credit/Debit Cards (Visa/Mastercard).",
                        category="Payments"
                    ),
                    models.FAQ(
                        question="How do I track my order parcel?",
                        answer="Once shipped, you will receive a TCS or DHL tracking number. You can ask this AI support widget with your Order number (e.g. SE-9821) to check live tracking details.",
                        category="Tracking"
                    ),
                    models.FAQ(
                        question="What is your contact support details?",
                        answer="Email support is available at support@shopease.pk. You can also call or WhatsApp us at +92 300 1234567 between Mon-Sat, 9:00 AM - 6:00 PM.",
                        category="Support"
                    ),
                    models.FAQ(
                        question="Do you offer Cash on Delivery?",
                        answer="Yes, Cash on Delivery (COD) is available across Pakistan for orders under Rs. 100,000.",
                        category="Payments"
                    ),
                    models.FAQ(
                        question="How long does a refund take?",
                        answer="Once your return is approved and received, refunds are processed within 5-7 business days to the original payment method.",
                        category="Returns"
                    ),
                    models.FAQ(
                        question="Can I cancel my order?",
                        answer="You can cancel an order while it is still in 'processing' status. Once shipped, cancellation is not possible — you can request a return after delivery.",
                        category="Orders"
                    ),
                    models.FAQ(
                        question="Do products come with warranty?",
                        answer="Yes. Electronics and mobiles include manufacturer warranty (usually 1 year). Fashion and home items follow our 30-day return policy.",
                        category="Products"
                    ),
                ]
                session.add_all(faqs)
                await session.commit()

            # 4. Seed sample orders (for AI tracking demos) if empty
            stmt = select(func.count()).select_from(models.Order)
            res = await session.execute(stmt)
            if res.scalar_one() == 0:
                logger.info("database.seeding_orders")
                products = (await session.execute(select(models.Product))).scalars().all()
                by_name = {p.name: p for p in products}

                def item(name: str, qty: int, price: float) -> dict:
                    p = by_name.get(name)
                    return {
                        "product_id": str(p.id) if p else None,
                        "name": name,
                        "quantity": qty,
                        "price": price,
                    }

                orders = [
                    models.Order(
                        order_number="SE-9821",
                        customer_name="Ali Khan",
                        customer_email="ali@example.com",
                        customer_phone="+92 300 1112233",
                        items=[
                            item("Sony WH-1000XM5", 1, 95000.00),
                            item("Cotton Casual Shirt", 2, 3500.00),
                        ],
                        total_amount=Decimal("102000.00"),
                        status="shipped",
                        payment_method="COD",
                        payment_status="pending",
                        shipping_address={
                            "street": "12 Gulberg III",
                            "city": "Lahore",
                            "province": "Punjab",
                            "postal_code": "54000",
                        },
                        tracking_number="TCS-88392019-SE",
                        estimated_delivery=date.today() + timedelta(days=2),
                    ),
                    models.Order(
                        order_number="SE-4392",
                        customer_name="Sara Ahmed",
                        customer_email="sara@example.com",
                        customer_phone="+92 321 4455667",
                        items=[item("Samsung Galaxy S24", 1, 85000.00)],
                        total_amount=Decimal("85000.00"),
                        status="delivered",
                        payment_method="JazzCash",
                        payment_status="paid",
                        shipping_address={
                            "street": "45 Clifton Block 5",
                            "city": "Karachi",
                            "province": "Sindh",
                            "postal_code": "75600",
                        },
                        tracking_number="DHL-55221100-SE",
                        estimated_delivery=date.today() - timedelta(days=3),
                    ),
                    models.Order(
                        order_number="ORD-1023",
                        customer_name="Hassan Raza",
                        customer_email="hassan@example.com",
                        customer_phone="+92 333 7788990",
                        items=[
                            item("Nike Air Max 270", 1, 12000.00),
                            item("Ceramic Coffee Mug Set", 1, 2800.00),
                        ],
                        total_amount=Decimal("14800.00"),
                        status="processing",
                        payment_method="Card",
                        payment_status="paid",
                        shipping_address={
                            "street": "88 F-7 Markaz",
                            "city": "Islamabad",
                            "province": "ICT",
                            "postal_code": "44000",
                        },
                        tracking_number=None,
                        estimated_delivery=date.today() + timedelta(days=5),
                    ),
                    models.Order(
                        order_number="ORD-2045",
                        customer_name="Fatima Noor",
                        customer_email="fatima@example.com",
                        customer_phone="+92 301 5566778",
                        items=[item("MacBook Pro M3", 1, 350000.00)],
                        total_amount=Decimal("350000.00"),
                        status="in_transit",
                        payment_method="EasyPaisa",
                        payment_status="paid",
                        shipping_address={
                            "street": "3 Model Town",
                            "city": "Lahore",
                            "province": "Punjab",
                            "postal_code": "54700",
                        },
                        tracking_number="TCS-99112233-SE",
                        estimated_delivery=date.today() + timedelta(days=1),
                    ),
                ]
                session.add_all(orders)
                await session.commit()

                delivered = (
                    await session.execute(
                        select(models.Order).where(models.Order.order_number == "SE-4392")
                    )
                ).scalar_one_or_none()
                if delivered:
                    session.add(
                        models.Return(
                            return_number="RET-1001",
                            order_id=delivered.id,
                            reason="Screen has dead pixels on delivery",
                            status="approved",
                            refund_amount=Decimal("85000.00"),
                        )
                    )
                    await session.commit()

        except Exception as e:
            await session.rollback()
            logger.error("database.seeding_failed", error=str(e))
        finally:
            await session.close()


async def dispose_engine() -> None:
    """Gracefully close all pooled connections on shutdown."""
    await engine.dispose()
    logger.info("database.engine_disposed")
