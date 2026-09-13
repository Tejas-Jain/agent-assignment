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
        description="Supplier lead time, MOQ, and unit cost for a SKU.",
        parameters={"type": "object", "properties": {"sku": {"type": "string"}}, "required": []},
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
        name="create_purchase_order",
        description="Create a purchase order for a SKU and quantity.",
        parameters={
            "type": "object",
            "properties": {
                "sku": {"type": "string"},
                "quantity": {"type": "integer"},
                "supplier_id": {"type": "string"},
            },
            "required": ["sku", "quantity"],
        },
    ),
    ToolDefinition(
        name="modify_purchase_order",
        description="Change quantity on an existing open PO.",
        parameters={
            "type": "object",
            "properties": {"po_id": {"type": "string"}, "quantity": {"type": "integer"}},
            "required": ["po_id", "quantity"],
        },
    ),
    ToolDefinition(
        name="validate_purchase_order",
        description="Validate a PO against MOQ, budget, and storage constraints. Call after create/modify.",
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
