import ast
import os
import sys
from pathlib import Path


# ============================================================
# STAGE 19.8
# FINAL OFFLINE RELEASE AUDIT
#
# IMPORTANT:
# - No Gemini API
# - No Tavily API
# - No internet request
# - No API quota consumption
# - This test only reads project files
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
# 1. PROJECT STRUCTURE
# ============================================================

def test_project_structure():

    print("\n" + "=" * 65)
    print("1. PROJECT STRUCTURE")
    print("=" * 65)

    required = [
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

    for path in required:

        check(
            f"Exists: {path.relative_to(PROJECT_ROOT)}",
            path.exists()
        )


# ============================================================
# 2. IMPORTANT FILES
# ============================================================

def test_important_files():

    print("\n" + "=" * 65)
    print("2. IMPORTANT FILES")
    print("=" * 65)

    required_files = [
        PROJECT_ROOT / ".env",
        PROJECT_ROOT / ".gitignore",
        PROJECT_ROOT / "app" / "main.py",
        PROJECT_ROOT / "app" / "streamlit_app.py",
    ]

    for path in required_files:

        check(
            f"File available: {path.relative_to(PROJECT_ROOT)}",
            path.is_file()
        )


# ============================================================
# 3. PYTHON SYNTAX AUDIT
# ============================================================

def test_python_syntax():

    print("\n" + "=" * 65)
    print("3. PYTHON SYNTAX AUDIT")
    print("=" * 65)

    scan_dirs = [
        PROJECT_ROOT / "app",
        PROJECT_ROOT / "tests",
    ]

    python_files = []

    for directory in scan_dirs:

        if not directory.is_dir():
            continue

        for file_path in directory.rglob("*.py"):

            # Ignore virtual environment if accidentally scanned.
            if "venv" in file_path.parts:
                continue

            python_files.append(file_path)

    python_files = sorted(
        set(python_files)
    )

    check(
        "Python files discovered",
        len(python_files) > 0
    )

    for file_path in python_files:

        try:

            source = file_path.read_text(
                encoding="utf-8"
            )

            ast.parse(source)

            check(
                f"Valid syntax: "
                f"{file_path.relative_to(PROJECT_ROOT)}",
                True
            )

        except Exception as error:

            check(
                f"Valid syntax: "
                f"{file_path.relative_to(PROJECT_ROOT)}",
                False
            )

            print(
                f"       Error: {error}"
            )


# ============================================================
# 4. ENVIRONMENT SECURITY
# ============================================================

def test_environment_security():

    print("\n" + "=" * 65)
    print("4. ENVIRONMENT SECURITY")
    print("=" * 65)

    env_file = PROJECT_ROOT / ".env"
    gitignore_file = PROJECT_ROOT / ".gitignore"

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
# 5. MEMORY DATABASE
# ============================================================

def test_memory_database():

    print("\n" + "=" * 65)
    print("5. MEMORY DATABASE")
    print("=" * 65)

    memory_paths = [
        PROJECT_ROOT / "data" / "memory.db",
        PROJECT_ROOT / "memory.db",
    ]

    existing = [
        path
        for path in memory_paths
        if path.is_file()
    ]

    check(
        "Memory database exists",
        len(existing) > 0
    )

    if not existing:
        return

    for database in existing:

        try:

            size = database.stat().st_size

            check(
                f"Memory database readable: "
                f"{database.relative_to(PROJECT_ROOT)}",
                size >= 0
            )

        except Exception as error:

            check(
                f"Memory database readable: "
                f"{database.relative_to(PROJECT_ROOT)}",
                False
            )

            print(
                f"       Error: {error}"
            )


# ============================================================
# 6. RAG STORAGE
# ============================================================

def test_rag_storage():

    print("\n" + "=" * 65)
    print("6. RAG STORAGE")
    print("=" * 65)

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
# 7. REGRESSION TEST DIRECTORY
# ============================================================

def test_regression_tests():

    print("\n" + "=" * 65)
    print("7. REGRESSION TESTS")
    print("=" * 65)

    tests_dir = PROJECT_ROOT / "tests"

    check(
        "Regression test directory exists",
        tests_dir.is_dir()
    )

    if not tests_dir.is_dir():
        return

    test_files = sorted(
        tests_dir.glob("test_*.py")
    )

    check(
        "Regression test files available",
        len(test_files) > 0
    )

    print(
        f"       Found {len(test_files)} test file(s)"
    )

    for file_path in test_files:

        check(
            f"Test available: {file_path.name}",
            file_path.is_file()
        )


# ============================================================
# 8. API KEY SAFETY
# ============================================================

def test_api_key_safety():

    print("\n" + "=" * 65)
    print("8. API KEY SAFETY")
    print("=" * 65)

    # Detection prefixes only.
    # These are NOT actual API keys.

    patterns = (
        "AIzaSy",
        "tvly-",
        "sk-",
    )

    excluded = {
        PROJECT_ROOT / "app" / "security.py",
        PROJECT_ROOT / "app" / "security_review.py",
    }

    suspicious = []

    app_dir = PROJECT_ROOT / "app"

    if app_dir.is_dir():

        for file_path in app_dir.rglob("*.py"):

            if file_path in excluded:
                continue

            try:

                content = file_path.read_text(
                    encoding="utf-8"
                )

            except Exception:

                continue

            for pattern in patterns:

                position = content.find(pattern)

                while position != -1:

                    start = position + len(pattern)

                    token = ""

                    for char in content[start:]:

                        if char.isalnum() or char in "_-":
                            token += char
                        else:
                            break

                    if len(token) >= 12:

                        suspicious.append(
                            file_path.relative_to(
                                PROJECT_ROOT
                            )
                        )

                        break

                    position = content.find(
                        pattern,
                        start
                    )

                if file_path.relative_to(
                    PROJECT_ROOT
                ) in suspicious:

                    break

    suspicious = sorted(
        set(
            str(path)
            for path in suspicious
        )
    )

    check(
        "No obvious hard-coded API keys",
        len(suspicious) == 0
    )

    if suspicious:

        print("       Possible files:")

        for file in suspicious:

            print(
                f"       - {file}"
            )


# ============================================================
# 9. OFFLINE TEST SAFETY
# ============================================================

def test_offline_safety():

    print("\n" + "=" * 65)
    print("9. OFFLINE TEST SAFETY")
    print("=" * 65)

    test_files = sorted(
        (PROJECT_ROOT / "tests").glob("test_*.py")
    )

    forbidden_calls = (
        "requests.get(",
        "requests.post(",
        "requests.request(",
        "httpx.get(",
        "httpx.post(",
        "urllib.request.urlopen(",
        "TavilyClient(",
        "ChatGoogleGenerativeAI(",
    )

    # We only inspect the test files.
    # This test file itself contains the forbidden strings
    # as detection patterns, so it is excluded.

    current_file = (
        PROJECT_ROOT
        / "tests"
        / "test_stage_19_8.py"
    )

    found = []

    for file_path in test_files:

        if file_path == current_file:
            continue

        try:

            content = file_path.read_text(
                encoding="utf-8"
            )

        except Exception:

            continue

        for call in forbidden_calls:

            if call in content:

                found.append(
                    (
                        file_path.name,
                        call
                    )
                )

    check(
        "No external API calls in regression tests",
        len(found) == 0
    )

    if found:

        print("       Found:")

        for filename, call in found:

            print(
                f"       - {filename}: {call}"
            )


# ============================================================
# 10. STREAMLIT FILE CHECK
# ============================================================

def test_streamlit_file():

    print("\n" + "=" * 65)
    print("10. STREAMLIT APPLICATION")
    print("=" * 65)

    streamlit_file = (
        PROJECT_ROOT
        / "app"
        / "streamlit_app.py"
    )

    check(
        "Streamlit application exists",
        streamlit_file.is_file()
    )

    if not streamlit_file.is_file():
        return

    try:

        source = streamlit_file.read_text(
            encoding="utf-8"
        )

        check(
            "Streamlit application is readable",
            len(source) > 0
        )

    except Exception as error:

        check(
            "Streamlit application is readable",
            False
        )

        print(
            f"       Error: {error}"
        )


# ============================================================
# 11. FINAL RELEASE FILE CHECK
# ============================================================

def test_release_files():

    print("\n" + "=" * 65)
    print("11. FINAL RELEASE FILE CHECK")
    print("=" * 65)

    important_files = [
        PROJECT_ROOT / "app" / "main.py",
        PROJECT_ROOT / "app" / "streamlit_app.py",
        PROJECT_ROOT / "app" / "security.py",
        PROJECT_ROOT / "app" / "security_review.py",
        PROJECT_ROOT / "tests" / "test_offline_hardening.py",
        PROJECT_ROOT / "tests" / "test_final_offline_validation.py",
    ]

    for file_path in important_files:

        check(
            f"Release file available: "
            f"{file_path.relative_to(PROJECT_ROOT)}",
            file_path.is_file()
        )


# ============================================================
# RUN ALL TESTS
# ============================================================

def run_tests():

    global PASS_COUNT, FAIL_COUNT

    print("\n" + "=" * 65)
    print("STAGE 19.8 - FINAL OFFLINE RELEASE AUDIT")
    print("=" * 65)

    test_project_structure()

    test_important_files()

    test_python_syntax()

    test_environment_security()

    test_memory_database()

    test_rag_storage()

    test_regression_tests()

    test_api_key_safety()

    test_offline_safety()

    test_streamlit_file()

    test_release_files()

    print("\n" + "=" * 65)

    total = PASS_COUNT + FAIL_COUNT

    print(
        f"FINAL OFFLINE RELEASE AUDIT: "
        f"{PASS_COUNT}/{total}"
    )

    if FAIL_COUNT == 0:

        print(
            "STAGE 19.8 STATUS: PASS"
        )

        print("=" * 65)

        return True

    print(
        "STAGE 19.8 STATUS: REVIEW REQUIRED"
    )

    print("=" * 65)

    return False


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    success = run_tests()

    raise SystemExit(
        0 if success else 1
    )