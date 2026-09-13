import json
from typing import Any, Callable

from app.agent.llm.base import ToolDefinition
from app.tools import actions, read

ToolHandler = Callable[..., dict]

TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="get_inventory",
        description="Get on-hand and inbound inventory for a SKU.",
        parameters={
            "type": "object",
            "properties": {"sku": {"type": "string", "description": "Product SKU"}},
            "required": [],
        },
    ),
    ToolDefinition(
        name="get_demand_forecast",
        description="Get demand forecast for a SKU over the planning horizon.",
        parameters={"type": "object", "properties": {"sku": {"type": "string"}}, "required": []},
    ),
    ToolDefinition(
        name="get_open_purchase_orders",
        description="List open purchase orders, optionally filtered by SKU.",
        parameters={"type": "object", "properties": {"sku": {"type": "string"}}, "required": []},
    ),
    ToolDefinition(
        name="get_supplier_terms",
        description="Supplier lead time, MOQ, and unit cost for a SKU. Omit supplier_id to list all suppliers for the SKU.",
        parameters={
            "type": "object",
            "properties": {
                "sku": {"type": "string"},
                "supplier_id": {"type": "string", "description": "Optional; returns terms for one supplier."},
            },
            "required": [],
        },
    ),
    ToolDefinition(
        name="get_purchasing_budget",
        description="Remaining purchasing budget for the buyer.",
        parameters={"type": "object", "properties": {}, "required": []},
    ),
    ToolDefinition(
        name="get_storage_capacity",
        description="Warehouse storage capacity and available space in units.",
        parameters={"type": "object", "properties": {}, "required": []},
    ),
    ToolDefinition(
        name="plan_purchase_quantity",
        description=(
            "Compute net demand gap and a feasible order quantity (MOQ, budget, storage). "
            "Call when reviewing a purchase recommendation; prefer modify over reject when suggested_quantity > 0."
        ),
        parameters={
            "type": "object",
            "properties": {
                "sku": {"type": "string"},
                "proposed_quantity": {
                    "type": "integer",
                    "description": "Quantity from the system recommendation or scenario brief, if given.",
                },
                "supplier_id": {
                    "type": "string",
                    "description": "Optional; plan using one supplier. If omitted, evaluates all suppliers and picks the best viable option.",
                },
            },
            "required": ["sku"],
        },
    ),
    ToolDefinition(
        name="create_purchase_order",
        description=(
            "Create a purchase order for a SKU and quantity. HIGH-STAKES: do not call until the human "
            "reviewer explicitly confirms in chat; then set human_confirmed=true."
        ),
        parameters={
            "type": "object",
            "properties": {
                "sku": {"type": "string"},
                "quantity": {"type": "integer"},
                "supplier_id": {"type": "string", "description": "Supplier to use; default is the first configured supplier for the SKU."},
                "human_confirmed": {
                    "type": "boolean",
                    "description": "Must be true only after explicit user approval in chat; otherwise the tool rejects.",
                },
            },
            "required": ["sku", "quantity", "human_confirmed"],
        },
    ),
    ToolDefinition(
        name="modify_purchase_order",
        description=(
            "Change quantity on an existing open PO. HIGH-STAKES: do not call until the human reviewer "
            "explicitly confirms in chat; then set human_confirmed=true."
        ),
        parameters={
            "type": "object",
            "properties": {
                "po_id": {"type": "string"},
                "quantity": {"type": "integer"},
                "human_confirmed": {
                    "type": "boolean",
                    "description": "Must be true only after explicit user approval in chat; otherwise the tool rejects.",
                },
            },
            "required": ["po_id", "quantity", "human_confirmed"],
        },
    ),
    ToolDefinition(
        name="validate_purchase_order",
        description=(
            "Validate a PO against MOQ, budget, and storage. Call after create/modify. "
            "If invalid, use suggested_quantity in the response and adjust the PO—do not reject the purchase outright."
        ),
        parameters={"type": "object", "properties": {"po_id": {"type": "string"}}, "required": ["po_id"]},
    ),
]

HANDLERS: dict[str, ToolHandler] = {
    "get_inventory": read.get_inventory,
    "get_demand_forecast": read.get_demand_forecast,
    "get_open_purchase_orders": read.get_open_purchase_orders,
    "get_supplier_terms": read.get_supplier_terms,
    "get_purchasing_budget": read.get_purchasing_budget,
    "get_storage_capacity": read.get_storage_capacity,
    "plan_purchase_quantity": actions.plan_purchase_quantity,
    "create_purchase_order": actions.create_purchase_order,
    "modify_purchase_order": actions.modify_purchase_order,
    "validate_purchase_order": actions.validate_purchase_order,
}


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    handler = HANDLERS.get(name)
    if not handler:
        return json.dumps({"error": f"Unknown tool: {name}"})
    result = handler(**arguments)
    return json.dumps(result)
