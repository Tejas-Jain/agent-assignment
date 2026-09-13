import uuid

from app.tools import read
from app.tools.session import get_session


def _total_cost(session_id: str, quantity: int) -> float:
    terms = read.get_supplier_terms(session_id)
    return quantity * terms["unit_cost"]


def create_purchase_order(session_id: str, sku: str, quantity: int, supplier_id: str | None = None, **_kwargs) -> dict:
    s = get_session(session_id)
    terms = s["supplier_terms"]
    if sku != s["sku"]:
        return {"error": f"Unknown SKU {sku}"}
    if supplier_id and supplier_id != terms["supplier_id"]:
        return {"error": f"Supplier {supplier_id} not linked to {sku}"}
    rec_qty = s["recommendation"]["recommended_quantity"]
    ratio = abs(quantity - rec_qty) / rec_qty if rec_qty else 0
    if ratio > s.get("human_approval_qty_delta_ratio", 0.2):
        return {
            "status": "pending_human_approval",
            "message": f"Quantity {quantity} differs from recommendation {rec_qty} by more than 20%. Awaiting buyer approval.",
            "requested_quantity": quantity,
        }
    po_id = f"PO-{uuid.uuid4().hex[:6].upper()}"
    po = {"po_id": po_id, "sku": sku, "quantity": quantity, "status": "open", "supplier_id": terms["supplier_id"]}
    s["open_purchase_orders"].append(po)
    s["recommendation"]["status"] = "accepted_via_po"
    return {"status": "created", "purchase_order": po}


def modify_purchase_order(session_id: str, po_id: str, quantity: int, **_kwargs) -> dict:
    s = get_session(session_id)
    for po in s["open_purchase_orders"]:
        if po["po_id"] == po_id:
            po["quantity"] = quantity
            return {"status": "modified", "purchase_order": po}
    return {"error": f"PO {po_id} not found"}


def reject_purchase_recommendation(session_id: str, reason: str, **_kwargs) -> dict:
    s = get_session(session_id)
    s["recommendation"]["status"] = "rejected"
    s["recommendation"]["rejection_reason"] = reason
    return {"status": "rejected", "reason": reason}


def validate_purchase_order(session_id: str, po_id: str, **_kwargs) -> dict:
    s = get_session(session_id)
    po = next((p for p in s["open_purchase_orders"] if p["po_id"] == po_id), None)
    if not po:
        return {"valid": False, "issues": [f"PO {po_id} not found"]}
    issues: list[str] = []
    terms = s["supplier_terms"]
    qty = po["quantity"]
    if qty < terms["minimum_order_quantity"]:
        issues.append(f"Quantity {qty} below MOQ {terms['minimum_order_quantity']}")
    cost = _total_cost(session_id, qty)
    budget = s["purchasing_budget"]["remaining_amount"]
    if cost > budget:
        issues.append(f"Cost {cost} exceeds remaining budget {budget}")
    inv = s["inventory"]
    storage = s["storage_capacity"]
    projected = inv["on_hand_units"] + inv["inbound_units"] + qty
    if projected > storage["max_units"]:
        issues.append(f"Projected stock {projected} exceeds warehouse max {storage['max_units']}")
    if qty > storage["available_units"]:
        issues.append(f"Order {qty} exceeds available storage slots {storage['available_units']}")
    return {"valid": len(issues) == 0, "issues": issues, "po_id": po_id, "estimated_cost": cost}
