from app.tools import store


def _sku_or_error(buyer_id: str, sku: str | None) -> tuple[str | None, dict | None]:
    resolved = store.resolve_sku(buyer_id, sku)
    if not resolved:
        return None, {"error": f"Unknown SKU {sku}" if sku else "SKU required"}
    return resolved, None


def get_inventory(sku: str | None = None, buyer_id: str = store.DEFAULT_BUYER_ID, **_kwargs) -> dict:
    resolved, err = _sku_or_error(buyer_id, sku)
    if err:
        return err
    product = store.get_product(buyer_id, resolved)
    if not product:
        return {"error": f"No inventory for SKU {resolved}"}
    return product["inventory"]


def get_demand_forecast(sku: str | None = None, buyer_id: str = store.DEFAULT_BUYER_ID, **_kwargs) -> dict:
    resolved, err = _sku_or_error(buyer_id, sku)
    if err:
        return err
    product = store.get_product(buyer_id, resolved)
    if not product:
        return {"error": f"No forecast for SKU {resolved}"}
    return product["expected_demand"]


def get_open_purchase_orders(sku: str | None = None, buyer_id: str = store.DEFAULT_BUYER_ID, **_kwargs) -> dict:
    return {"purchase_orders": store.list_open_pos(buyer_id, sku)}


def get_supplier_terms(sku: str | None = None, buyer_id: str = store.DEFAULT_BUYER_ID, **_kwargs) -> dict:
    resolved, err = _sku_or_error(buyer_id, sku)
    if err:
        return err
    product = store.get_product(buyer_id, resolved)
    if not product:
        return {"error": f"No supplier terms for SKU {resolved}"}
    return product["supplier_terms"]


def get_purchasing_budget(buyer_id: str = store.DEFAULT_BUYER_ID, **_kwargs) -> dict:
    buyer = store.get_buyer(buyer_id)
    if not buyer:
        return {"error": f"Unknown buyer {buyer_id}"}
    return buyer["purchasing_budget"]


def get_storage_capacity(buyer_id: str = store.DEFAULT_BUYER_ID, **_kwargs) -> dict:
    buyer = store.get_buyer(buyer_id)
    if not buyer:
        return {"error": f"Unknown buyer {buyer_id}"}
    return buyer["storage_capacity"]
