from types import MappingProxyType

from app.tools.calculator import calculator
from app.tools.python_tool import run_python


# ============================================================
# TOOL REGISTRY
# ============================================================

_TOOL_REGISTRY = {
    "calculator": {
        "function": calculator,
        "description": "Performs safe mathematical calculations.",
        "enabled": True,
        "input_type": "expression",
        "risk_level": "low",
    },

    "python": {
        "function": run_python,
        "description": "Executes restricted and validated Python calculations.",
        "enabled": True,
        "input_type": "code",
        "risk_level": "medium",
    },
}


TOOL_REGISTRY = MappingProxyType(_TOOL_REGISTRY)


# ============================================================
# SECURITY RULES
# ============================================================

ALLOWED_TOOL_NAMES = frozenset({
    "calculator",
    "python",
})

ALLOWED_INPUT_TYPES = frozenset({
    "expression",
    "code",
})

ALLOWED_RISK_LEVELS = frozenset({
    "low",
    "medium",
    "high",
})


# ============================================================
# TOOL NAME VALIDATION
# ============================================================

def is_valid_tool_name(tool_name: str) -> bool:

    if not isinstance(tool_name, str):
        return False

    tool_name = tool_name.strip()

    if not tool_name:
        return False

    return tool_name in ALLOWED_TOOL_NAMES


# ============================================================
# TOOL DEFINITION VALIDATION
# ============================================================

def validate_tool_definition(
    tool_name: str,
    tool: dict,
) -> bool:

    if not isinstance(tool, dict):
        return False

    required_fields = {
        "function",
        "description",
        "enabled",
        "input_type",
        "risk_level",
    }

    if not required_fields.issubset(tool.keys()):
        return False

    if not callable(tool.get("function")):
        return False

    if not isinstance(
        tool.get("description"),
        str,
    ):
        return False

    if not isinstance(
        tool.get("enabled"),
        bool,
    ):
        return False

    if tool.get("input_type") not in ALLOWED_INPUT_TYPES:
        return False

    if tool.get("risk_level") not in ALLOWED_RISK_LEVELS:
        return False

    return True


# ============================================================
# REGISTRY VALIDATION
# ============================================================

def validate_registry() -> tuple[bool, list[str]]:

    errors = []

    for tool_name, tool in TOOL_REGISTRY.items():

        if not is_valid_tool_name(tool_name):
            errors.append(
                f"Invalid tool name: {tool_name}"
            )
            continue

        if not validate_tool_definition(
            tool_name,
            tool,
        ):
            errors.append(
                f"Invalid tool definition: {tool_name}"
            )

    for expected_tool in ALLOWED_TOOL_NAMES:

        if expected_tool not in TOOL_REGISTRY:
            errors.append(
                f"Missing required tool: {expected_tool}"
            )

    return (
        len(errors) == 0,
        errors,
    )


# ============================================================
# GET TOOL
# ============================================================

def get_tool(tool_name: str):

    if not is_valid_tool_name(tool_name):
        return None

    tool = TOOL_REGISTRY.get(tool_name)

    if tool is None:
        return None

    if not validate_tool_definition(
        tool_name,
        tool,
    ):
        return None

    if not tool.get("enabled", False):
        return None

    return tool


# ============================================================
# AUTHORIZATION
# ============================================================

def is_tool_authorized(tool_name: str) -> bool:

    tool = get_tool(tool_name)

    if tool is None:
        return False

    return (
        tool.get("enabled", False)
        and callable(tool.get("function"))
    )


# ============================================================
# REGISTERED CHECK
# ============================================================

def is_tool_registered(tool_name: str) -> bool:

    if not is_valid_tool_name(tool_name):
        return False

    if tool_name not in TOOL_REGISTRY:
        return False

    return validate_tool_definition(
        tool_name,
        TOOL_REGISTRY[tool_name],
    )


# ============================================================
# AVAILABLE TOOLS
# ============================================================

def list_available_tools() -> list[str]:

    available = []

    for tool_name in TOOL_REGISTRY:

        if is_tool_authorized(tool_name):
            available.append(tool_name)

    return available


# ============================================================
# TOOL DESCRIPTION
# ============================================================

def get_tool_description(tool_name: str) -> str:

    tool = get_tool(tool_name)

    if tool is None:
        return "Tool not available."

    return tool.get(
        "description",
        "No description available.",
    )


# ============================================================
# INPUT TYPE
# ============================================================

def get_tool_input_type(tool_name: str) -> str:

    tool = get_tool(tool_name)

    if tool is None:
        return "unknown"

    return tool.get(
        "input_type",
        "unknown",
    )


# ============================================================
# RISK LEVEL
# ============================================================

def get_tool_risk_level(tool_name: str) -> str:

    tool = get_tool(tool_name)

    if tool is None:
        return "unknown"

    return tool.get(
        "risk_level",
        "unknown",
    )


# ============================================================
# SECURE TOOL EXECUTION
# ============================================================

def execute_tool(
    tool_name: str,
    tool_input: str,
) -> str:

    if not is_tool_authorized(tool_name):
        return (
            f"Tool '{tool_name}' "
            "is not authorized."
        )

    tool = get_tool(tool_name)

    if tool is None:
        return (
            f"Tool '{tool_name}' "
            "is unavailable."
        )

    function = tool.get("function")

    try:
        result = function(tool_input)
        return str(result)

    except Exception as error:
        return (
            f"Tool execution error: "
            f"{str(error)}"
        )


# ============================================================
# STARTUP VALIDATION
# ============================================================

REGISTRY_VALID, REGISTRY_ERRORS = validate_registry()