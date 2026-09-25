from fastapi import FastAPI
import os
import time

app = FastAPI(title="BugForge Sample Target")


@app.get("/health")
def health():
    return {"status": "ok", "service": "sample-target"}


@app.get("/api/products")
def get_products():
    """Simulate a slow DB query."""
    time.sleep(0.05)
    return [{"id": i, "name": f"Product {i}", "price": i * 9.99} for i in range(1, 11)]


@app.get("/api/orders")
def get_orders():
    return [{"id": i, "product_id": i, "qty": i} for i in range(1, 6)]
