from app.tools import actions, registry, session


def test_validate_fails_when_below_moq():
    session.reset_session("test-moq")
    actions.create_purchase_order("test-moq", sku="PROD-001", quantity=800)
    pos = registry.execute_tool("test-moq", "get_open_purchase_orders", {})
    import json

    po_id = json.loads(pos)["purchase_orders"][-1]["po_id"]
    actions.modify_purchase_order("test-moq", po_id=po_id, quantity=100)
    result = json.loads(registry.execute_tool("test-moq", "validate_purchase_order", {"po_id": po_id}))
    assert result["valid"] is False
    assert any("MOQ" in issue for issue in result["issues"])


def test_validate_fails_when_exceeds_storage():
    session.reset_session("test-storage")
    create = actions.create_purchase_order("test-storage", sku="PROD-001", quantity=800)
    assert create["status"] == "created"
    po_id = create["purchase_order"]["po_id"]
    result = __import__("json").loads(registry.execute_tool("test-storage", "validate_purchase_order", {"po_id": po_id}))
    assert result["valid"] is False
    assert any("storage" in issue.lower() for issue in result["issues"])


def test_read_tools_return_scenario1_recommendation():
    session.reset_session("test-read")
    rec = __import__("json").loads(registry.execute_tool("test-read", "get_purchase_recommendation", {}))
    assert rec["recommended_quantity"] == 800
