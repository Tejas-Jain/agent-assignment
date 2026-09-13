import json

from app.tools import actions, registry, store


def test_validate_fails_when_below_moq():
    store.reset_from_seed()
    actions.create_purchase_order(sku="PROD-001", quantity=1000)
    pos = registry.execute_tool("get_open_purchase_orders", {})
    po_id = json.loads(pos)["purchase_orders"][-1]["po_id"]
    actions.modify_purchase_order(po_id=po_id, quantity=100)
    result = json.loads(registry.execute_tool("validate_purchase_order", {"po_id": po_id}))
    assert result["valid"] is False
    assert any("MOQ" in issue for issue in result["issues"])


def test_validate_fails_when_exceeds_storage():
    store.reset_from_seed()
    create = actions.create_purchase_order(sku="PROD-001", quantity=1000)
    assert create["status"] == "created"
    po_id = create["purchase_order"]["po_id"]
    result = json.loads(registry.execute_tool("validate_purchase_order", {"po_id": po_id}))
    assert result["valid"] is False
    assert any("storage" in issue.lower() for issue in result["issues"])


def test_read_inventory_and_demand_for_sku():
    store.reset_from_seed()
    inv = json.loads(registry.execute_tool("get_inventory", {"sku": "PROD-001"}))
    demand = json.loads(registry.execute_tool("get_demand_forecast", {"sku": "PROD-001"}))
    assert inv["on_hand_units"] == 100
    assert demand["expected_units"] == 1000


def test_create_po_persists_to_live_file():
    store.reset_from_seed()
    actions.create_purchase_order(sku="PROD-001", quantity=500)
    on_disk = json.loads(store.LIVE_BUYERS_PATH.read_text(encoding="utf-8"))
    pos = on_disk["buyers"][0]["products"][0]["open_purchase_orders"]
    assert any(p["quantity"] == 500 for p in pos)
