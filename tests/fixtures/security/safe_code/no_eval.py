# Safe code sample: Safe Alternatives to Eval
# These patterns should NOT trigger security warnings

import ast
import json
import operator


def safe_parse_literal(expr):
    """Safe: Using ast.literal_eval for safe literal parsing."""
    return ast.literal_eval(expr)


def parse_json(json_string):
    """Safe: Using json.loads for JSON parsing."""
    return json.loads(json_string)


def safe_math(a, b, op):
    """Safe: Using operator module instead of eval."""
    operations = {
        "+": operator.add,
        "-": operator.sub,
        "*": operator.mul,
        "/": operator.truediv,
    }
    if op in operations:
        return operations[op](a, b)
    raise ValueError(f"Unknown operator: {op}")


# Safe: Using importlib for dynamic imports
import importlib


def dynamic_import(module_name):
    """Safe: Using importlib for dynamic module loading."""
    if module_name in ALLOWED_MODULES:
        return importlib.import_module(module_name)
    raise ValueError(f"Module not allowed: {module_name}")


ALLOWED_MODULES = {"json", "os", "sys"}


# Safe: Using restricted expression parser
def parse_math_expression(expr):
    """Safe: Custom expression parser with allowed operations only."""
    # Implement custom parser instead of eval
    allowed_chars = set("0123456789+-*/. ")
    if not all(c in allowed_chars for c in expr):
        raise ValueError("Invalid characters in expression")
    # Safe numeric calculation
    return safe_calculate(expr)


def safe_calculate(expr):
    """Safe calculator using ast module."""
    tree = ast.parse(expr, mode="eval")
    # Validate only safe nodes are used
    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Expression, ast.BinOp, ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div)
        ):
            raise ValueError("Unsafe expression")
    return eval(compile(tree, "<expr>", "eval"))
