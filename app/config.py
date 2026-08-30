import os
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

# Monday.com API configuration
MONDAY_API_TOKEN = os.getenv("MONDAY_API_TOKEN")

DEALS_BOARD_ID = int(os.getenv("DEALS_BOARD_ID", "5030964525"))
WORK_ORDERS_BOARD_ID = int(os.getenv("WORK_ORDERS_BOARD_ID", "5030964579"))

# Monday.com API endpoint
MONDAY_API_URL = "https://api.monday.com/v2"


def validate_config():
    """Validate that required configuration is available."""

    if not MONDAY_API_TOKEN:
        raise ValueError(
            "MONDAY_API_TOKEN is missing. "
            "Please check your .env file."
        )

    if not DEALS_BOARD_ID:
        raise ValueError("DEALS_BOARD_ID is missing.")

    if not WORK_ORDERS_BOARD_ID:
        raise ValueError("WORK_ORDERS_BOARD_ID is missing.")


if __name__ == "__main__":
    validate_config()

    print("Configuration loaded successfully.")
    print(f"Deals Board ID: {DEALS_BOARD_ID}")
    print(f"Work Orders Board ID: {WORK_ORDERS_BOARD_ID}")
    print("Monday API token: [LOADED]")