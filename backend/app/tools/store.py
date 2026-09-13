import copy
import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_BUYER_ID = "BUYER-01"
_DEFAULT_SKU = "PROD-001"

_BUYERS_PATH = Path(__file__).resolve().parent.parent / "data" / "buyers.json"
_BUYERS: list[dict] = json.loads(_BUYERS_PATH.read_text(encoding="utf-8"))["buyers"]


@dataclass
class SessionOverlay:
    po_qty: dict[str, int] = field(default_factory=dict)
    added_pos: list[dict] = field(default_factory=list)


_overlays: dict[str, SessionOverlay] = {}


def reset_overlay(session_id: str) -> None:
    _overlays.pop(session_id, None)


def _overlay(session_id: str) -> SessionOverlay:
    if session_id not in _overlays:
        _overlays[session_id] = SessionOverlay()
    return _overlays[session_id]


def get_buyer(buyer_id: str = DEFAULT_BUYER_ID) -> dict | None:
    return next((b for b in _BUYERS if b["buyer_id"] == buyer_id), None)


def resolve_sku(buyer_id: str, sku: str | None) -> str | None:
    buyer = get_buyer(buyer_id)
    if not buyer:
        return None
    products = buyer.get("products") or []
    if sku:
        return sku if any(p["sku"] == sku for p in products) else None
    if len(products) == 1:
        return products[0]["sku"]
    return _DEFAULT_SKU if any(p["sku"] == _DEFAULT_SKU for p in products) else None


def get_product(buyer_id: str, sku: str | None = None) -> dict | None:
    resolved = resolve_sku(buyer_id, sku)
    if not resolved:
        return None
    buyer = get_buyer(buyer_id)
    assert buyer is not None
    return next((p for p in buyer["products"] if p["sku"] == resolved), None)


def _seed_pos_for_buyer(buyer_id: str) -> list[dict]:
    buyer = get_buyer(buyer_id)
    if not buyer:
        return []
    pos: list[dict] = []
    for product in buyer.get("products") or []:
        for po in product.get("open_purchase_orders") or []:
            pos.append(copy.deepcopy(po))
    return pos


def list_open_pos(session_id: str, buyer_id: str = DEFAULT_BUYER_ID, sku: str | None = None) -> list[dict]:
    overlay = _overlay(session_id)
    merged: dict[str, dict] = {}
    for po in _seed_pos_for_buyer(buyer_id):
        merged[po["po_id"]] = copy.deepcopy(po)
    for po in overlay.added_pos:
        merged[po["po_id"]] = copy.deepcopy(po)
    for po_id, qty in overlay.po_qty.items():
        if po_id in merged:
            merged[po_id]["quantity"] = qty
    orders = list(merged.values())
    if sku:
        orders = [o for o in orders if o.get("sku") == sku]
    return orders


def get_po(session_id: str, po_id: str, buyer_id: str = DEFAULT_BUYER_ID) -> dict | None:
    return next((p for p in list_open_pos(session_id, buyer_id) if p["po_id"] == po_id), None)


def add_po(session_id: str, po: dict) -> None:
    _overlay(session_id).added_pos.append(copy.deepcopy(po))


def update_po_qty(session_id: str, po_id: str, quantity: int) -> bool:
    if get_po(session_id, po_id) is None:
        return False
    _overlay(session_id).po_qty[po_id] = quantity
    return True
