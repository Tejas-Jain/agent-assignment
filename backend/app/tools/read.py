import json

from app.tools.session import get_session


def get_purchase_recommendation(session_id: str, **_kwargs) -> dict:
    s = get_session(session_id)
    return {"sku": s["sku"], **s["recommendation"]}


def get_inventory(session_id: str, sku: str | None = None, **_kwargs) -> dict:
    s = get_session(session_id)
    inv = s["inventory"]
    if sku and sku != inv["sku"]:
        return {"error": f"No inventory for SKU {sku}"}
    return inv


def get_demand_forecast(session_id: str, sku: str | None = None, **_kwargs) -> dict:
    s = get_session(session_id)
    fc = s["demand_forecast"]
    if sku and sku != fc["sku"]:
        return {"error": f"No forecast for SKU {sku}"}
    return fc


def get_open_purchase_orders(session_id: str, sku: str | None = None, **_kwargs) -> dict:
    s = get_session(session_id)
    orders = s["open_purchase_orders"]
    if sku:
        orders = [o for o in orders if o["sku"] == sku]
    return {"purchase_orders": orders}


def get_supplier_terms(session_id: str, sku: str | None = None, **_kwargs) -> dict:
    s = get_session(session_id)
    terms = s["supplier_terms"]
    if sku and sku != terms["sku"]:
        return {"error": f"No supplier terms for SKU {sku}"}
    return terms


def get_purchasing_budget(session_id: str, **_kwargs) -> dict:
    return get_session(session_id)["purchasing_budget"]


def get_storage_capacity(session_id: str, **_kwargs) -> dict:
    return get_session(session_id)["storage_capacity"]
