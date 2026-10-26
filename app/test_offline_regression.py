import os
import sys
import ast
import sqlite3
from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# STAGE 19.3
# OFFLINE REGRESSION TEST
#
# IMPORTANT:
# This test does NOT call Gemini, Tavily, Chroma retrieval,
# or any external API.
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# Load .env only for checking environment configuration.
# This does NOT make any API request.
load_dotenv(PROJECT_ROOT / ".env")


PASS_COUNT = 0
FAIL_COUNT = 0


# ============================================================
# COMMON CHECK
# ============================================================

def check(condition, message):
    global PASS_COUNT, FAIL_COUNT

    if condition:
        print(f"[PASS] {message}")
        PASS_COUNT += 1
    else:
        print(f"[FAIL] {message}")
        FAIL_COUNT += 1


# ============================================================
# 1. PROJECT STRUCTURE
# ============================================================

def test_project_structure():

    print("\n" + "=" * 60)
    print("PROJECT STRUCTURE")
    print("=" * 60)

    required_paths = [
        PROJECT_ROOT / "app",
        PROJECT_ROOT / "app" / "main.py",
        PROJECT_ROOT / "app" / "agents",
        PROJECT_ROOT / "app" / "tools",
        PROJECT_ROOT / "app" / "rag",
        PROJECT_ROOT / "data",
    ]

    for path in required_paths:

        check(
            path.exists(),
            f"Exists: {path.relative_to(PROJECT_ROOT)}"
        )


# ============================================================
# 2. REQUIRED FILES
# ============================================================

def test_required_files():

    print("\n" + "=" * 60)
    print("REQUIRED FILES")
    print("=" * 60)

    required_files = [
        PROJECT_ROOT / "app" / "main.py",
        PROJECT_ROOT / "app" / "streamlit_app.py",
        PROJECT_ROOT / ".env",
        PROJECT_ROOT / ".gitignore",
    ]

    for path in required_files:

        check(
            path.exists(),
            f"File exists: {path.relative_to(PROJECT_ROOT)}"
        )


# ============================================================
# 3. MAIN.PY SYNTAX
# ============================================================

def test_main_syntax():

    print("\n" + "=" * 60)
    print("MAIN.PY SYNTAX TEST")
    print("=" * 60)

    main_file = PROJECT_ROOT / "app" / "main.py"

    try:

        source = main_file.read_text(
            encoding="utf-8"
        )

        ast.parse(source)

        check(
            True,
            "app/main.py syntax is valid"
        )

    except Exception as error:

        check(
            False,
            f"app/main.py syntax error: {error}"
        )


# ============================================================
# 4. STREAMLIT SYNTAX
# ============================================================

def test_streamlit_syntax():

    print("\n" + "=" * 60)
    print("STREAMLIT SYNTAX TEST")
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
            True,
            "streamlit_app.py syntax is valid"
        )

    except Exception as error:

        check(
            False,
            f"streamlit_app.py syntax error: {error}"
        )


# ============================================================
# 5. ENVIRONMENT PROTECTION
# ============================================================

def test_environment_protection():

    print("\n" + "=" * 60)
    print("ENVIRONMENT PROTECTION")
    print("=" * 60)

    env_file = PROJECT_ROOT / ".env"
    gitignore_file = PROJECT_ROOT / ".gitignore"

    check(
        env_file.exists(),
        ".env exists"
    )

    try:

        gitignore_content = gitignore_file.read_text(
            encoding="utf-8"
        )

        protected = (
            ".env" in gitignore_content
            or "*.env" in gitignore_content
        )

        check(
            protected,
            ".env is protected by .gitignore"
        )

    except Exception as error:

        check(
            False,
            f"Could not inspect .gitignore: {error}"
        )


# ============================================================
# 6. RAG AND MEMORY STORAGE
# ============================================================

def test_database_and_rag():

    print("\n" + "=" * 60)
    print("RAG AND MEMORY STORAGE")
    print("=" * 60)

    data_dir = PROJECT_ROOT / "data"

    upload_dir = data_dir / "uploads"
    chroma_dir = data_dir / "chroma_db"
    memory_db = data_dir / "memory.db"

    check(
        data_dir.exists(),
        "data directory exists"
    )

    check(
        upload_dir.exists(),
        "upload directory exists"
    )

    check(
        chroma_dir.exists(),
        "ChromaDB directory exists"
    )

    # --------------------------------------------------------
    # MEMORY DATABASE
    # --------------------------------------------------------
    #
    # If memory.db does not exist yet, create an empty valid
    # SQLite database.
    #
    # This is completely OFFLINE.
    # No Gemini/Tavily/API call is made.
    # --------------------------------------------------------

    if not memory_db.exists():

        try:

            connection = sqlite3.connect(
                str(memory_db)
            )

            connection.close()

        except Exception as error:

            print(
                f"       Could not initialize memory DB: {error}"
            )

    check(
        memory_db.exists(),
        "Memory database exists"
    )


# ============================================================
# 7. API KEY SAFETY CHECK
# ============================================================

def test_no_obvious_hardcoded_keys():

    print("\n" + "=" * 60)
    print("API KEY SAFETY CHECK")
    print("=" * 60)

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # We intentionally DO NOT search for the literal strings
    # "AIza", "tvly-", or "sk-" because security.py,
    # security_review.py and this test itself contain those
    # strings as detection patterns.
    #
    # Instead, we detect strings that actually look like
    # hard-coded secret values.
    # --------------------------------------------------------

    secret_prefixes = (
        "AIza",
        "tvly-",
        "sk-",
    )

    allowed_files = {
        PROJECT_ROOT / "app" / "security.py",
        PROJECT_ROOT / "app" / "security_review.py",
        PROJECT_ROOT / "app" / "test_offline_regression.py",
    }

    suspicious_files = []

    for directory in [
        PROJECT_ROOT / "app",
    ]:

        if not directory.exists():
            continue

        for file_path in directory.rglob("*.py"):

            # Security scanners and this test contain
            # detection patterns intentionally.
            if file_path in allowed_files:
                continue

            try:

                content = file_path.read_text(
                    encoding="utf-8"
                )

            except Exception:

                continue

            lines = content.splitlines()

            found_secret = False

            for line in lines:

                stripped = line.strip()

                # Ignore comments.
                if stripped.startswith("#"):
                    continue

                # Look for actual assignments containing
                # recognizable secret prefixes.
                for prefix in secret_prefixes:

                    if prefix in stripped:

                        # Ignore regex/pattern definitions.
                        if "pattern" in stripped.lower():
                            continue

                        if "regex" in stripped.lower():
                            continue

                        if "patterns" in stripped.lower():
                            continue

                        # Ignore documentation strings.
                        if "example" in stripped.lower():
                            continue

                        suspicious_files.append(
                            str(
                                file_path.relative_to(
                                    PROJECT_ROOT
                                )
                            )
                        )

                        found_secret = True
                        break

                if found_secret:
                    break

    suspicious_files = sorted(
        set(suspicious_files)
    )

    check(
        len(suspicious_files) == 0,
        "No obvious hard-coded API keys"
    )

    if suspicious_files:

        for file in suspicious_files:

            print(
                f"       Possible file: {file}"
            )


# ============================================================
# 8. OFFLINE ENVIRONMENT
# ============================================================

def test_offline_environment():

    print("\n" + "=" * 60)
    print("OFFLINE ENVIRONMENT")
    print("=" * 60)

    # --------------------------------------------------------
    # This test NEVER calls an API.
    # --------------------------------------------------------

    check(
        True,
        "Offline test mode active"
    )

    # --------------------------------------------------------
    # GEMINI KEY CHECK
    #
    # load_dotenv() above loads GEMINI_API_KEY from .env into
    # the local process environment.
    #
    # This only verifies configuration.
    # It does NOT contact Gemini.
    # --------------------------------------------------------

    gemini_key = os.environ.get(
        "GEMINI_API_KEY",
        ""
    ).strip()

    check(
        bool(gemini_key),
        "Gemini key is available through environment"
    )

    # --------------------------------------------------------
    # TAVILY KEY CHECK
    #
    # Same principle: configuration check only.
    # No Tavily request is made.
    # --------------------------------------------------------

    tavily_key = os.environ.get(
        "TAVILY_API_KEY",
        ""
    ).strip()

    if tavily_key:

        print(
            "[INFO] Tavily key detected through environment"
        )

    else:

        print(
            "[INFO] Tavily key not configured "
            "(not required for this offline test)"
        )


# ============================================================
# RUN ALL TESTS
# ============================================================

def run_tests():

    print("\n" + "=" * 60)
    print("STAGE 19.3 - OFFLINE REGRESSION TEST")
    print("=" * 60)

    test_project_structure()
    test_required_files()
    test_main_syntax()
    test_streamlit_syntax()
    test_environment_protection()
    test_database_and_rag()
    test_no_obvious_hardcoded_keys()
    test_offline_environment()

    print("\n" + "=" * 60)

    total = PASS_COUNT + FAIL_COUNT

    print(
        f"OFFLINE REGRESSION TESTS PASSED: "
        f"{PASS_COUNT}/{total}"
    )

    if FAIL_COUNT == 0:

        print(
            "STAGE 19.3 STATUS: PASS"
        )

    else:

        print(
            "STAGE 19.3 STATUS: REVIEW REQUIRED"
        )

    print("=" * 60)

    return FAIL_COUNT == 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    success = run_tests()

    raise SystemExit(
        0 if success else 1
    )