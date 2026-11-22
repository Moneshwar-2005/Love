"""
Safe Calculator Tool for Universal Work Intelligence (Phase 05).
Evaluates mathematical expressions, percentages, and algebra via AST node parsing without eval().
"""

import ast
import math
import operator
import re
from typing import Any, Dict

from backend.app.work.schemas import PermissionLevel, RiskLevel
from backend.app.work.tools.base import BaseTool


class SafeMathEvaluator(ast.NodeVisitor):
    """
    Safely traverses and computes AST expressions using a strictly bounded operator and function whitelist.
    Prohibits variable lookups, code execution, imports, and arbitrary function calls.
    """

    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    ALLOWED_FUNCTIONS = {
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "abs": abs,
        "round": round,
        "ceil": math.ceil,
        "floor": math.floor,
    }

    ALLOWED_CONSTANTS = {
        "pi": math.pi,
        "e": math.e,
    }

    def visit(self, node: ast.AST) -> float:
        method = f"visit_{node.__class__.__name__}"
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: ast.AST) -> float:
        raise ValueError(f"Disallowed mathematical operation or construct: {node.__class__.__name__}")

    def visit_Expression(self, node: ast.Expression) -> float:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> float:
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError(f"Only numerical constants are permitted in expressions, got: {type(node.value).__name__}")

    def visit_BinOp(self, node: ast.BinOp) -> float:
        left = self.visit(node.left)
        right = self.visit(node.right)
        op_type = type(node.op)
        if op_type not in self.OPERATORS:
            raise ValueError(f"Unsupported binary operator: {op_type.__name__}")
        if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
            raise ZeroDivisionError("Division by zero in mathematical expression.")
        # Guard against absurd exponent computation
        if op_type is ast.Pow and (abs(left) > 1e6 or right > 1000):
            raise OverflowError("Exponentiation exceeds safe magnitude threshold.")
        return self.OPERATORS[op_type](left, right)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> float:
        operand = self.visit(node.operand)
        op_type = type(node.op)
        if op_type not in self.OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        return self.OPERATORS[op_type](operand)

    def visit_Name(self, node: ast.Name) -> float:
        name_lower = node.id.lower()
        if name_lower in self.ALLOWED_CONSTANTS:
            return self.ALLOWED_CONSTANTS[name_lower]
        raise ValueError(f"Unknown or unauthorized identifier: '{node.id}'")

    def visit_Call(self, node: ast.Call) -> float:
        if not isinstance(node.func, ast.Name):
            raise ValueError("Security restriction: Only direct whitelisted math functions can be invoked.")
        func_name = node.func.id.lower()
        if func_name not in self.ALLOWED_FUNCTIONS:
            raise ValueError(f"Security restriction: Function '{func_name}' is not in the authorized mathematical whitelist.")
        args = [self.visit(arg) for arg in node.args]
        return self.ALLOWED_FUNCTIONS[func_name](*args)


class CalculatorTool(BaseTool):
    """
    Safely computes arithmetic and mathematical expressions.
    """

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return (
            "Evaluates arithmetic calculations, percentages, trigonometric functions, "
            "logarithms, and mathematical expressions using a secure AST sandbox."
        )

    @property
    def category(self) -> str:
        return "math"

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.LOW

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.AUTO_PERMIT

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression (e.g. '2 + 2', 'sqrt(144) + 10', '15% of 350')"
                }
            },
            "required": ["expression"]
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {"type": "string"},
                "result": {"type": "number"},
                "formatted": {"type": "string"}
            }
        }

    @staticmethod
    def _preprocess_percentage(expr: str) -> str:
        """Preprocesses 'X% of Y' or 'X%' into standard mathematical notation."""
        # e.g. "15% of 250" -> "(15 / 100 * 250)"
        cleaned = re.sub(
            r"(\d+(?:\.\d+)?)\s*%\s*(?:of|\*)\s*(\d+(?:\.\d+)?)",
            r"(\1 / 100.0 * \2)",
            expr,
            flags=re.IGNORECASE
        )
        # e.g. "15%" -> "(15 / 100.0)"
        cleaned = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"(\1 / 100.0)", cleaned)
        return cleaned

    async def run(self, **kwargs) -> Dict[str, Any]:
        expression = kwargs.get("expression", "").strip()
        if not expression:
            raise ValueError("Expression parameter cannot be empty.")

        if len(expression) > 300:
            raise ValueError("Mathematical expression exceeds maximum allowable length of 300 characters.")

        # Clean up any trailing conversational requests like "and explain the result"
        cleaned_expr = re.sub(
            r"\s+(?:and\s+)?(?:explain|tell me|show work|show the result|detail|summarize|please).*$",
            "",
            expression,
            flags=re.IGNORECASE
        ).strip()
        cleaned_expr = re.sub(r"^(?:calculate|compute|solve|what is)\s+", "", cleaned_expr, flags=re.IGNORECASE).strip()
        normalized_expr = self._preprocess_percentage(cleaned_expr or expression)

        try:
            tree = ast.parse(normalized_expr, mode="eval")
        except SyntaxError as exc:
            raise ValueError(f"Invalid mathematical syntax: {exc}") from exc

        evaluator = SafeMathEvaluator()
        try:
            result_value = evaluator.visit(tree)
        except ZeroDivisionError as zde:
            raise ValueError(f"Division by zero: {zde}") from zde

        # Simplify integer floats (e.g. 4.0 -> 4)
        if isinstance(result_value, float) and result_value.is_integer() and abs(result_value) < 1e15:
            display_result = int(result_value)
        else:
            display_result = round(result_value, 6)

        return {
            "expression": expression,
            "result": display_result,
            "formatted": str(display_result),
        }

