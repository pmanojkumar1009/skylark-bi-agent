import os
from dotenv import load_dotenv

# Load local .env when running locally
load_dotenv()

# ---------------------------------------------------------
# Streamlit Cloud Secrets
# ---------------------------------------------------------

try:
    import streamlit as st
except ImportError:
    st = None


def get_secret(name, default=None):
    """
    Read configuration from:
    1. Streamlit secrets (Cloud)
    2. Environment variables / .env (Local)
    """

    # Streamlit Cloud
    if st is not None:
        try:
            value = st.secrets.get(name)

            if value is not None:
                return str(value)

        except Exception:
            pass

    # Local .env / environment variables
    return os.getenv(name, default)


# ---------------------------------------------------------
# Monday.com Configuration
# ---------------------------------------------------------

MONDAY_API_TOKEN = get_secret("MONDAY_API_TOKEN")

DEALS_BOARD_ID = int(
    get_secret(
        "DEALS_BOARD_ID",
        "5030964525"
    )
)

WORK_ORDERS_BOARD_ID = int(
    get_secret(
        "WORK_ORDERS_BOARD_ID",
        "5030964579"
    )
)

MONDAY_API_URL = "https://api.monday.com/v2"


# ---------------------------------------------------------
# Gemini Configuration
# ---------------------------------------------------------

GEMINI_API_KEY = get_secret("GEMINI_API_KEY")


# ---------------------------------------------------------
# Validation
# ---------------------------------------------------------

def validate_config():
    """Validate required configuration."""

    if not MONDAY_API_TOKEN:
        raise ValueError(
            "MONDAY_API_TOKEN is missing. "
            "Configure it in .env or Streamlit Secrets."
        )

    if not DEALS_BOARD_ID:
        raise ValueError(
            "DEALS_BOARD_ID is missing."
        )

    if not WORK_ORDERS_BOARD_ID:
        raise ValueError(
            "WORK_ORDERS_BOARD_ID is missing."
        )


# ---------------------------------------------------------
# Local configuration test
# ---------------------------------------------------------

if __name__ == "__main__":

    validate_config()

    print("=" * 60)
    print("SKYLARK BI CONFIGURATION")
    print("=" * 60)

    print(
        f"Deals Board ID: {DEALS_BOARD_ID}"
    )

    print(
        f"Work Orders Board ID: {WORK_ORDERS_BOARD_ID}"
    )

    print(
        "Monday API token: "
        + ("[LOADED]" if MONDAY_API_TOKEN else "[MISSING]")
    )

    print(
        "Gemini API key: "
        + ("[LOADED]" if GEMINI_API_KEY else "[MISSING]")
    )

    print("=" * 60)