import os
import re

from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# REQUIRED SECRETS
# ============================================================

REQUIRED_SECRETS = (
    "GEMINI_API_KEY",
    "TAVILY_API_KEY",
)


# ============================================================
# SECRET PATTERNS
# ============================================================

SECRET_PATTERNS = (
    r"AIza[0-9A-Za-z_\-]{20,}",       # Google/Gemini style key
    r"tvly-[0-9A-Za-z_\-]{10,}",      # Tavily style key
    r"sk-[0-9A-Za-z_\-]{20,}",        # Generic API-key pattern
)


# ============================================================
# ENVIRONMENT SECRET CHECK
# ============================================================

def get_secret(name: str) -> str | None:
    """
    Safely retrieve a secret from environment variables.

    Returns None if the secret is missing or empty.
    """

    if not isinstance(name, str):
        return None

    name = name.strip()

    if not name:
        return None

    value = os.getenv(name)

    if value is None:
        return None

    value = value.strip()

    if not value:
        return None

    return value


# ============================================================
# REQUIRED SECRET VALIDATION
# ============================================================

def validate_required_secrets() -> tuple[bool, list[str]]:
    """
    Check whether required API keys exist.

    Actual secret values are never returned.
    """

    missing = []

    for secret_name in REQUIRED_SECRETS:

        value = get_secret(secret_name)

        if not value:
            missing.append(secret_name)

    return (
        len(missing) == 0,
        missing,
    )


# ============================================================
# SECRET DETECTION
# ============================================================

def contains_secret(value: str) -> bool:
    """
    Detect common API-key patterns inside text.
    """

    if not isinstance(value, str):
        return False

    for pattern in SECRET_PATTERNS:

        if re.search(pattern, value):
            return True

    return False


# ============================================================
# SECRET REDACTION
# ============================================================

def redact_secrets(value: str) -> str:
    """
    Replace detected API keys with [REDACTED].

    Useful for logs and error messages.
    """

    if not isinstance(value, str):
        return value

    redacted = value

    for pattern in SECRET_PATTERNS:

        redacted = re.sub(
            pattern,
            "[REDACTED]",
            redacted,
        )

    return redacted


# ============================================================
# SAFE ERROR MESSAGE
# ============================================================

def safe_error_message(error: Exception) -> str:
    """
    Convert an exception into a message that does not expose
    detected API keys.
    """

    message = str(error)

    return redact_secrets(message)


# ============================================================
# SECRET STATUS
# ============================================================

def get_secret_status() -> dict[str, bool]:
    """
    Return only whether each required secret exists.

    Secret values are never exposed.
    """

    return {
        secret_name: bool(
            get_secret(secret_name)
        )
        for secret_name in REQUIRED_SECRETS
    }


# ============================================================
# SECURITY STARTUP CHECK
# ============================================================

SECRETS_VALID, MISSING_SECRETS = (
    validate_required_secrets()
)