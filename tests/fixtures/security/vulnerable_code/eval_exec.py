# Vulnerable code sample: Eval/Exec Usage
# These patterns should be detected by SecurityChecker


def calculate_expression(expr):
    """Vulnerable: Using eval on user input."""
    return eval(expr)  # Never eval user input!


def execute_code(code_string):
    """Vulnerable: Using exec on arbitrary code."""
    exec(code_string)  # Extremely dangerous!


def dynamic_import(module_name):
    """Vulnerable: Using eval for imports."""
    module = eval(f"import {module_name}")
    return module


def process_formula(formula):
    """Vulnerable: eval in mathematical context."""
    result = eval(formula)
    return result


# Also detectable patterns
compile_and_run = lambda code: exec(compile(code, "<string>", "exec"))
