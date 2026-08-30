import os
from dotenv import load_dotenv

# Load local .env file
load_dotenv()

# ---------------------------------------------------------
# Streamlit Secrets support
# ---------------------------------------------------------

try:
    import streamlit as st
except ImportError:
    st = None


def get_config(name, default=None):
    """
    Get configuration value.

    Priority:
    1. Environment variable
    2. Streamlit Secrets
    3. Default value
    """

    # Local environment / .env
    value = os.getenv(name)

    if value:
        return value.strip()

    # Streamlit Cloud Secrets
    if st is not None:
        try:
            value = st.secrets.get(name)

            if value:
                return str(value).strip()

        except Exception:
            pass

    return default


# ---------------------------------------------------------
# Monday.com API configuration
# ---------------------------------------------------------

MONDAY_API_TOKEN = get_config("MONDAY_API_TOKEN")

DEALS_BOARD_ID = int(
    get_config("DEALS_BOARD_ID", "5030964525")
)

WORK_ORDERS_BOARD_ID = int(
    get_config("WORK_ORDERS_BOARD_ID", "5030964579")
)

MONDAY_API_URL = "https://api.monday.com/v2"


# ---------------------------------------------------------
# Gemini API configuration
# ---------------------------------------------------------

GEMINI_API_KEY = get_config("GEMINI_API_KEY")


# ---------------------------------------------------------
# Configuration validation
# ---------------------------------------------------------

def validate_config():
    """Validate that required configuration is available."""

    if not MONDAY_API_TOKEN:
        raise ValueError(
            "MONDAY_API_TOKEN is missing. "
            "Configure it in .env locally or Streamlit Secrets."
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

    print("Configuration loaded successfully.")
    print(f"Deals Board ID: {DEALS_BOARD_ID}")
    print(f"Work Orders Board ID: {WORK_ORDERS_BOARD_ID}")

    print(
        f"Monday API token loaded: "
        f"{bool(MONDAY_API_TOKEN)}"
    )

    print(
        f"Gemini API key loaded: "
        f"{bool(GEMINI_API_KEY)}"
    )

    print("=" * 60)