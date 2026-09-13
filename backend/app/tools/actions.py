import uuid

from app.tools import store


def _require_human_confirmation(human_confirmed: bool, operation: str) -> dict | None:
    if human_confirmed is not True:
        return {
            "error": "human_confirmation_required",
            "message": (
                f"Cannot {operation} without explicit human confirmation in chat. "
                "Ask the reviewer to approve the exact PO change, then retry with human_confirmed=true."
            ),
        }
    return None


def _total_cost(
    sku: str, quantity: int, buyer_id: str = store.DEFAULT_BUYER_ID, supplier_id: str | None = None
) -> float:
    product = store.get_product(buyer_id, sku)
    if not product:
        return 0.0
    terms = store.get_supplier_terms(product, supplier_id)
    if not terms:
        return 0.0
    return quantity * terms["unit_cost"]


def _net_requirement_units(buyer_id: str, sku: str) -> int | None:
    product = store.get_product(buyer_id, sku)
    if not product:
        return None
    inv = product["inventory"]
    demand = product["expected_demand"]["expected_units"]
    supply = inv["on_hand_units"] + inv["inbound_units"]
    return max(0, demand - supply)


def _order_quantity_bounds(buyer_id: str, sku: str, supplier_id: str | None = None) -> dict | None:
    product = store.get_product(buyer_id, sku)
    buyer = store.get_buyer(buyer_id)
    if not product or not buyer:
        return None
    terms = store.get_supplier_terms(product, supplier_id)
    if not terms:
        return None
    inv = product["inventory"]
    storage = buyer["storage_capacity"]
    budget = buyer["purchasing_budget"]["remaining_amount"]
    unit_cost = terms["unit_cost"]
    max_by_projected = storage["max_units"] - (inv["on_hand_units"] + inv["inbound_units"])
    max_by_slots = storage["available_units"]
    max_by_budget = int(budget // unit_cost) if unit_cost else 0
    max_order = max(0, min(max_by_projected, max_by_slots, max_by_budget))
    return {
        "supplier_id": terms["supplier_id"],
        "minimum_order_quantity": terms["minimum_order_quantity"],
        "max_order_quantity": max_order,
        "unit_cost": unit_cost,
        "lead_time_days": terms["lead_time_days"],
    }


def _plan_decision(net_requirement: int, proposed_quantity: int | None, moq: int, max_order: int) -> tuple[str, int, str | None]:
    if net_requirement <= 0:
        return "reject", 0, "No additional purchase needed; on-hand plus inbound already covers forecast demand."
    if max_order < moq:
        return "reject", 0, "Cannot place an MOQ-compliant order within budget and storage limits."
    target = proposed_quantity if proposed_quantity is not None else net_requirement
    if target > max_order:
        suggested = max_order
    elif target < moq:
        suggested = moq
    else:
        suggested = target
    if proposed_quantity is None:
        decision = "modify" if suggested != net_requirement else "accept"
    elif suggested == proposed_quantity:
        decision = "accept"
    else:
        decision = "modify"
    return decision, suggested, None


def plan_purchase_quantity(
    sku: str,
    proposed_quantity: int | None = None,
    supplier_id: str | None = None,
    buyer_id: str = store.DEFAULT_BUYER_ID,
    **_kwargs,
) -> dict:
    resolved = store.resolve_sku(buyer_id, sku)
    if not resolved:
        return {"error": f"Unknown SKU {sku}"}
    product = store.get_product(buyer_id, resolved)
    if not product:
        return {"error": f"No planning data for SKU {resolved}"}
    net_req = _net_requirement_units(buyer_id, resolved)
    if net_req is None:
        return {"error": f"No planning data for SKU {resolved}"}
    inv = product["inventory"]
    supplier_ids = [supplier_id] if supplier_id else [s["supplier_id"] for s in store.list_suppliers(product)]
    if not supplier_ids:
        return {"error": f"No suppliers configured for SKU {resolved}"}

    options: list[dict] = []
    for sid in supplier_ids:
        bounds = _order_quantity_bounds(buyer_id, resolved, sid)
        if not bounds:
            continue
        decision, suggested, reject_reason = _plan_decision(
            net_req, proposed_quantity, bounds["minimum_order_quantity"], bounds["max_order_quantity"]
        )
        options.append(
            {
                "supplier_id": sid,
                "decision": decision,
                "suggested_quantity": suggested,
                "reject_reason": reject_reason,
                "constraints": bounds,
                "estimated_cost": suggested * bounds["unit_cost"] if suggested else 0,
            }
        )
    if not options:
        return {"error": f"No supplier terms for SKU {resolved}"}

    viable = [o for o in options if o["decision"] != "reject"]
    chosen = min(viable, key=lambda o: (o["estimated_cost"], o["constraints"]["minimum_order_quantity"])) if viable else options[0]
    return {
        "sku": resolved,
        "proposed_quantity": proposed_quantity,
        "net_requirement_units": net_req,
        "supply_before_order": {"on_hand_units": inv["on_hand_units"], "inbound_units": inv["inbound_units"]},
        "recommended_supplier_id": chosen["supplier_id"],
        "decision": chosen["decision"],
        "suggested_quantity": chosen["suggested_quantity"],
        "reject_reason": chosen["reject_reason"],
        "constraints": chosen["constraints"],
        "supplier_options": options,
    }


def create_purchase_order(
    sku: str,
    quantity: int,
    supplier_id: str | None = None,
    human_confirmed: bool = False,
    buyer_id: str = store.DEFAULT_BUYER_ID,
    **_kwargs,
) -> dict:
    if block := _require_human_confirmation(human_confirmed, "create a purchase order"):
        return block
    product = store.get_product(buyer_id, sku)
    if not product:
        return {"error": f"Unknown SKU {sku}"}
    terms = store.get_supplier_terms(product, supplier_id)
    if not terms:
        return {"error": f"Supplier {supplier_id or '(default)'} not linked to {sku}"}
    po_id = f"PO-{uuid.uuid4().hex[:6].upper()}"
    po = {"po_id": po_id, "sku": sku, "quantity": quantity, "status": "open", "supplier_id": terms["supplier_id"]}
    store.add_po(buyer_id, sku, po)
    return {"status": "created", "purchase_order": po}


def modify_purchase_order(
    po_id: str, quantity: int, human_confirmed: bool = False, buyer_id: str = store.DEFAULT_BUYER_ID, **_kwargs
) -> dict:
    if block := _require_human_confirmation(human_confirmed, "modify a purchase order"):
        return block
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
    po_supplier_id = po.get("supplier_id")
    terms = store.get_supplier_terms(product, po_supplier_id)
    if not terms:
        return {"valid": False, "issues": [f"Supplier {po_supplier_id} not linked to {sku}"]}
    buyer = store.get_buyer(buyer_id)
    assert buyer is not None
    issues: list[str] = []
    qty = po["quantity"]
    if qty < terms["minimum_order_quantity"]:
        issues.append(f"Quantity {qty} below MOQ {terms['minimum_order_quantity']} for {terms['supplier_id']}")
    cost = _total_cost(sku, qty, buyer_id, terms["supplier_id"])
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
    net_req = _net_requirement_units(buyer_id, sku)
    bounds = _order_quantity_bounds(buyer_id, sku, terms["supplier_id"])
    suggested_quantity: int | None = None
    if net_req is not None and bounds is not None:
        _, suggested_quantity, _ = _plan_decision(
            net_req, qty, bounds["minimum_order_quantity"], bounds["max_order_quantity"]
        )
    payload: dict = {
        "valid": len(issues) == 0,
        "issues": issues,
        "po_id": po_id,
        "estimated_cost": cost,
        "net_requirement_units": net_req,
    }
    if not payload["valid"] and suggested_quantity and suggested_quantity != qty:
        payload["suggested_quantity"] = suggested_quantity
    return payload
