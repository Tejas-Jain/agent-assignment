import copy
import json
import shutil
from pathlib import Path

DEFAULT_BUYER_ID = "BUYER-01"
_DEFAULT_SKU = "PROD-001"

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SEED_BUYERS_PATH = _DATA_DIR / "seed" / "buyers.json"
LIVE_BUYERS_PATH = _DATA_DIR / "buyers.json"

_buyers: list[dict] = []


def _read_live_file() -> list[dict]:
    return json.loads(LIVE_BUYERS_PATH.read_text(encoding="utf-8"))["buyers"]


def _write_live_file(buyers: list[dict]) -> None:
    LIVE_BUYERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    LIVE_BUYERS_PATH.write_text(json.dumps({"buyers": buyers}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def ensure_live_from_seed() -> None:
    if not LIVE_BUYERS_PATH.is_file():
        LIVE_BUYERS_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(SEED_BUYERS_PATH, LIVE_BUYERS_PATH)


def reload() -> None:
    global _buyers
    ensure_live_from_seed()
    _buyers = _read_live_file()


def reset_from_seed() -> None:
    shutil.copy(SEED_BUYERS_PATH, LIVE_BUYERS_PATH)
    reload()


def persist() -> None:
    _write_live_file(_buyers)


def get_all_buyers() -> list[dict]:
    if not _buyers:
        reload()
    return _buyers


def get_buyer(buyer_id: str = DEFAULT_BUYER_ID) -> dict | None:
    return next((b for b in get_all_buyers() if b["buyer_id"] == buyer_id), None)


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


def list_suppliers(product: dict) -> list[dict]:
    if product.get("suppliers"):
        return copy.deepcopy(product["suppliers"])
    terms = product.get("supplier_terms")
    if terms is None:
        return []
    if isinstance(terms, list):
        return copy.deepcopy(terms)
    return [copy.deepcopy(terms)]


def get_supplier_terms(product: dict, supplier_id: str | None = None) -> dict | None:
    suppliers = list_suppliers(product)
    if not suppliers:
        return None
    if supplier_id:
        return next((s for s in suppliers if s.get("supplier_id") == supplier_id), None)
    return suppliers[0]


def list_open_pos(buyer_id: str = DEFAULT_BUYER_ID, sku: str | None = None) -> list[dict]:
    buyer = get_buyer(buyer_id)
    if not buyer:
        return []
    orders: list[dict] = []
    for product in buyer.get("products") or []:
        for po in product.get("open_purchase_orders") or []:
            orders.append(copy.deepcopy(po))
    if sku:
        orders = [o for o in orders if o.get("sku") == sku]
    return orders


def get_po(po_id: str, buyer_id: str = DEFAULT_BUYER_ID) -> dict | None:
    return next((p for p in list_open_pos(buyer_id) if p["po_id"] == po_id), None)


def _find_po_product(buyer_id: str, po_id: str) -> tuple[dict, dict] | None:
    buyer = get_buyer(buyer_id)
    if not buyer:
        return None
    for product in buyer.get("products") or []:
        for po in product.get("open_purchase_orders") or []:
            if po["po_id"] == po_id:
                return product, po
    return None


def add_po(buyer_id: str, sku: str, po: dict) -> None:
    product = get_product(buyer_id, sku)
    if not product:
        raise ValueError(f"Unknown SKU {sku}")
    product.setdefault("open_purchase_orders", []).append(copy.deepcopy(po))
    persist()


def update_po_qty(buyer_id: str, po_id: str, quantity: int) -> bool:
    found = _find_po_product(buyer_id, po_id)
    if not found:
        return False
    _, po = found
    po["quantity"] = quantity
    persist()
    return True


reload()
