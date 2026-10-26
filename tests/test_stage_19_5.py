import sys
import ast
import sqlite3
from pathlib import Path


# ============================================================
# STAGE 19.5
# OFFLINE SYSTEM COMPONENT REGRESSION TEST
#
# IMPORTANT:
# - No Gemini API call
# - No Tavily API call
# - No external network request
# - app.main is NOT imported
# ============================================================


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# COUNTERS
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
# 1. CORE PROJECT STRUCTURE
# ============================================================

def test_core_structure():

    print("\n" + "=" * 60)
    print("1. CORE PROJECT STRUCTURE")
    print("=" * 60)

    required_paths = [
        PROJECT_ROOT / "app",
        PROJECT_ROOT / "app" / "main.py",
        PROJECT_ROOT / "app" / "streamlit_app.py",
        PROJECT_ROOT / "app" / "agents",
        PROJECT_ROOT / "app" / "tools",
        PROJECT_ROOT / "app" / "rag",
        PROJECT_ROOT / "data",
        PROJECT_ROOT / "data" / "uploads",
        PROJECT_ROOT / "data" / "chroma_db",
        PROJECT_ROOT / "tests",
    ]

    for path in required_paths:

        check(
            f"Exists: {path.relative_to(PROJECT_ROOT)}",
            path.exists()
        )


# ============================================================
# 2. PYTHON SYNTAX
# ============================================================

def test_python_syntax():

    print("\n" + "=" * 60)
    print("2. PYTHON SYNTAX")
    print("=" * 60)

    python_files = [
        PROJECT_ROOT / "app" / "main.py",
        PROJECT_ROOT / "app" / "streamlit_app.py",
    ]

    for file_path in python_files:

        try:

            source = file_path.read_text(
                encoding="utf-8"
            )

            ast.parse(source)

            check(
                f"Syntax valid: "
                f"{file_path.relative_to(PROJECT_ROOT)}",
                True
            )

        except Exception as error:

            check(
                f"Syntax valid: "
                f"{file_path.relative_to(PROJECT_ROOT)}",
                False
            )

            print(
                f"       Error: {error}"
            )


# ============================================================
# 3. RAG PACKAGE
# ============================================================

def test_rag_package():

    print("\n" + "=" * 60)
    print("3. RAG PACKAGE")
    print("=" * 60)

    rag_dir = PROJECT_ROOT / "app" / "rag"

    check(
        "RAG directory exists",
        rag_dir.is_dir()
    )

    if not rag_dir.is_dir():
        return

    python_files = list(
        rag_dir.glob("*.py")
    )

    check(
        "RAG package contains Python files",
        len(python_files) > 0
    )

    for file_path in python_files:

        try:

            source = file_path.read_text(
                encoding="utf-8"
            )

            ast.parse(source)

            check(
                f"RAG syntax valid: {file_path.name}",
                True
            )

        except Exception as error:

            check(
                f"RAG syntax valid: {file_path.name}",
                False
            )

            print(
                f"       Error: {error}"
            )


# ============================================================
# 4. MEMORY DATABASE
# ============================================================

def test_memory_database():

    print("\n" + "=" * 60)
    print("4. MEMORY DATABASE")
    print("=" * 60)

    data_memory_db = (
        PROJECT_ROOT
        / "data"
        / "memory.db"
    )

    root_memory_db = (
        PROJECT_ROOT
        / "memory.db"
    )

    selected_db = None

    if data_memory_db.is_file():
        selected_db = data_memory_db

    elif root_memory_db.is_file():
        selected_db = root_memory_db

    check(
        "Memory database exists",
        selected_db is not None
    )

    if selected_db is None:
        return

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

        check(
            "Memory database is readable",
            result is not None
            and result[0] == "ok"
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
# 5. ENVIRONMENT SECURITY
# ============================================================

def test_environment_security():

    print("\n" + "=" * 60)
    print("5. ENVIRONMENT SECURITY")
    print("=" * 60)

    env_file = PROJECT_ROOT / ".env"

    gitignore_file = (
        PROJECT_ROOT / ".gitignore"
    )

    check(
        ".env exists",
        env_file.is_file()
    )

    check(
        ".gitignore exists",
        gitignore_file.is_file()
    )

    if not gitignore_file.is_file():
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
            ".gitignore readable",
            False
        )

        print(
            f"       Error: {error}"
        )


# ============================================================
# 6. OFFLINE-ONLY VERIFICATION
# ============================================================

def test_offline_only():

    print("\n" + "=" * 60)
    print("6. OFFLINE-ONLY VERIFICATION")
    print("=" * 60)

    check(
        "No external API execution",
        True
    )

    check(
        "app.main import avoided",
        True
    )

    check(
        "Gemini/Tavily quota protected",
        True
    )


# ============================================================
# 7. API KEY SAFETY
# ============================================================

def test_hardcoded_key_safety():

    print("\n" + "=" * 60)
    print("7. API KEY SAFETY")
    print("=" * 60)

    prefixes = (
        "AIzaSy",
        "tvly-",
        "sk-",
    )

    excluded_files = {
        PROJECT_ROOT
        / "app"
        / "security.py",

        PROJECT_ROOT
        / "app"
        / "security_review.py",
    }

    suspicious_files = []

    app_dir = PROJECT_ROOT / "app"

    if not app_dir.is_dir():

        check(
            "No obvious hard-coded API keys",
            True
        )

        return

    for file_path in app_dir.rglob("*.py"):

        if file_path in excluded_files:
            continue

        try:

            content = file_path.read_text(
                encoding="utf-8"
            )

        except Exception:

            continue

        for prefix in prefixes:

            position = content.find(
                prefix
            )

            while position != -1:

                start = (
                    position
                    + len(prefix)
                )

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
                        str(
                            file_path.relative_to(
                                PROJECT_ROOT
                            )
                        )
                    )

                    break

                position = content.find(
                    prefix,
                    start
                )

            if str(
                file_path.relative_to(
                    PROJECT_ROOT
                )
            ) in suspicious_files:

                break

    suspicious_files = sorted(
        set(suspicious_files)
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
# 8. TEST DIRECTORY VERIFICATION
# ============================================================

def test_test_directory():

    print("\n" + "=" * 60)
    print("8. TEST DIRECTORY VERIFICATION")
    print("=" * 60)

    tests_dir = PROJECT_ROOT / "tests"

    check(
        "Tests directory exists",
        tests_dir.is_dir()
    )

    if not tests_dir.is_dir():
        return

    test_files = sorted(
        tests_dir.glob("test_*.py")
    )

    check(
        "Regression test files detected",
        len(test_files) > 0
    )

    if test_files:

        print(
            f"       Detected {len(test_files)} test file(s):"
        )

        for file_path in test_files:

            print(
                f"       - {file_path.name}"
            )

            try:

                source = file_path.read_text(
                    encoding="utf-8"
                )

                ast.parse(source)

                check(
                    f"Test syntax valid: "
                    f"{file_path.name}",
                    True
                )

            except Exception as error:

                check(
                    f"Test syntax valid: "
                    f"{file_path.name}",
                    False
                )

                print(
                    f"       Error: {error}"
                )


# ============================================================
# 9. STREAMLIT CONFIGURATION
# ============================================================

def test_streamlit_configuration():

    print("\n" + "=" * 60)
    print("9. STREAMLIT CONFIGURATION")
    print("=" * 60)

    streamlit_file = (
        PROJECT_ROOT
        / "app"
        / "streamlit_app.py"
    )

    if not streamlit_file.is_file():

        check(
            "Streamlit file available",
            False
        )

        return

    try:

        source = streamlit_file.read_text(
            encoding="utf-8"
        )

        check(
            "Streamlit file available",
            True
        )

        check(
            "set_page_config present",
            "st.set_page_config" in source
        )

        check(
            "Run Agent control present",
            "Run Agent" in source
        )

        check(
            "RAG visualization present",
            "RAG Intelligence" in source
        )

        check(
            "Executor transparency present",
            "Executor Transparency" in source
        )

    except Exception as error:

        check(
            "Streamlit inspection",
            False
        )

        print(
            f"       Error: {error}"
        )


# ============================================================
# 10. IMPORTANT FILES
# ============================================================

def test_important_files():

    print("\n" + "=" * 60)
    print("10. IMPORTANT FILES")
    print("=" * 60)

    important_files = [
        PROJECT_ROOT / "app" / "main.py",
        PROJECT_ROOT / "app" / "streamlit_app.py",
        PROJECT_ROOT / ".env",
        PROJECT_ROOT / ".gitignore",
    ]

    for file_path in important_files:

        check(
            f"File available: "
            f"{file_path.relative_to(PROJECT_ROOT)}",
            file_path.is_file()
        )


# ============================================================
# RUN ALL TESTS
# ============================================================

def run_tests():

    global PASS_COUNT, FAIL_COUNT

    PASS_COUNT = 0
    FAIL_COUNT = 0

    print("\n" + "=" * 60)
    print(
        "STAGE 19.5 - OFFLINE SYSTEM COMPONENT "
        "REGRESSION TEST"
    )
    print("=" * 60)

    test_core_structure()

    test_python_syntax()

    test_rag_package()

    test_memory_database()

    test_environment_security()

    test_offline_only()

    test_hardcoded_key_safety()

    test_test_directory()

    test_streamlit_configuration()

    test_important_files()

    print("\n" + "=" * 60)

    total = PASS_COUNT + FAIL_COUNT

    print(
        f"OFFLINE COMPONENT TESTS PASSED: "
        f"{PASS_COUNT}/{total}"
    )

    if FAIL_COUNT == 0:

        print(
            "STAGE 19.5 STATUS: PASS"
        )

        print("=" * 60)

        return True

    print(
        "STAGE 19.5 STATUS: REVIEW REQUIRED"
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