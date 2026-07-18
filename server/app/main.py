"""
app/main.py — Main FastAPI Entry Point.
Initializes structured logging, mounts API routers, manages CORS policies,
and configures global HTTP error filters.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logger import configure_logging, get_logger
from app.database.db import create_all_tables, dispose_engine

# Import Routers
from app.api import auth, products, orders, returns, users, uploads, chat

logger = get_logger(__name__)


# ─── Lifespan Context Manager ────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize logging configuration
    configure_logging()
    logger.info("app.startup", status="initializing", version=settings.APP_VERSION)
    
    # 2. Setup database tables (dev-only fallback, production uses migrations)
    try:
        from app.database.db import AsyncSessionFactory
        from app.database import models
        from sqlalchemy import select, func

        # Quick check: if the Product table exists and is seeded, we can skip startup DB initialization entirely
        async with AsyncSessionFactory() as session:
            stmt = select(func.count()).select_from(models.Product)
            res = await session.execute(stmt)
            has_data = res.scalar_one() > 0
            
        if has_data:
            logger.info("app.database_check", status="ready", message="Database already initialized and seeded.")
        else:
            # Table exists but empty, run seed only
            from app.database.db import seed_dummy_data
            await seed_dummy_data()
            logger.info("app.database_check", status="seeded")
    except Exception:
        # UndefinedTable or connection error — tables do not exist or database is cold.
        # Run full initialization and seeding.
        logger.info("app.database_check", status="missing_tables", message="Tables missing or connection cold. Initializing database...")
        try:
            from app.database.db import seed_dummy_data
            await create_all_tables()
            await seed_dummy_data()
        except Exception as e:
            logger.error("app.database_connection_failed", error=str(e), message="Table initialization and seeding skipped.")

    # Warm catalog in background — never block request readiness
    async def _warm_catalog_cache() -> None:
        try:
            from app.core import ttl_cache
            from app.database.db import AsyncSessionFactory
            from app.services import product_service
            from app.database import schemas

            async with AsyncSessionFactory() as session:
                products, total = await product_service.list_products(
                    db=session, page=1, page_size=50
                )
                items = [
                    schemas.ProductResponse.model_validate(p).model_dump(mode="json")
                    for p in products
                ]
                ttl_cache.set(
                    "products:None:None:None:None:None:1:50",
                    {"items": items, "total": total, "page": 1, "page_size": 50},
                    60.0,
                )
                cats = await product_service.list_categories(session)
                ttl_cache.set(
                    "categories",
                    [
                        schemas.CategoryResponse.model_validate(c).model_dump(mode="json")
                        for c in cats
                    ],
                    120.0,
                )
            logger.info("app.catalog_cache_warmed", products=total)
        except Exception as warm_err:
            logger.warning("app.catalog_cache_warm_failed", error=str(warm_err))

    import asyncio
    asyncio.create_task(_warm_catalog_cache())
    
    yield
    
    # 3. Graceful shutdown
    logger.info("app.shutdown", status="finalizing")
    await dispose_engine()


# ─── App Declaration ─────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# ─── CORS Middleware ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Static files mounting ────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")


# ─── Global Error Handling Middleware ──────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Interceptors unhandled exceptions to prevent stack trace leakages in responses."""
    logger.exception("unhandled_error_intercepted", path=request.url.path, error=str(exc))
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An unexpected error occurred. Please try again later.",
            "data": None,
            "errors": [str(exc)] if settings.DEBUG else None
        }
    )


# ─── Mount Routes ──────────────────────────────────────────────────────────────
app.include_router(auth.router,     prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(orders.router,   prefix="/api")
app.include_router(returns.router,  prefix="/api")
app.include_router(users.router,    prefix="/api")
app.include_router(uploads.router,  prefix="/api")
app.include_router(chat.router,     prefix="/api")


# ─── Root Check ────────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root_health():
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }
