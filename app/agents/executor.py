import ast
import re
import time

from langchain_google_genai import ChatGoogleGenerativeAI

from .state import AgentState
from .error_handler import MAX_RETRIES
from app.tools.registry import (
    get_tool,
    is_tool_registered,
    list_available_tools,
)


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0
)


# =========================
# SAFETY CHECK
# =========================

def contains_unsafe_action(request: str) -> bool:

    unsafe_patterns = [
        r"\bread\s+(a\s+)?file\b",
        r"\bwrite\s+(to\s+)?(a\s+)?file\b",
        r"\bdelete\s+(a\s+)?file\b",
        r"\bmodify\s+(a\s+)?file\b",
        r"\baccess\s+(a\s+)?file\b",
        r"\bopen\s+(a\s+)?file\b",
        r"\bfilesystem\b",
        r"\bfile\s+system\b",
        r"\bterminal\b",
        r"\bshell\s+command\b",
        r"\bcommand\s+line\b",
        r"\brun\s+(a\s+)?command\b",
        r"\bexecute\s+(a\s+)?command\b",
        r"\bcommand\s+execution\b",
        r"\bos\s+command\b",
        r"\bnetwork\s+request\b",
        r"\baccess\s+the\s+internet\b",
        r"\bdownload\s+(a\s+)?file\b",
        r"\bupload\s+(a\s+)?file\b",
        r"\bsend\s+(an?\s+)?http\b",
        r"\bmake\s+(an?\s+)?http\b",
        r"\bsystem\s+access\b",
        r"\benvironment\s+variables?\b",
        r"\binstall\s+(a\s+)?package\b",
        r"\bpip\s+install\b",
    ]

    request_lower = request.lower()

    for pattern in unsafe_patterns:

        if re.search(
            pattern,
            request_lower
        ):
            return True

    return False


# =========================
# CALCULATOR SAFETY
# =========================

def is_safe_calculation(
    expression: str
) -> bool:

    if not expression:
        return False

    if len(expression) > 200:
        return False

    pattern = r"^[0-9+\-*/().%\s]+$"

    return bool(
        re.fullmatch(
            pattern,
            expression
        )
    )


# =========================
# PYTHON SAFETY
# =========================

def is_safe_python(
    code: str
) -> bool:

    if not code:
        return False

    if len(code) > 2000:
        return False

    blocked_words = [
        "import",
        "__import__",
        "os.",
        "sys.",
        "subprocess",
        "socket",
        "requests",
        "urllib",
        "shutil",
        "pathlib",
        "open(",
        "eval(",
        "exec(",
        "compile(",
        "globals(",
        "locals(",
        "getattr(",
        "setattr(",
        "delattr(",
        "input(",
    ]

    code_lower = code.lower()

    for word in blocked_words:

        if word in code_lower:
            return False

    try:

        tree = ast.parse(
            code,
            mode="exec"
        )

    except SyntaxError:

        return False

    allowed_nodes = (
        ast.Module,
        ast.Expr,
        ast.Assign,
        ast.AnnAssign,
        ast.Name,
        ast.Load,
        ast.Store,
        ast.Constant,
        ast.List,
        ast.Tuple,
        ast.Dict,
        ast.Set,
        ast.BinOp,
        ast.UnaryOp,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Mod,
        ast.Pow,
        ast.FloorDiv,
        ast.USub,
        ast.UAdd,
        ast.Compare,
        ast.Eq,
        ast.NotEq,
        ast.Lt,
        ast.LtE,
        ast.Gt,
        ast.GtE,
        ast.BoolOp,
        ast.And,
        ast.Or,
        ast.IfExp,
        ast.For,
        ast.comprehension,
        ast.ListComp,
        ast.Call,
        ast.FunctionDef,
        ast.Return,
        ast.If,
        ast.Subscript,
        ast.Slice,
        ast.Index,
    )

    for node in ast.walk(tree):

        if not isinstance(
            node,
            allowed_nodes
        ):
            return False

        if isinstance(
            node,
            ast.Call
        ):

            if not isinstance(
                node.func,
                ast.Name
            ):
                return False

            allowed_functions = {
                "print",
                "len",
                "sum",
                "min",
                "max",
                "sorted",
                "range",
                "abs",
                "round",
            }

            if node.func.id not in allowed_functions:
                return False

    return True


# =========================
# EXECUTION LOG
# =========================

def create_execution_log(
    tool: str,
    input_data: str,
    status: str,
    result: str,
):

    return {
        "tool": tool,
        "input": input_data,
        "status": status,
        "result": result,
    }


# =========================
# ERROR RESPONSE
# =========================

def create_error_response(
    tool: str,
    input_data: str,
    message: str,
    execution_logs: list,
    retry_count: int,
):

    output = (
        f"{tool.capitalize()} execution error: "
        f"{message}"
    )

    execution_logs.append(
        create_execution_log(
            tool,
            input_data,
            "error",
            output,
        )
    )

    return {
        "results": [output],
        "final_response": output,

        # IMPORTANT:
        # Mark tool failure so the
        # recovery router can detect it.
        "critique": (
            f"STATUS: ERROR | "
            f"{tool.capitalize()} execution failed: "
            f"{message}"
        ),

        "execution_logs": execution_logs,

        "retry_count": retry_count,
    }


# =========================
# TOOL EXECUTION
# =========================

def execute_registered_tool(
    tool_name: str,
    tool_input: str,
):

    if not is_tool_registered(
        tool_name
    ):

        return {
            "status": "blocked",
            "result": (
                f"Tool '{tool_name}' is not "
                "registered or enabled."
            ),
        }

    tool = get_tool(
        tool_name
    )

    if tool is None:

        return {
            "status": "blocked",
            "result": (
                f"Tool '{tool_name}' is not "
                "available."
            ),
        }

    try:

        result = tool["function"](
            tool_input
        )

        if result is None:

            return {
                "status": "error",
                "result": (
                    "Tool returned an empty result."
                ),
            }

        return {
            "status": "success",
            "result": str(result),
        }

    except Exception as error:

        return {
            "status": "error",
            "result": str(error),
        }


# =========================
# LLM DECISION
# =========================

def get_llm_decision(
    prompt: str,
    retry_count: int,
):

    last_error = None

    for attempt in range(
        retry_count,
        MAX_RETRIES + 1
    ):

        try:

            response = llm.invoke(
                prompt
            )

            decision = str(
                response.content
            ).strip()

            if decision:

                return {
                    "success": True,
                    "decision": decision,
                    "retry_count": attempt,
                    "error": "",
                }

            last_error = (
                "LLM returned an empty response."
            )

        except Exception as error:

            last_error = str(error)

            if attempt < MAX_RETRIES:

                time.sleep(1)

    return {
        "success": False,
        "decision": "",
        "retry_count": MAX_RETRIES,
        "error": (
            last_error
            or "Unknown LLM error."
        ),
    }


# =========================
# EXECUTOR AGENT
# =========================

def executor_agent(
    state: AgentState
):

    user_request = state.get(
        "contextualized_query",
        state["user_input"]
    )

    execution_logs = state.get(
        "execution_logs",
        []
    )

    retry_count = int(
        state.get(
            "retry_count",
            0
        )
    )

    print(
        "\n===== EXECUTOR ====="
    )

    try:

        # =========================
        # SAFETY GUARD
        # =========================

        if contains_unsafe_action(
            user_request
        ):

            output = (
                "Action blocked: this executor does not allow "
                "file, system, shell, network, or environment access."
            )

            print(
                "Safety Guard: BLOCKED"
            )

            execution_logs.append(
                create_execution_log(
                    "none",
                    user_request,
                    "blocked",
                    output,
                )
            )

            return {
                "results": [output],
                "final_response": output,
                "execution_logs":
                    execution_logs,
                "retry_count":
                    retry_count,
            }

        # =========================
        # AVAILABLE TOOLS
        # =========================

        available_tools = (
            list_available_tools()
        )

        print(
            "Available Tools:",
            available_tools
        )

        print(
            "User Request:",
            user_request
        )

        # =========================
        # LLM PROMPT
        # =========================

        prompt = f"""
You are a Safe Executor Agent.

User request:
{user_request}

Available registered tools:
{available_tools}

Choose the appropriate tool.

IMPORTANT SAFETY RULES:

- Only use tools from the registered tools list.
- Do not invent tool names.
- Do not perform file operations.
- Do not access the operating system.
- Do not access the network.
- Do not access environment variables.
- Do not install packages.
- Do not execute shell commands.

AVAILABLE TOOL FORMATS:

1. CALCULATOR

Use calculator for simple mathematical expressions.

Return exactly:

CALCULATE: <expression>


2. PYTHON

Use Python only when the user specifically asks for Python,
Python execution, data processing, loops, lists, or calculations
that require Python.

Return exactly:

PYTHON: <code>


3. NONE

If no tool is required, return exactly:

NO_TOOL

Return ONLY one of these formats.
"""

        # =========================
        # LLM DECISION
        # =========================

        decision_result = get_llm_decision(
            prompt,
            retry_count,
        )

        if not decision_result[
            "success"
        ]:

            error_message = (
                decision_result[
                    "error"
                ]
            )

            new_retry_count = (
                decision_result[
                    "retry_count"
                ]
            )

            output = (
                "Executor could not determine "
                "the required tool after "
                f"{new_retry_count} attempts."
            )

            print(
                "LLM Recovery Failed:",
                error_message
            )

            execution_logs.append(
                create_execution_log(
                    "executor",
                    user_request,
                    "error",
                    (
                        f"{output} "
                        f"Internal error: "
                        f"{error_message}"
                    ),
                )
            )

            return {
                "results": [output],
                "final_response": output,
                "execution_logs":
                    execution_logs,
                "retry_count":
                    new_retry_count,
                "critique": (
                    "STATUS: ERROR | "
                    "Executor LLM failure: "
                    f"{error_message}"
                ),
            }

        decision = (
            decision_result[
                "decision"
            ]
        )

        retry_count = (
            decision_result[
                "retry_count"
            ]
        )

        print(
            "Executor Decision:",
            decision
        )

        # =========================
        # CALCULATOR
        # =========================

        if decision.startswith(
            "CALCULATE:"
        ):

            expression = (
                decision
                .replace(
                    "CALCULATE:",
                    "",
                    1
                )
                .strip()
            )

            if not is_safe_calculation(
                expression
            ):

                output = (
                    "The calculation was blocked because "
                    "the expression was not safe."
                )

                execution_logs.append(
                    create_execution_log(
                        "calculator",
                        expression,
                        "blocked",
                        output,
                    )
                )

                return {
                    "results": [output],
                    "final_response": output,
                    "execution_logs":
                        execution_logs,
                    "retry_count":
                        retry_count,
                }

            execution = (
                execute_registered_tool(
                    "calculator",
                    expression,
                )
            )

            status = execution[
                "status"
            ]

            result = execution[
                "result"
            ]

            # =========================
            # CALCULATOR SUCCESS
            # =========================

            if status == "success":

                output = (
                    f"Calculation: "
                    f"{expression} = {result}"
                )

                execution_logs.append(
                    create_execution_log(
                        "calculator",
                        expression,
                        status,
                        output,
                    )
                )

                return {
                    "results": [output],
                    "final_response": output,
                    "execution_logs":
                        execution_logs,
                    "retry_count":
                        retry_count,
                }

            # =========================
            # CALCULATOR BLOCKED
            # =========================

            if status == "blocked":

                output = result

                execution_logs.append(
                    create_execution_log(
                        "calculator",
                        expression,
                        status,
                        output,
                    )
                )

                return {
                    "results": [output],
                    "final_response": output,
                    "execution_logs":
                        execution_logs,
                    "retry_count":
                        retry_count,
                }

            # =========================
            # CALCULATOR ERROR
            # =========================

            return create_error_response(
                "calculator",
                expression,
                result,
                execution_logs,
                retry_count,
            )

        # =========================
        # PYTHON
        # =========================

        if decision.startswith(
            "PYTHON:"
        ):

            code = (
                decision
                .replace(
                    "PYTHON:",
                    "",
                    1
                )
                .strip()
            )

            if not is_safe_python(
                code
            ):

                output = (
                    "Python execution was blocked because "
                    "the requested code contains an unsafe "
                    "operation."
                )

                execution_logs.append(
                    create_execution_log(
                        "python",
                        code,
                        "blocked",
                        output,
                    )
                )

                return {
                    "results": [output],
                    "final_response": output,
                    "execution_logs":
                        execution_logs,
                    "retry_count":
                        retry_count,
                }

            execution = (
                execute_registered_tool(
                    "python",
                    code,
                )
            )

            status = execution[
                "status"
            ]

            result = execution[
                "result"
            ]

            # =========================
            # PYTHON SUCCESS
            # =========================

            if status == "success":

                output = (
                    f"Python result: "
                    f"{result}"
                )

                execution_logs.append(
                    create_execution_log(
                        "python",
                        code,
                        status,
                        output,
                    )
                )

                return {
                    "results": [output],
                    "final_response": output,
                    "execution_logs":
                        execution_logs,
                    "retry_count":
                        retry_count,
                }

            # =========================
            # PYTHON BLOCKED
            # =========================

            if status == "blocked":

                output = result

                execution_logs.append(
                    create_execution_log(
                        "python",
                        code,
                        status,
                        output,
                    )
                )

                return {
                    "results": [output],
                    "final_response": output,
                    "execution_logs":
                        execution_logs,
                    "retry_count":
                        retry_count,
                }

            # =========================
            # PYTHON ERROR
            # =========================

            return create_error_response(
                "python",
                code,
                result,
                execution_logs,
                retry_count,
            )

        # =========================
        # NO TOOL
        # =========================

        output = (
            f"Task processed: "
            f"{user_request}"
        )

        execution_logs.append(
            create_execution_log(
                "none",
                user_request,
                "not_required",
                output,
            )
        )

        return {
            "results": [output],
            "final_response": output,
            "execution_logs":
                execution_logs,
            "retry_count":
                retry_count,
        }

    # =========================
    # UNEXPECTED ERROR
    # =========================

    except Exception as error:

        output = (
            "Executor error: "
            f"{str(error)}"
        )

        print(
            "Executor Error:",
            str(error)
        )

        execution_logs.append(
            create_execution_log(
                "executor",
                user_request,
                "error",
                output,
            )
        )

        return {
            "results": [output],
            "final_response": output,
            "execution_logs": execution_logs,
            "retry_count": retry_count,
            "critique": (
                "STATUS: ERROR | "
                "Unexpected executor error: "
                f"{str(error)}"
            ),
        }