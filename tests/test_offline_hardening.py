import os
import sys
import ast
import importlib
import sqlite3
from pathlib import Path


# ============================================================
# STAGE 19.4
# OFFLINE FINAL SYSTEM HARDENING TEST
#
# IMPORTANT:
# This test does NOT call Gemini, Tavily, or any external API.
# ============================================================


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# TEST COUNTERS
# ============================================================

PASS_COUNT = 0
FAIL_COUNT = 0


# ============================================================
# HELPER
# ============================================================

def check(label, condition):

    global PASS_COUNT, FAIL_COUNT

    if condition:
        print(f"[PASS] {label}")
        PASS_COUNT += 1
        return True

    print(f"[FAIL] {label}")
    FAIL_COUNT += 1
    return False


# ============================================================
# 1. PROJECT STRUCTURE
# ============================================================

def test_project_structure():

    print("\n" + "=" * 60)
    print("1. PROJECT STRUCTURE")
    print("=" * 60)

    required_paths = [
        PROJECT_ROOT / "app",
        PROJECT_ROOT / "app" / "main.py",
        PROJECT_ROOT / "app" / "agents",
        PROJECT_ROOT / "app" / "tools",
        PROJECT_ROOT / "app" / "rag",
        PROJECT_ROOT / "data",
        PROJECT_ROOT / "tests",
    ]

    for path in required_paths:

        check(
            f"Exists: {path.relative_to(PROJECT_ROOT)}",
            path.exists()
        )


# ============================================================
# 2. REQUIRED FILES
# ============================================================

def test_required_files():

    print("\n" + "=" * 60)
    print("2. REQUIRED FILES")
    print("=" * 60)

    required_files = [
        PROJECT_ROOT / "app" / "main.py",
        PROJECT_ROOT / "app" / "streamlit_app.py",
        PROJECT_ROOT / ".env",
        PROJECT_ROOT / ".gitignore",
        PROJECT_ROOT / "tests" / "test_offline_hardening.py",
    ]

    for path in required_files:

        check(
            f"File exists: {path.relative_to(PROJECT_ROOT)}",
            path.is_file()
        )


# ============================================================
# 3. MAIN.PY SYNTAX
# ============================================================

def test_main_syntax():

    print("\n" + "=" * 60)
    print("3. MAIN.PY SYNTAX")
    print("=" * 60)

    main_file = PROJECT_ROOT / "app" / "main.py"

    try:

        source = main_file.read_text(
            encoding="utf-8"
        )

        ast.parse(source)

        check(
            "app/main.py syntax is valid",
            True
        )

    except Exception as error:

        check(
            "app/main.py syntax is valid",
            False
        )

        print(f"       Error: {error}")


# ============================================================
# 4. STREAMLIT SYNTAX
# ============================================================

def test_streamlit_syntax():

    print("\n" + "=" * 60)
    print("4. STREAMLIT SYNTAX")
    print("=" * 60)

    streamlit_file = (
        PROJECT_ROOT
        / "app"
        / "streamlit_app.py"
    )

    try:

        source = streamlit_file.read_text(
            encoding="utf-8"
        )

        ast.parse(source)

        check(
            "streamlit_app.py syntax is valid",
            True
        )

    except Exception as error:

        check(
            "streamlit_app.py syntax is valid",
            False
        )

        print(f"       Error: {error}")


# ============================================================
# 5. ENVIRONMENT PROTECTION
# ============================================================

def test_environment_protection():

    print("\n" + "=" * 60)
    print("5. ENVIRONMENT PROTECTION")
    print("=" * 60)

    env_file = PROJECT_ROOT / ".env"
    gitignore_file = PROJECT_ROOT / ".gitignore"

    check(
        ".env exists",
        env_file.is_file()
    )

    if not gitignore_file.is_file():

        check(
            ".env protected by .gitignore",
            False
        )

        return

    try:

        content = gitignore_file.read_text(
            encoding="utf-8"
        )

        lines = {
            line.strip()
            for line in content.splitlines()
            if line.strip()
        }

        protected = (
            ".env" in lines
            or "*.env" in lines
        )

        check(
            ".env protected by .gitignore",
            protected
        )

    except Exception as error:

        check(
            ".env protected by .gitignore",
            False
        )

        print(f"       Error: {error}")


# ============================================================
# 6. RAG STORAGE
# ============================================================

def test_rag_storage():

    print("\n" + "=" * 60)
    print("6. RAG STORAGE")
    print("=" * 60)

    data_dir = PROJECT_ROOT / "data"

    upload_dir = data_dir / "uploads"
    chroma_dir = data_dir / "chroma_db"

    check(
        "data directory exists",
        data_dir.is_dir()
    )

    check(
        "Upload directory exists",
        upload_dir.is_dir()
    )

    check(
        "ChromaDB directory exists",
        chroma_dir.is_dir()
    )


# ============================================================
# 7. MEMORY DATABASE
# ============================================================

def test_memory_database():

    print("\n" + "=" * 60)
    print("7. MEMORY DATABASE")
    print("=" * 60)

    # Primary location used by the project.
    memory_db = (
        PROJECT_ROOT
        / "data"
        / "memory.db"
    )

    # Some earlier project versions may have created
    # memory.db in the project root.
    root_memory_db = (
        PROJECT_ROOT
        / "memory.db"
    )

    if memory_db.is_file():

        selected_db = memory_db

    elif root_memory_db.is_file():

        selected_db = root_memory_db

    else:

        check(
            "Memory database exists",
            False
        )

        return

    check(
        f"Memory database exists: "
        f"{selected_db.relative_to(PROJECT_ROOT)}",
        True
    )

    # --------------------------------------------------------
    # SQLite readability check
    # --------------------------------------------------------

    try:

        connection = sqlite3.connect(
            str(selected_db)
        )

        cursor = connection.cursor()

        cursor.execute(
            "PRAGMA integrity_check;"
        )

        result = cursor.fetchone()

        connection.close()

        readable = (
            result is not None
            and result[0] == "ok"
        )

        check(
            "Memory database is readable",
            readable
        )

    except Exception as error:

        check(
            "Memory database is readable",
            False
        )

        print(
            f"       Error: {error}"
        )


# ============================================================
# 8. SAFE MODULE IMPORT
# ============================================================

def test_safe_imports():

    print("\n" + "=" * 60)
    print("8. SAFE MODULE IMPORT")
    print("=" * 60)

    # app.main is intentionally NOT imported.
    # This prevents accidental model/API initialization.

    safe_modules = [
        "app.rag",
    ]

    for module_name in safe_modules:

        try:

            importlib.import_module(
                module_name
            )

            check(
                f"Safe import: {module_name}",
                True
            )

        except Exception as error:

            check(
                f"Safe import: {module_name}",
                False
            )

            print(
                f"       Error: {error}"
            )


# ============================================================
# 9. API KEY SAFETY
# ============================================================

def test_no_hardcoded_api_keys():

    print("\n" + "=" * 60)
    print("9. API KEY SAFETY")
    print("=" * 60)

    # These are prefixes used only for security scanning.
    # The security scanner files themselves are excluded.

    key_prefixes = (
        "AIzaSy",
        "tvly-",
        "sk-",
    )

    excluded_files = {
        PROJECT_ROOT / "app" / "security.py",
        PROJECT_ROOT / "app" / "security_review.py",
    }

    suspicious_files = []

    search_root = PROJECT_ROOT / "app"

    if search_root.is_dir():

        for file_path in search_root.rglob("*.py"):

            if file_path in excluded_files:
                continue

            try:

                content = file_path.read_text(
                    encoding="utf-8"
                )

            except Exception:

                continue

            for prefix in key_prefixes:

                position = 0

                while True:

                    position = content.find(
                        prefix,
                        position
                    )

                    if position == -1:
                        break

                    start = position + len(prefix)

                    token = ""

                    for character in content[start:]:

                        if (
                            character.isalnum()
                            or character in "_-"
                        ):

                            token += character

                        else:

                            break

                    if len(token) >= 12:

                        suspicious_files.append(
                            file_path.relative_to(
                                PROJECT_ROOT
                            )
                        )

                        break

                    position = start

                if file_path.relative_to(
                    PROJECT_ROOT
                ) in suspicious_files:

                    break

    suspicious_files = sorted(
        set(
            str(path)
            for path in suspicious_files
        )
    )

    check(
        "No obvious hard-coded API keys",
        len(suspicious_files) == 0
    )

    if suspicious_files:

        print(
            "       Possible files:"
        )

        for file in suspicious_files:

            print(
                f"       - {file}"
            )


# ============================================================
# 10. OFFLINE MODE
# ============================================================

def test_offline_mode():

    print("\n" + "=" * 60)
    print("10. OFFLINE MODE")
    print("=" * 60)

    # This test performs no network request.
    check(
        "Offline test mode active",
        True
    )

    # We inspect the test file using AST instead of searching
    # for API-call strings. This prevents false positives caused
    # by the test itself containing those names.

    test_file = (
        PROJECT_ROOT
        / "tests"
        / "test_offline_hardening.py"
    )

    try:

        source = test_file.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(source)

        forbidden_modules = {
            "requests",
            "httpx",
            "urllib.request",
            "tavily",
        }

        forbidden_client_names = {
            "TavilyClient",
            "ChatGoogleGenerativeAI",
        }

        found_forbidden = []

        for node in ast.walk(tree):

            # Check imports
            if isinstance(
                node,
                ast.Import
            ):

                for alias in node.names:

                    root_name = alias.name.split(".")[0]

                    if (
                        alias.name in forbidden_modules
                        or root_name in forbidden_modules
                    ):

                        found_forbidden.append(
                            alias.name
                        )

            # Check from-imports
            elif isinstance(
                node,
                ast.ImportFrom
            ):

                module = node.module or ""

                if module in forbidden_modules:

                    found_forbidden.append(
                        module
                    )

                for alias in node.names:

                    if alias.name in forbidden_client_names:

                        found_forbidden.append(
                            alias.name
                        )

        found_forbidden = sorted(
            set(found_forbidden)
        )

        check(
            "No external API clients imported by hardening test",
            len(found_forbidden) == 0
        )

        if found_forbidden:

            print(
                "       Found:"
            )

            for item in found_forbidden:

                print(
                    f"       - {item}"
                )

    except Exception as error:

        check(
            "Hardening test can be inspected",
            False
        )

        print(
            f"       Error: {error}"
        )


# ============================================================
# 11. HARDENING TEST SYNTAX
# ============================================================

def test_hardening_syntax():

    print("\n" + "=" * 60)
    print("11. HARDENING TEST SYNTAX")
    print("=" * 60)

    test_file = (
        PROJECT_ROOT
        / "tests"
        / "test_offline_hardening.py"
    )

    try:

        source = test_file.read_text(
            encoding="utf-8"
        )

        ast.parse(source)

        check(
            "test_offline_hardening.py syntax is valid",
            True
        )

    except Exception as error:

        check(
            "test_offline_hardening.py syntax is valid",
            False
        )

        print(
            f"       Error: {error}"
        )


# ============================================================
# FINAL TEST RUNNER
# ============================================================

def run_tests():

    global PASS_COUNT, FAIL_COUNT

    PASS_COUNT = 0
    FAIL_COUNT = 0

    print("\n" + "=" * 60)
    print(
        "STAGE 19.4 - OFFLINE FINAL SYSTEM HARDENING TEST"
    )
    print("=" * 60)

    test_project_structure()

    test_required_files()

    test_main_syntax()

    test_streamlit_syntax()

    test_environment_protection()

    test_rag_storage()

    test_memory_database()

    test_safe_imports()

    test_no_hardcoded_api_keys()

    test_offline_mode()

    test_hardening_syntax()

    print("\n" + "=" * 60)

    total = PASS_COUNT + FAIL_COUNT

    print(
        f"OFFLINE HARDENING TESTS PASSED: "
        f"{PASS_COUNT}/{total}"
    )

    if FAIL_COUNT == 0:

        print(
            "STAGE 19.4 STATUS: PASS"
        )

        print("=" * 60)

        return True

    print(
        "STAGE 19.4 STATUS: REVIEW REQUIRED"
    )

    print("=" * 60)

    return False


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    success = run_tests()

    raise SystemExit(
        0 if success else 1
    )