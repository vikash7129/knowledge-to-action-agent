import os
import sys
import ast
from pathlib import Path


# ============================================================
# STAGE 19.7
# FINAL OFFLINE VALIDATION
#
# IMPORTANT:
# This validation does NOT call Gemini, Tavily,
# Chroma retrieval, or any external API.
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

    global PASS_COUNT
    global FAIL_COUNT

    if condition:

        print(f"[PASS] {label}")
        PASS_COUNT += 1

    else:

        print(f"[FAIL] {label}")
        FAIL_COUNT += 1


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
# 2. IMPORTANT FILES
# ============================================================

def test_important_files():

    print("\n" + "=" * 60)
    print("2. IMPORTANT FILES")
    print("=" * 60)

    required_files = [

        PROJECT_ROOT / "app" / "main.py",

        PROJECT_ROOT / "app" / "streamlit_app.py",

        PROJECT_ROOT / ".env",

        PROJECT_ROOT / ".gitignore",

    ]

    for path in required_files:

        check(
            f"File available: "
            f"{path.relative_to(PROJECT_ROOT)}",
            path.is_file()
        )


# ============================================================
# 3. PYTHON SYNTAX
# ============================================================

def test_python_syntax():

    print("\n" + "=" * 60)
    print("3. PYTHON SYNTAX VALIDATION")
    print("=" * 60)

    scan_directories = [

        PROJECT_ROOT / "app",

        PROJECT_ROOT / "tests",

    ]

    for directory in scan_directories:

        if not directory.is_dir():
            continue

        for file_path in directory.rglob("*.py"):

            try:

                source = file_path.read_text(
                    encoding="utf-8"
                )

                ast.parse(source)

                relative = file_path.relative_to(
                    PROJECT_ROOT
                )

                check(
                    f"Valid syntax: {relative}",
                    True
                )

            except Exception as error:

                relative = file_path.relative_to(
                    PROJECT_ROOT
                )

                check(
                    f"Valid syntax: {relative}",
                    False
                )

                print(
                    f"       Error: {error}"
                )


# ============================================================
# 4. ENVIRONMENT SECURITY
# ============================================================

def test_environment_security():

    print("\n" + "=" * 60)
    print("4. ENVIRONMENT SECURITY")
    print("=" * 60)

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

    if gitignore_file.is_file():

        try:

            content = gitignore_file.read_text(
                encoding="utf-8"
            )

            protected = any(
                line.strip() in {
                    ".env",
                    "*.env",
                }
                for line in content.splitlines()
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
# 5. RAG STORAGE
# ============================================================

def test_rag_storage():

    print("\n" + "=" * 60)
    print("5. RAG STORAGE")
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
# 6. MEMORY DATABASE
# ============================================================

def test_memory_database():

    print("\n" + "=" * 60)
    print("6. MEMORY DATABASE")
    print("=" * 60)

    memory_db = (
        PROJECT_ROOT
        / "data"
        / "memory.db"
    )

    check(
        "Memory database exists",
        memory_db.is_file()
    )

    if memory_db.is_file():

        try:

            with open(
                memory_db,
                "rb"
            ) as file:

                file.read(1)

            check(
                "Memory database is readable",
                True
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
# 7. REGRESSION TESTS
# ============================================================

def test_regression_files():

    print("\n" + "=" * 60)
    print("7. REGRESSION TESTS")
    print("=" * 60)

    tests_dir = PROJECT_ROOT / "tests"

    if not tests_dir.is_dir():

        check(
            "Tests directory available",
            False
        )

        return

    test_files = sorted(
        tests_dir.glob("test_*.py")
    )

    # Exclude the current validation file.
    available_tests = [
        file
        for file in test_files
        if file.name
        != "test_final_offline_validation.py"
    ]

    # We do NOT require specific filenames.
    # Different project stages may use different
    # regression-test names.

    check(
        "Regression test directory available",
        True
    )

    check(
        "Regression test files available",
        len(available_tests) > 0
    )

    if available_tests:

        print(
            f"       Found {len(available_tests)} "
            f"regression test file(s):"
        )

        for file in available_tests:

            print(
                f"       - {file.name}"
            )


# ============================================================
# 8. API KEY SAFETY
# ============================================================

def test_api_key_safety():

    print("\n" + "=" * 60)
    print("8. API KEY SAFETY")
    print("=" * 60)

    # Build detection prefixes dynamically so that this
    # validation file does not contain long secret-like
    # strings that can trigger its own scanner.

    prefix_google = "AIza" + "Sy"

    prefix_tavily = "tvly" + "-"

    prefix_generic = "sk" + "-"

    key_prefixes = (
        prefix_google,
        prefix_tavily,
        prefix_generic,
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

    if app_dir.is_dir():

        for file_path in app_dir.rglob("*.py"):

            if file_path in excluded_files:
                continue

            try:

                content = file_path.read_text(
                    encoding="utf-8"
                )

            except Exception:

                continue

            for prefix in key_prefixes:

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
# 9. OFFLINE VALIDATION SAFETY
# ============================================================

def test_offline_safety():

    print("\n" + "=" * 60)
    print("9. OFFLINE VALIDATION SAFETY")
    print("=" * 60)

    # This test only checks the source code of the
    # validation script itself.
    #
    # API-call signatures are constructed dynamically
    # to avoid self-detection.

    test_file = Path(__file__)

    try:

        content = test_file.read_text(
            encoding="utf-8"
        )

        external_call_fragments = [

            ("requests", "get"),
            ("requests", "post"),
            ("requests", "request"),

            ("httpx", "get"),
            ("httpx", "post"),

            ("urllib.request", "urlopen"),

            ("Tavily" + "Client", ""),

            ("ChatGoogle" + "GenerativeAI", ""),

        ]

        found_calls = []

        for module_name, function_name in (
            external_call_fragments
        ):

            # Reconstruct the search target.
            if function_name:

                search_text = (
                    module_name
                    + "."
                    + function_name
                    + "("
                )

            else:

                search_text = (
                    module_name
                    + "("
                )

            # Remove the current scanner section
            # before checking, so the test does not
            # detect its own search strings.

            scanner_marker = (
                "external_call_fragments"
            )

            marker_position = content.find(
                scanner_marker
            )

            searchable_content = content

            if marker_position != -1:

                searchable_content = (
                    content[:marker_position]
                )

            if search_text in searchable_content:

                found_calls.append(
                    search_text
                )

        check(
            "No external API calls in validation test",
            len(found_calls) == 0
        )

        if found_calls:

            print(
                "       Found:"
            )

            for call in found_calls:

                print(
                    f"       - {call}"
                )

    except Exception as error:

        check(
            "Validation test readable",
            False
        )

        print(
            f"       Error: {error}"
        )


# ============================================================
# 10. STREAMLIT VALIDATION
# ============================================================

def test_streamlit():

    print("\n" + "=" * 60)
    print("10. STREAMLIT VALIDATION")
    print("=" * 60)

    streamlit_file = (
        PROJECT_ROOT
        / "app"
        / "streamlit_app.py"
    )

    if not streamlit_file.is_file():

        check(
            "Streamlit application available",
            False
        )

        return

    try:

        source = streamlit_file.read_text(
            encoding="utf-8"
        )

        ast.parse(source)

        check(
            "Streamlit syntax valid",
            True
        )

        check(
            "Agent Goal interface available",
            "Agent Goal" in source
        )

        check(
            "Run Agent button available",
            "Run Agent" in source
        )

        check(
            "RAG visualization available",
            "RAG Intelligence" in source
        )

        check(
            "Executor transparency available",
            "Executor Transparency" in source
        )

    except Exception as error:

        check(
            "Streamlit validation",
            False
        )

        print(
            f"       Error: {error}"
        )


# ============================================================
# 11. CORE MODULE DIRECTORIES
# ============================================================

def test_core_directories():

    print("\n" + "=" * 60)
    print("11. CORE MODULE DIRECTORIES")
    print("=" * 60)

    directories = [

        PROJECT_ROOT / "app" / "agents",

        PROJECT_ROOT / "app" / "tools",

        PROJECT_ROOT / "app" / "rag",

    ]

    for directory in directories:

        check(
            f"Directory available: "
            f"{directory.relative_to(PROJECT_ROOT)}",
            directory.is_dir()
        )


# ============================================================
# FINAL RUNNER
# ============================================================

def run_tests():

    print("\n" + "=" * 60)
    print(
        "STAGE 19.7 - FINAL OFFLINE VALIDATION"
    )
    print("=" * 60)

    test_project_structure()

    test_important_files()

    test_python_syntax()

    test_environment_security()

    test_rag_storage()

    test_memory_database()

    test_regression_files()

    test_api_key_safety()

    test_offline_safety()

    test_streamlit()

    test_core_directories()

    print("\n" + "=" * 60)

    total = PASS_COUNT + FAIL_COUNT

    print(
        f"FINAL OFFLINE VALIDATION: "
        f"{PASS_COUNT}/{total}"
    )

    if FAIL_COUNT == 0:

        print(
            "STAGE 19.7 STATUS: PASS"
        )

        print("=" * 60)

        return True

    print(
        "STAGE 19.7 STATUS: REVIEW REQUIRED"
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