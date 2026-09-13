import uuid

from app.tools import read, store


def _total_cost(sku: str, quantity: int, buyer_id: str = store.DEFAULT_BUYER_ID) -> float:
    terms = read.get_supplier_terms(sku=sku, buyer_id=buyer_id)
    if "error" in terms:
        return 0.0
    return quantity * terms["unit_cost"]


def create_purchase_order(
    sku: str, quantity: int, supplier_id: str | None = None, buyer_id: str = store.DEFAULT_BUYER_ID, **_kwargs
) -> dict:
    product = store.get_product(buyer_id, sku)
    if not product:
        return {"error": f"Unknown SKU {sku}"}
    terms = product["supplier_terms"]
    if supplier_id and supplier_id != terms["supplier_id"]:
        return {"error": f"Supplier {supplier_id} not linked to {sku}"}
    po_id = f"PO-{uuid.uuid4().hex[:6].upper()}"
    po = {"po_id": po_id, "sku": sku, "quantity": quantity, "status": "open", "supplier_id": terms["supplier_id"]}
    store.add_po(buyer_id, sku, po)
    return {"status": "created", "purchase_order": po}


def modify_purchase_order(po_id: str, quantity: int, buyer_id: str = store.DEFAULT_BUYER_ID, **_kwargs) -> dict:
    if not store.update_po_qty(buyer_id, po_id, quantity):
        return {"error": f"PO {po_id} not found"}
    po = store.get_po(po_id, buyer_id)
    return {"status": "modified", "purchase_order": po}


def validate_purchase_order(po_id: str, buyer_id: str = store.DEFAULT_BUYER_ID, **_kwargs) -> dict:
    po = store.get_po(po_id, buyer_id)
    if not po:
        return {"valid": False, "issues": [f"PO {po_id} not found"]}
    sku = po["sku"]
    product = store.get_product(buyer_id, sku)
    if not product:
        return {"valid": False, "issues": [f"Unknown SKU {sku} for PO"]}
    terms = product["supplier_terms"]
    buyer = store.get_buyer(buyer_id)
    assert buyer is not None
    issues: list[str] = []
    qty = po["quantity"]
    if qty < terms["minimum_order_quantity"]:
        issues.append(f"Quantity {qty} below MOQ {terms['minimum_order_quantity']}")
    cost = _total_cost(sku, qty, buyer_id)
    budget = buyer["purchasing_budget"]["remaining_amount"]
    if cost > budget:
        issues.append(f"Cost {cost} exceeds remaining budget {budget}")
    inv = product["inventory"]
    storage = buyer["storage_capacity"]
    projected = inv["on_hand_units"] + inv["inbound_units"] + qty
    if projected > storage["max_units"]:
        issues.append(f"Projected stock {projected} exceeds warehouse max {storage['max_units']}")
    if qty > storage["available_units"]:
        issues.append(f"Order {qty} exceeds available storage slots {storage['available_units']}")
    return {"valid": len(issues) == 0, "issues": issues, "po_id": po_id, "estimated_cost": cost}
