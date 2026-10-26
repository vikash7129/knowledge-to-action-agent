import os
import re

from app.security import (
    validate_required_secrets,
    get_secret_status,
)
from app.tools.registry import (
    validate_registry,
    list_available_tools,
)
from app.tools.calculator import calculator
from app.tools.python_tool import (
    run_python,
    validate_code,
)


# ============================================================
# SECURITY REVIEW CONFIG
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
    )
)

IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "data",
    ".idea",
    ".vscode",
}

SECRET_PATTERNS = (
    r"AIza[0-9A-Za-z_\-]{20,}",
    r"tvly-[0-9A-Za-z_\-]{10,}",
    r"sk-[0-9A-Za-z_\-]{20,}",
)


# ============================================================
# RESULT STORAGE
# ============================================================

def create_result(
    name: str,
    passed: bool,
    message: str,
) -> dict:

    return {
        "name": name,
        "passed": passed,
        "message": message,
    }


# ============================================================
# CHECK ENVIRONMENT SECRETS
# ============================================================

def check_environment_secrets() -> dict:

    valid, missing = (
        validate_required_secrets()
    )

    if valid:
        return create_result(
            "Environment secrets",
            True,
            "Required API secrets are available.",
        )

    return create_result(
        "Environment secrets",
        False,
        "Missing secrets: "
        + ", ".join(missing),
    )


# ============================================================
# CHECK SECRET STATUS
# ============================================================

def check_secret_visibility() -> dict:

    status = get_secret_status()

    # Values must never appear in the status.
    if not all(
        isinstance(value, bool)
        for value in status.values()
    ):
        return create_result(
            "Secret visibility",
            False,
            "Secret status contains unexpected values.",
        )

    return create_result(
        "Secret visibility",
        True,
        "Only secret presence is exposed; values are hidden.",
    )


# ============================================================
# CHECK TOOL REGISTRY
# ============================================================

def check_tool_registry() -> dict:

    valid, errors = validate_registry()

    if valid:
        return create_result(
            "Tool registry",
            True,
            "All registered tools passed validation.",
        )

    return create_result(
        "Tool registry",
        False,
        "; ".join(errors),
    )


# ============================================================
# CHECK AVAILABLE TOOLS
# ============================================================

def check_authorized_tools() -> dict:

    tools = list_available_tools()

    if not tools:
        return create_result(
            "Authorized tools",
            False,
            "No authorized tools are available.",
        )

    return create_result(
        "Authorized tools",
        True,
        "Authorized tools: "
        + ", ".join(tools),
    )


# ============================================================
# CHECK CALCULATOR
# ============================================================

def check_calculator_security() -> dict:

    try:

        safe_result = calculator(
            "25 * 4 + 10"
        )

        if safe_result != "110":
            return create_result(
                "Calculator security",
                False,
                "Safe calculator test returned an unexpected result.",
            )

        try:
            calculator(
                "__import__('os')"
            )

            return create_result(
                "Calculator security",
                False,
                "Unsafe calculator expression was accepted.",
            )

        except Exception:
            pass

        return create_result(
            "Calculator security",
            True,
            "Safe calculation works and unsafe syntax is blocked.",
        )

    except Exception as error:

        return create_result(
            "Calculator security",
            False,
            f"Calculator check failed: {error}",
        )


# ============================================================
# CHECK PYTHON TOOL
# ============================================================

def check_python_security() -> dict:

    try:

        safe_result = run_python(
            "result = 25 * 4"
        )

        if safe_result != "100":
            return create_result(
                "Python security",
                False,
                "Safe Python test returned an unexpected result.",
            )

        valid, _ = validate_code(
            "import os"
        )

        if valid:
            return create_result(
                "Python security",
                False,
                "Unsafe import was accepted.",
            )

        valid, _ = validate_code(
            "result = __import__('os')"
        )

        if valid:
            return create_result(
                "Python security",
                False,
                "Unsafe builtin access was accepted.",
            )

        return create_result(
            "Python security",
            True,
            "Safe execution works and unsafe operations are blocked.",
        )

    except Exception as error:

        return create_result(
            "Python security",
            False,
            f"Python security check failed: {error}",
        )


# ============================================================
# SCAN SOURCE FILES FOR EXPOSED SECRETS
# ============================================================

def scan_source_for_secrets() -> dict:

    findings = []

    for root, directories, files in os.walk(
        PROJECT_ROOT
    ):

        directories[:] = [
            directory
            for directory in directories
            if directory not in IGNORED_DIRECTORIES
        ]

        for filename in files:

            if not filename.endswith(
                ".py"
            ):
                continue

            filepath = os.path.join(
                root,
                filename,
            )

            try:

                with open(
                    filepath,
                    "r",
                    encoding="utf-8",
                ) as file:

                    content = file.read()

            except (
                OSError,
                UnicodeDecodeError,
            ):
                continue

            for pattern in SECRET_PATTERNS:

                if re.search(
                    pattern,
                    content,
                ):

                    relative_path = os.path.relpath(
                        filepath,
                        PROJECT_ROOT,
                    )

                    findings.append(
                        relative_path
                    )

                    break

    if findings:

        return create_result(
            "Source secret scan",
            False,
            "Possible hardcoded secret pattern found in: "
            + ", ".join(findings),
        )

    return create_result(
        "Source secret scan",
        True,
        "No hardcoded API-key pattern detected in Python source files.",
    )


# ============================================================
# RUN COMPLETE SECURITY REVIEW
# ============================================================

def run_security_review() -> list[dict]:

    return [
        check_environment_secrets(),
        check_secret_visibility(),
        check_tool_registry(),
        check_authorized_tools(),
        check_calculator_security(),
        check_python_security(),
        scan_source_for_secrets(),
    ]


# ============================================================
# PRINT SECURITY REPORT
# ============================================================

def print_security_report() -> bool:

    results = run_security_review()

    print("\n" + "=" * 60)
    print("FINAL SECURITY REVIEW")
    print("=" * 60)

    passed_count = 0

    for result in results:

        status = (
            "PASS"
            if result["passed"]
            else "FAIL"
        )

        print(
            f"[{status}] "
            f"{result['name']}: "
            f"{result['message']}"
        )

        if result["passed"]:
            passed_count += 1

    total = len(results)

    print("=" * 60)
    print(
        f"Security checks passed: "
        f"{passed_count}/{total}"
    )

    if passed_count == total:

        print(
            "FINAL SECURITY STATUS: PASS"
        )

        return True

    print(
        "FINAL SECURITY STATUS: REVIEW REQUIRED"
    )

    return False


# ============================================================
# DIRECT EXECUTION
# ============================================================

if __name__ == "__main__":

    success = print_security_report()

    raise SystemExit(
        0 if success else 1
    )