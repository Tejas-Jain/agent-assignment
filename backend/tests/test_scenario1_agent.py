import json

from app.tools import actions, registry, store


def test_validate_fails_when_below_moq():
    store.reset_from_seed()
    actions.create_purchase_order(sku="PROD-001", quantity=1000, human_confirmed=True)
    pos = registry.execute_tool("get_open_purchase_orders", {})
    po_id = json.loads(pos)["purchase_orders"][-1]["po_id"]
    actions.modify_purchase_order(po_id=po_id, quantity=100, human_confirmed=True)
    result = json.loads(registry.execute_tool("validate_purchase_order", {"po_id": po_id}))
    assert result["valid"] is False
    assert any("MOQ" in issue for issue in result["issues"])


def test_validate_fails_when_exceeds_storage():
    store.reset_from_seed()
    create = actions.create_purchase_order(sku="PROD-001", quantity=1000, human_confirmed=True)
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


def test_list_suppliers_for_sku():
    store.reset_from_seed()
    result = json.loads(registry.execute_tool("get_supplier_terms", {"sku": "PROD-001"}))
    assert result["sku"] == "PROD-001"
    assert len(result["suppliers"]) == 2
    assert {s["supplier_id"] for s in result["suppliers"]} == {"SUP-ACME", "SUP-BETA"}


def test_plan_caps_oversized_recommendation_to_storage():
    store.reset_from_seed()
    plan = json.loads(registry.execute_tool("plan_purchase_quantity", {"sku": "PROD-001", "proposed_quantity": 1000}))
    assert plan["net_requirement_units"] == 800
    assert plan["decision"] == "modify"
    assert plan["suggested_quantity"] == 600


def test_plan_rounds_up_to_moq_when_net_need_below_moq():
    store.reset_from_seed()
    buyer = store.get_buyer("BUYER-01")
    assert buyer is not None
    product = buyer["products"][0]
    product["expected_demand"]["expected_units"] = 250
    store.persist()
    store.reload()
    plan = json.loads(registry.execute_tool("plan_purchase_quantity", {"sku": "PROD-001", "proposed_quantity": 500}))
    assert plan["net_requirement_units"] == 50
    assert plan["decision"] == "accept"
    assert plan["suggested_quantity"] == 500


def test_plan_rejects_when_no_net_requirement():
    store.reset_from_seed()
    buyer = store.get_buyer("BUYER-01")
    assert buyer is not None
    product = buyer["products"][0]
    product["expected_demand"]["expected_units"] = 200
    store.persist()
    store.reload()
    plan = json.loads(registry.execute_tool("plan_purchase_quantity", {"sku": "PROD-001", "proposed_quantity": 500}))
    assert plan["decision"] == "reject"
    assert plan["suggested_quantity"] == 0


def test_create_po_blocked_without_human_confirmation():
    store.reset_from_seed()
    result = actions.create_purchase_order(sku="PROD-001", quantity=500, human_confirmed=False)
    assert result["error"] == "human_confirmation_required"
    via_tool = json.loads(
        registry.execute_tool(
            "create_purchase_order", {"sku": "PROD-001", "quantity": 500, "human_confirmed": False}
        )
    )
    assert via_tool["error"] == "human_confirmation_required"


def test_create_po_persists_to_live_file():
    store.reset_from_seed()
    actions.create_purchase_order(sku="PROD-001", quantity=500, human_confirmed=True)
    on_disk = json.loads(store.LIVE_BUYERS_PATH.read_text(encoding="utf-8"))
    pos = on_disk["buyers"][0]["products"][0]["open_purchase_orders"]
    assert any(p["quantity"] == 500 for p in pos)
