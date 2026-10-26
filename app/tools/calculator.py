import ast
import operator


# ============================================================
# SECURITY LIMITS
# ============================================================

MAX_EXPRESSION_LENGTH = 500
MAX_POWER = 100
MAX_ABSOLUTE_NUMBER = 10**12
MAX_AST_NODES = 100
MAX_NESTING_DEPTH = 15


# ============================================================
# OPERATORS
# ============================================================

BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


# ============================================================
# SAFE CALCULATOR
# ============================================================

class SafeCalculator(ast.NodeVisitor):

    def __init__(self):
        self.node_count = 0
        self.max_depth = 0

    def visit(self, node, depth=0):

        self.node_count += 1

        if self.node_count > MAX_AST_NODES:
            raise ValueError(
                "Expression contains too many operations."
            )

        self.max_depth = max(
            self.max_depth,
            depth,
        )

        if self.max_depth > MAX_NESTING_DEPTH:
            raise ValueError(
                "Expression nesting is too deep."
            )

        method = "visit_" + node.__class__.__name__

        visitor = getattr(
            self,
            method,
            self.generic_visit,
        )

        return visitor(
            node,
            depth,
        )

    def visit_Expression(
        self,
        node,
        depth=0,
    ):
        return self.visit(
            node.body,
            depth + 1,
        )

    def visit_Constant(
        self,
        node,
        depth=0,
    ):

        if not isinstance(
            node.value,
            (int, float),
        ):
            raise ValueError(
                "Only numeric values are allowed."
            )

        if abs(node.value) > MAX_ABSOLUTE_NUMBER:
            raise ValueError(
                "Number exceeds the allowed limit."
            )

        return node.value

    def visit_BinOp(
        self,
        node,
        depth=0,
    ):

        operator_type = type(node.op)

        if operator_type not in BINARY_OPERATORS:
            raise ValueError(
                "This mathematical operator "
                "is not allowed."
            )

        left = self.visit(
            node.left,
            depth + 1,
        )

        right = self.visit(
            node.right,
            depth + 1,
        )

        if operator_type in (
            ast.Div,
            ast.FloorDiv,
            ast.Mod,
        ):

            if right == 0:
                raise ZeroDivisionError(
                    "division by zero"
                )

        if operator_type is ast.Pow:

            if abs(right) > MAX_POWER:
                raise ValueError(
                    "Exponent is too large."
                )

            if abs(left) > 1000:
                raise ValueError(
                    "Base is too large for exponentiation."
                )

        operation = BINARY_OPERATORS[
            operator_type
        ]

        try:

            result = operation(
                left,
                right,
            )

        except OverflowError:

            raise ValueError(
                "Calculation result is too large."
            )

        if isinstance(
            result,
            (int, float),
        ):

            if abs(result) > MAX_ABSOLUTE_NUMBER:

                raise ValueError(
                    "Calculation result "
                    "exceeds the allowed limit."
                )

        return result

    def visit_UnaryOp(
        self,
        node,
        depth=0,
    ):

        operator_type = type(node.op)

        if operator_type not in UNARY_OPERATORS:
            raise ValueError(
                "This unary operator "
                "is not allowed."
            )

        operand = self.visit(
            node.operand,
            depth + 1,
        )

        return UNARY_OPERATORS[
            operator_type
        ](operand)

    def generic_visit(
        self,
        node,
        depth=0,
    ):

        raise ValueError(
            f"Unsupported expression: "
            f"{type(node).__name__}"
        )


# ============================================================
# CALCULATOR
# ============================================================

def calculator(
    expression: str,
) -> str:

    if not isinstance(
        expression,
        str,
    ):
        raise ValueError(
            "Expression must be a string."
        )

    expression = expression.strip()

    if not expression:
        raise ValueError(
            "Empty expression."
        )

    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise ValueError(
            "Expression is too long."
        )

    try:

        tree = ast.parse(
            expression,
            mode="eval",
        )

    except SyntaxError:

        raise ValueError(
            "Invalid mathematical expression."
        )

    evaluator = SafeCalculator()

    try:

        result = evaluator.visit(tree)

    except ZeroDivisionError:

        raise ZeroDivisionError(
            "division by zero"
        )

    except ValueError:

        raise

    except Exception as error:

        raise ValueError(
            "Unable to calculate "
            "the expression."
        ) from error

    if not isinstance(
        result,
        (int, float),
    ):
        raise ValueError(
            "Calculation produced "
            "an invalid result."
        )

    return str(result)