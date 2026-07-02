"""Integration tests for FastAPI REST endpoints."""

from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient):
    """Tests GET /api/health endpoint."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "tools_count" in data
    assert "available_providers" in data


def test_categories_endpoint(client: TestClient):
    """Tests GET /api/categories endpoint."""
    res = client.get("/api/categories")
    assert res.status_code == 200
    data = res.json()
    assert "categories" in data
    assert len(data["categories"]) > 0


def test_expenses_api_lifecycle(client: TestClient):
    """Tests expense creation, retrieval, and deletion through REST API."""
    # 1. Create
    payload = {
        "amount": 28.50,
        "category": "Food",
        "subcategory": "Lunch",
        "note": "Sweetgreen bowl",
        "date": "2026-08-25",
    }
    create_res = client.post("/api/expenses", json=payload)
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["amount"] == 28.50
    assert created["category"] == "Food"
    expense_id = created["id"]

    # 2. Get single
    get_res = client.get(f"/api/expenses/{expense_id}")
    assert get_res.status_code == 200
    assert get_res.json()["note"] == "Sweetgreen bowl"

    # 3. List
    list_res = client.get("/api/expenses?category=Food&limit=10")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(e["id"] == expense_id for e in list_data["expenses"])

    # 4. Update
    put_res = client.put(f"/api/expenses/{expense_id}", json={"amount": 32.00, "note": "Sweetgreen + Drink"})
    assert put_res.status_code == 200
    assert put_res.json()["amount"] == 32.00

    # 5. Delete
    del_res = client.delete(f"/api/expenses/{expense_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 6. Verify 404
    get_del_res = client.get(f"/api/expenses/{expense_id}")
    assert get_del_res.status_code == 404


def test_budgets_api(client: TestClient):
    """Tests budget retrieval and setting via REST API."""
    # Set budget
    post_res = client.post("/api/budgets", json={"category": "Utilities", "limit_amount": 180.00})
    assert post_res.status_code == 200
    assert post_res.json()["category"] == "Utilities"
    assert post_res.json()["limit_amount"] == 180.00

    # List budgets
    get_res = client.get("/api/budgets")
    assert get_res.status_code == 200
    data = get_res.json()
    assert "budgets" in data
    assert any(b["category"] == "Utilities" for b in data["budgets"])


def test_seed_and_clear_endpoints(client: TestClient):
    """Tests POST /api/seed and POST /api/clear endpoints."""
    # 1. Clear database
    clear_res = client.post("/api/clear")
    assert clear_res.status_code == 200
    assert clear_res.json()["success"] is True

    # Confirm empty summary
    summary_empty = client.get("/api/summary").json()
    assert summary_empty["total_spent_this_month"] == 0.0
    assert summary_empty["total_transactions_this_month"] == 0

    # 2. Seed database
    seed_res = client.post("/api/seed")
    assert seed_res.status_code == 200
    assert seed_res.json()["seeded_expenses"] > 0
    assert seed_res.json()["seeded_budgets"] > 0

    # Confirm populated summary
    summary_seeded = client.get("/api/summary").json()
    assert summary_seeded["total_spent_this_month"] > 0
    assert summary_seeded["total_transactions_this_month"] > 0


def test_models_api_missing_key(client: TestClient):
    """Tests POST /api/models returns 400 when required API key is absent."""
    res = client.post("/api/models", json={"provider": "openai", "api_key": ""})
    assert res.status_code == 400
    assert "API Key is missing" in res.json()["detail"]


def test_static_ui_serving(client: TestClient):
    """Tests that static UI index.html, styles.css, and app.js are served properly."""
    res_index = client.get("/")
    assert res_index.status_code == 200
    assert "<!DOCTYPE html>" in res_index.text

    res_css = client.get("/styles.css")
    assert res_css.status_code == 200

    res_js = client.get("/app.js")
    assert res_js.status_code == 200

    res_fav = client.get("/favicon.svg")
    assert res_fav.status_code == 200
