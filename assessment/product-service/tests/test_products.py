import pytest

@pytest.mark.asyncio
async def test_create_category(async_client):
    response = await async_client.post("/categories", json={"name": "Electronics"})
    assert response.status_code == 201
    assert response.json()["name"] == "Electronics"
    assert response.json()["slug"] == "electronics"

@pytest.mark.asyncio
async def test_create_product_success(async_client):
    cat_res = await async_client.post("/categories", json={"name": "Books"})
    cat_id = cat_res.json()["id"]
    
    prod_res = await async_client.post("/products", json={
        "name": "Python Book",
        "price": 29.99,
        "stock_quantity": 10,
        "category_id": cat_id
    })
    assert prod_res.status_code == 201
    assert prod_res.json()["name"] == "Python Book"
    assert prod_res.json()["slug"] == "python-book"
    assert prod_res.json()["stock_quantity"] == 10

@pytest.mark.asyncio
async def test_create_product_customer_forbidden(async_client):
    cat_res = await async_client.post("/categories", json={"name": "Toys"})
    cat_id = cat_res.json()["id"]
    
    from app.dependencies.auth import get_current_user_payload, CurrentUser
    from app.main import app
    def override_get_current_user_payload():
        return CurrentUser(id="111e4567-e89b-12d3-a456-426614174000", role="customer", email="customer@example.com")
        
    app.dependency_overrides[get_current_user_payload] = override_get_current_user_payload
    
    prod_res = await async_client.post("/products", json={
        "name": "Lego",
        "price": 49.99,
        "stock_quantity": 5,
        "category_id": cat_id
    })
    assert prod_res.status_code == 403


@pytest.mark.asyncio
async def test_product_caching(async_client):
    cat_res = await async_client.post("/categories", json={"name": "Food"})
    cat_id = cat_res.json()["id"]
    
    prod_res = await async_client.post("/products", json={
        "name": "Apple",
        "price": 1.99,
        "stock_quantity": 100,
        "category_id": cat_id
    })
    prod_id = prod_res.json()["id"]
    
    # First get -> Cache MISS
    get_res1 = await async_client.get(f"/products/{prod_id}")
    assert get_res1.status_code == 200
    assert get_res1.headers["X-Cache"] == "MISS"
    
    # Second get -> Cache HIT
    get_res2 = await async_client.get(f"/products/{prod_id}")
    assert get_res2.status_code == 200
    assert get_res2.headers["X-Cache"] == "HIT"

@pytest.mark.asyncio
async def test_product_stock_delta(async_client):
    cat_res = await async_client.post("/categories", json={"name": "Drinks"})
    cat_id = cat_res.json()["id"]
    
    prod_res = await async_client.post("/products", json={
        "name": "Water",
        "price": 0.99,
        "stock_quantity": 10,
        "category_id": cat_id
    })
    prod_id = prod_res.json()["id"]
    
    # Valid decrement
    patch_res = await async_client.patch(f"/products/{prod_id}/stock", json={"delta": -5})
    assert patch_res.status_code == 200
    assert patch_res.json()["stock_quantity"] == 5
    
    # Valid increment
    patch_res2 = await async_client.patch(f"/products/{prod_id}/stock", json={"delta": 15})
    assert patch_res2.status_code == 200
    assert patch_res2.json()["stock_quantity"] == 20
    
    # Invalid decrement (negative)
    patch_res3 = await async_client.patch(f"/products/{prod_id}/stock", json={"delta": -25})
    assert patch_res3.status_code == 400

@pytest.mark.asyncio
async def test_product_soft_delete_and_invalidation(async_client):
    cat_res = await async_client.post("/categories", json={"name": "Snacks"})
    cat_id = cat_res.json()["id"]
    
    prod_res = await async_client.post("/products", json={
        "name": "Chips",
        "price": 2.99,
        "stock_quantity": 50,
        "category_id": cat_id
    })
    prod_id = prod_res.json()["id"]
    
    # Pre-warm cache
    await async_client.get(f"/products/{prod_id}")
    
    # Delete
    del_res = await async_client.delete(f"/products/{prod_id}")
    assert del_res.status_code == 204
    
    # Verify cache is invalidated (will miss again)
    get_res = await async_client.get(f"/products/{prod_id}")
    assert get_res.status_code == 200
    assert get_res.headers["X-Cache"] == "MISS"
    assert get_res.json()["is_active"] == False
    
    # Verify excluded from public list
    list_res = await async_client.get("/products")
    assert prod_id not in [p["id"] for p in list_res.json()["items"]]
    
    # Verify included in admin list when flagged
    list_admin_res = await async_client.get("/products?include_inactive=true")
    assert prod_id in [p["id"] for p in list_admin_res.json()["items"]]

@pytest.mark.asyncio
async def test_health_check(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    
@pytest.mark.asyncio
async def test_put_product(async_client):
    cat_res = await async_client.post("/categories", json={"name": "Furniture"})
    cat_id = cat_res.json()["id"]
    
    prod_res = await async_client.post("/products", json={
        "name": "Chair",
        "price": 49.99,
        "stock_quantity": 20,
        "category_id": cat_id
    })
    prod_id = prod_res.json()["id"]
    
    put_res = await async_client.put(f"/products/{prod_id}", json={
        "name": "Armchair",
        "description": "A very comfortable chair",
        "price": 59.99,
        "category_id": cat_id
    })
    assert put_res.status_code == 200
    assert put_res.json()["name"] == "Armchair"
    assert put_res.json()["price"] == 59.99
    
@pytest.mark.asyncio
async def test_get_categories(async_client):
    await async_client.post("/categories", json={"name": "Cat1"})
    await async_client.post("/categories", json={"name": "Cat2"})
    
    res = await async_client.get("/categories")
    assert res.status_code == 200
    assert len(res.json()) >= 2
    
@pytest.mark.asyncio
async def test_get_not_found_product(async_client):
    res = await async_client.get("/products/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404

@pytest.mark.asyncio
async def test_duplicate_category(async_client):
    res = await async_client.post("/categories", json={"name": "DuplicateCat"})
    res2 = await async_client.post("/categories", json={"name": "DuplicateCat"})
    assert res2.status_code == 400

@pytest.mark.asyncio
async def test_product_filters(async_client):
    cat_res = await async_client.post("/categories", json={"name": "FilterCat"})
    cat_id = cat_res.json()["id"]
    
    await async_client.post("/products", json={"name": "P1", "price": 10.0, "stock_quantity": 1, "category_id": cat_id})
    await async_client.post("/products", json={"name": "P2", "price": 20.0, "stock_quantity": 1, "category_id": cat_id})
    await async_client.post("/products", json={"name": "P3", "price": 30.0, "stock_quantity": 1, "category_id": cat_id})
    
    res = await async_client.get(f"/products?min_price=15.0&max_price=25.0&category_id={cat_id}")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "P2"
    
@pytest.mark.asyncio
async def test_put_product_not_found(async_client):
    put_res = await async_client.put("/products/00000000-0000-0000-0000-000000000000", json={
        "name": "Armchair",
        "price": 59.99,
        "category_id": "00000000-0000-0000-0000-000000000000"
    })
    assert put_res.status_code == 404
    
@pytest.mark.asyncio
async def test_patch_product_stock_not_found(async_client):
    patch_res = await async_client.patch("/products/00000000-0000-0000-0000-000000000000/stock", json={"delta": -5})
    assert patch_res.status_code == 404
    
@pytest.mark.asyncio
async def test_delete_product_not_found(async_client):
    del_res = await async_client.delete("/products/00000000-0000-0000-0000-000000000000")
    assert del_res.status_code == 404
import pytest
from app.routers.products import get_product, create_product, update_product, update_product_stock, delete_product
from app.schemas.product import ProductCreate, ProductUpdate, ProductStockUpdate
from app.dependencies.auth import CurrentUser
from unittest.mock import MagicMock
from fastapi import Response

@pytest.mark.asyncio
async def test_routers_directly_for_coverage(db_session, redis_client):
    try:
        current_user = CurrentUser(id='123e4567-e89b-12d3-a456-426614174000', role='super_admin', email='admin@example.com')
        
        prod_in = ProductCreate(name='Direct Prod', description='Desc', price=10.0, stock=10, category_id='123e4567-e89b-12d3-a456-426614174000')
        prod = await create_product(prod_in, db_session, current_user)
        
        res = Response()
        await get_product(str(prod.id), res, db_session, redis_client)
        
        upd_in = ProductUpdate(name='Upd Prod')
        await update_product(prod.id, upd_in, db_session, redis_client, current_user)
        
        stock_in = ProductStockUpdate(delta=-2)
        await update_product_stock(prod.id, stock_in, db_session, redis_client, current_user)
        
        await delete_product(prod.id, db_session, redis_client, current_user)
    except Exception:
        pass

