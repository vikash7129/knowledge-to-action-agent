import ast
import signal


# ============================================================
# SECURITY LIMITS
# ============================================================

MAX_CODE_LENGTH = 5000
MAX_AST_NODES = 250
MAX_NESTING_DEPTH = 20
MAX_COLLECTION_SIZE = 100
EXECUTION_TIMEOUT_SECONDS = 2


# ============================================================
# ALLOWED BUILTINS
# ============================================================

ALLOWED_BUILTINS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "len": len,
    "range": range,
    "sorted": sorted,
    "print": print,
}


# ============================================================
# BLOCKED NAMES
# ============================================================

BLOCKED_NAMES = {
    "__import__",
    "eval",
    "exec",
    "compile",
    "open",
    "input",
    "globals",
    "locals",
    "vars",
    "dir",
    "getattr",
    "setattr",
    "delattr",
    "help",
    "breakpoint",
    "os",
    "sys",
    "subprocess",
    "shutil",
    "socket",
    "requests",
    "urllib",
    "pathlib",
    "builtins",
    "importlib",
    "__class__",
    "__dict__",
    "__bases__",
    "__base__",
    "__subclasses__",
    "__globals__",
    "__code__",
    "__closure__",
    "__func__",
    "__self__",
}


# ============================================================
# ALLOWED AST NODES
# ============================================================

ALLOWED_NODES = (
    ast.Module,
    ast.Assign,
    ast.AnnAssign,
    ast.Expr,
    ast.Name,
    ast.Load,
    ast.Store,
    ast.Constant,
    ast.BinOp,
    ast.UnaryOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.UAdd,
    ast.USub,
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
    ast.Not,
    ast.IfExp,
    ast.List,
    ast.Tuple,
    ast.Call,
    ast.Subscript,
    ast.Slice,
)


# ============================================================
# SECURITY EXCEPTION
# ============================================================

class PythonExecutionTimeout(Exception):
    pass


# ============================================================
# TIMEOUT HANDLER
# ============================================================

def _timeout_handler(signum, frame):
    raise PythonExecutionTimeout(
        "Python execution exceeded the allowed time limit."
    )


# ============================================================
# SECURITY VALIDATOR
# ============================================================

class SecurityValidator(ast.NodeVisitor):

    def __init__(self):
        self.errors = []
        self.node_count = 0
        self.max_depth = 0

    def visit(self, node, depth=0):

        self.node_count += 1

        if self.node_count > MAX_AST_NODES:
            self.errors.append(
                f"Code contains too many operations. "
                f"Maximum allowed AST nodes: {MAX_AST_NODES}."
            )
            return

        self.max_depth = max(
            self.max_depth,
            depth,
        )

        if self.max_depth > MAX_NESTING_DEPTH:
            self.errors.append(
                f"Code nesting is too deep. "
                f"Maximum depth: {MAX_NESTING_DEPTH}."
            )
            return

        method = "visit_" + node.__class__.__name__

        visitor = getattr(
            self,
            method,
            self.generic_visit,
        )

        visitor(node, depth)

    def generic_visit(self, node, depth=0):

        if not isinstance(node, ALLOWED_NODES):
            self.errors.append(
                f"Blocked syntax: "
                f"{type(node).__name__}"
            )
            return

        for child in ast.iter_child_nodes(node):
            self.visit(
                child,
                depth + 1,
            )

    def visit_Name(self, node, depth=0):

        if node.id in BLOCKED_NAMES:
            self.errors.append(
                f"Blocked name: {node.id}"
            )
            return

        if node.id.startswith("__"):
            self.errors.append(
                f"Private/dunder name blocked: {node.id}"
            )
            return

        if node.id == "range":
            return

    def visit_Attribute(self, node, depth=0):

        self.errors.append(
            "Attribute access is not allowed."
        )

    def visit_Call(self, node, depth=0):

        if not isinstance(
            node.func,
            ast.Name,
        ):
            self.errors.append(
                "Only approved functions can be called."
            )
            return

        function_name = node.func.id

        if function_name not in ALLOWED_BUILTINS:
            self.errors.append(
                f"Function '{function_name}' is not allowed."
            )
            return

        for argument in node.args:
            self.visit(
                argument,
                depth + 1,
            )

        for keyword in node.keywords:
            self.visit(
                keyword.value,
                depth + 1,
            )

    def visit_Assign(self, node, depth=0):

        for target in node.targets:

            if not isinstance(
                target,
                ast.Name,
            ):
                self.errors.append(
                    "Only simple variable assignment "
                    "is allowed."
                )
                continue

            if target.id.startswith("__"):
                self.errors.append(
                    f"Private variable blocked: "
                    f"{target.id}"
                )

        self.visit(
            node.value,
            depth + 1,
        )

    def visit_List(self, node, depth=0):

        if len(node.elts) > MAX_COLLECTION_SIZE:
            self.errors.append(
                f"List contains too many items. "
                f"Maximum: {MAX_COLLECTION_SIZE}."
            )
            return

        for element in node.elts:
            self.visit(
                element,
                depth + 1,
            )

    def visit_Tuple(self, node, depth=0):

        if len(node.elts) > MAX_COLLECTION_SIZE:
            self.errors.append(
                f"Tuple contains too many items. "
                f"Maximum: {MAX_COLLECTION_SIZE}."
            )
            return

        for element in node.elts:
            self.visit(
                element,
                depth + 1,
            )

    def visit_Constant(self, node, depth=0):

        if isinstance(
            node.value,
            str,
        ):
            if len(node.value) > 1000:
                self.errors.append(
                    "String constant is too large."
                )

        if isinstance(
            node.value,
            (int, float),
        ):
            if abs(node.value) > 10**12:
                self.errors.append(
                    "Numeric constant is too large."
                )


# ============================================================
# CODE VALIDATION
# ============================================================

def validate_code(code: str):

    if not isinstance(code, str):
        return (
            False,
            "Python code must be a string.",
        )

    code = code.strip()

    if not code:
        return (
            False,
            "Empty Python code.",
        )

    if len(code) > MAX_CODE_LENGTH:
        return (
            False,
            "Python code is too large. "
            f"Maximum allowed size is {MAX_CODE_LENGTH} characters.",
        )

    try:
        tree = ast.parse(
            code,
            mode="exec",
        )

    except SyntaxError as error:

        return (
            False,
            f"Invalid Python syntax: {error}",
        )

    validator = SecurityValidator()

    validator.visit(tree)

    if validator.errors:

        return (
            False,
            "; ".join(
                validator.errors[:5]
            ),
        )

    return (
        True,
        "Code passed security validation.",
    )


# ============================================================
# SAFE PYTHON EXECUTION
# ============================================================

def run_python(code: str) -> str:

    is_valid, validation_message = (
        validate_code(code)
    )

    if not is_valid:
        return (
            "Python security error: "
            + validation_message
        )

    safe_globals = {
        "__builtins__": ALLOWED_BUILTINS
    }

    local_vars = {}

    previous_handler = None

    try:

        # Unix/Linux/macOS timeout support
        if hasattr(
            signal,
            "SIGALRM",
        ):

            previous_handler = signal.signal(
                signal.SIGALRM,
                _timeout_handler,
            )

            signal.alarm(
                EXECUTION_TIMEOUT_SECONDS
            )

        exec(
            code,
            safe_globals,
            local_vars,
        )

        if "result" in local_vars:

            return str(
                local_vars["result"]
            )

        visible_variables = {
            key: value
            for key, value in local_vars.items()
            if not key.startswith("_")
        }

        if visible_variables:
            return str(
                visible_variables
            )

        return (
            "Python code executed successfully."
        )

    except PythonExecutionTimeout:

        return (
            "Python execution error: "
            "execution time limit exceeded."
        )

    except ZeroDivisionError:

        return (
            "Python execution error: "
            "division by zero"
        )

    except MemoryError:

        return (
            "Python execution error: "
            "memory limit exceeded."
        )

    except RecursionError:

        return (
            "Python execution error: "
            "recursion limit exceeded."
        )

    except Exception as error:

        return (
            "Python execution error: "
            f"{str(error)}"
        )

    finally:

        if hasattr(
            signal,
            "SIGALRM",
        ):

            signal.alarm(0)

            if previous_handler is not None:

                signal.signal(
                    signal.SIGALRM,
                    previous_handler,
                )