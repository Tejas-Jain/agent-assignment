import json

from app.tools import actions, registry, store


def test_validate_fails_when_below_moq():
    store.reset_overlay("test-moq")
    actions.create_purchase_order("test-moq", sku="PROD-001", quantity=1000)
    pos = registry.execute_tool("test-moq", "get_open_purchase_orders", {})
    po_id = json.loads(pos)["purchase_orders"][-1]["po_id"]
    actions.modify_purchase_order("test-moq", po_id=po_id, quantity=100)
    result = json.loads(registry.execute_tool("test-moq", "validate_purchase_order", {"po_id": po_id}))
    assert result["valid"] is False
    assert any("MOQ" in issue for issue in result["issues"])


def test_validate_fails_when_exceeds_storage():
    store.reset_overlay("test-storage")
    create = actions.create_purchase_order("test-storage", sku="PROD-001", quantity=1000)
    assert create["status"] == "created"
    po_id = create["purchase_order"]["po_id"]
    result = json.loads(registry.execute_tool("test-storage", "validate_purchase_order", {"po_id": po_id}))
    assert result["valid"] is False
    assert any("storage" in issue.lower() for issue in result["issues"])


def test_read_inventory_and_demand_for_sku():
    store.reset_overlay("test-read")
    inv = json.loads(registry.execute_tool("test-read", "get_inventory", {"sku": "PROD-001"}))
    demand = json.loads(registry.execute_tool("test-read", "get_demand_forecast", {"sku": "PROD-001"}))
    assert inv["on_hand_units"] == 100
    assert demand["expected_units"] == 1000
