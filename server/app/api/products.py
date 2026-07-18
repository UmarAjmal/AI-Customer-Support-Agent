"""
app/api/products.py — Product listing, filters, details, and modifications.
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_admin
from app.core import ttl_cache
from app.database import schemas
from app.services import product_service

router = APIRouter(prefix="/products", tags=["Products"])

_CATALOG_TTL = 60.0


@router.get("", response_model=schemas.StandardResponse)
async def list_products(
    response: Response,
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(None, description="Search query matching name/description"),
    category: Optional[str] = Query(None, description="Filter products by Category Name"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    sort_by: Optional[str] = Query(None, description="Sorting parameter: price_asc, price_desc, rating"),
    page: int = Query(1, ge=1, description="Page index"),
    page_size: int = Query(12, ge=1, le=50, description="Items per page")
):
    """Retrieve filtered, paginated list of catalog products."""
    cache_key = f"products:{search}:{category}:{min_price}:{max_price}:{sort_by}:{page}:{page_size}"
    cached = ttl_cache.get(cache_key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = "public, max-age=30"
        return schemas.StandardResponse(
            success=True,
            message="Products fetched successfully",
            data=cached,
        )

    products, total = await product_service.list_products(
        db=db,
        search=search,
        category=category,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
        page=page,
        page_size=page_size
    )
    
    serialized = [schemas.ProductResponse.model_validate(p).model_dump(mode="json") for p in products]
    result_data = {
        "items": serialized,
        "total": total,
        "page": page,
        "page_size": page_size
    }
    ttl_cache.set(cache_key, result_data, _CATALOG_TTL)
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = "public, max-age=30"
    
    return schemas.StandardResponse(
        success=True,
        message="Products fetched successfully",
        data=result_data
    )


@router.get("/categories", response_model=schemas.StandardResponse)
async def list_categories(response: Response, db: AsyncSession = Depends(get_db)):
    """Fetch distinct category items."""
    cached = ttl_cache.get("categories")
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = "public, max-age=60"
        return schemas.StandardResponse(
            success=True,
            message="Categories fetched successfully",
            data=cached,
        )

    cats = await product_service.list_categories(db)
    serialized = [schemas.CategoryResponse.model_validate(c).model_dump(mode="json") for c in cats]
    ttl_cache.set("categories", serialized, 120.0)
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = "public, max-age=60"
    return schemas.StandardResponse(
        success=True,
        message="Categories fetched successfully",
        data=serialized
    )


@router.get("/{id}", response_model=schemas.StandardResponse)
async def get_product(id: UUID, response: Response, db: AsyncSession = Depends(get_db)):
    """Fetch a single product detail card by UUID."""
    cache_key = f"product:{id}"
    cached = ttl_cache.get(cache_key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = "public, max-age=30"
        return schemas.StandardResponse(
            success=True,
            message="Product found",
            data=cached,
        )

    product = await product_service.get_product(db, id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {id} not found."
        )
    
    res = schemas.ProductResponse.model_validate(product).model_dump(mode="json")
    ttl_cache.set(cache_key, res, _CATALOG_TTL)
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = "public, max-age=30"
    return schemas.StandardResponse(
        success=True,
        message="Product found",
        data=res
    )


@router.post("", response_model=schemas.StandardResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    prod_in: schemas.ProductCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Create a new product card in database. Admin restricted."""
    product = await product_service.create_new_product(db, prod_in)
    ttl_cache.invalidate("products:")
    ttl_cache.invalidate("categories")
    res = schemas.ProductResponse.model_validate(product)
    return schemas.StandardResponse(
        success=True,
        message="Product created successfully",
        data=res
    )


@router.put("/{id}", response_model=schemas.StandardResponse)
async def update_product(
    id: UUID,
    update_data: schemas.ProductUpdate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Update details of an existing product card. Admin restricted."""
    product = await product_service.update_existing_product(db, id, update_data)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {id} not found."
        )
    
    ttl_cache.invalidate("products:")
    ttl_cache.invalidate(f"product:{id}")
    ttl_cache.invalidate("categories")
    res = schemas.ProductResponse.model_validate(product)
    return schemas.StandardResponse(
        success=True,
        message="Product updated successfully",
        data=res
    )


@router.delete("/{id}", response_model=schemas.StandardResponse)
async def delete_product(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Permanently delete a product card. Admin restricted."""
    success = await product_service.remove_product(db, id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {id} not found."
        )
    
    ttl_cache.invalidate("products:")
    ttl_cache.invalidate(f"product:{id}")
    ttl_cache.invalidate("categories")
    return schemas.StandardResponse(
        success=True,
        message="Product deleted successfully"
    )
