import requests

from app.config import (
    MONDAY_API_TOKEN,
    MONDAY_API_URL,
    DEALS_BOARD_ID,
    WORK_ORDERS_BOARD_ID,
)


class MondayClient:
    """Client for reading data from Monday.com."""

    def __init__(self):
        self.url = MONDAY_API_URL

        self.headers = {
            "Authorization": MONDAY_API_TOKEN,
            "Content-Type": "application/json",
        }

        self.timeout = (10, 30)

    def _query(self, query, variables=None):
        """Execute a GraphQL query."""

        payload = {
            "query": query,
            "variables": variables or {},
        }

        try:
            response = requests.post(
                self.url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout,
            )

            response.raise_for_status()

        except requests.exceptions.Timeout as exc:
            raise RuntimeError(
                "Monday.com API request timed out."
            ) from exc

        except requests.exceptions.RequestException as exc:
            raise RuntimeError(
                f"Monday.com API request failed: {exc}"
            ) from exc

        try:
            result = response.json()
        except ValueError as exc:
            raise RuntimeError(
                "Monday.com returned an invalid JSON response."
            ) from exc

        if "errors" in result:
            raise RuntimeError(
                f"Monday.com GraphQL error: {result['errors']}"
            )

        return result.get("data", {})

    # ---------------------------------------------------------
    # Board information
    # ---------------------------------------------------------

    def get_board(self, board_id):
        """Fetch board metadata and column definitions."""

        query = """
        query ($board_id: ID!) {
            boards(ids: [$board_id]) {
                id
                name
                description
                columns {
                    id
                    title
                    type
                }
            }
        }
        """

        data = self._query(
            query,
            {
                "board_id": str(board_id)
            },
        )

        boards = data.get("boards", [])

        if not boards:
            raise ValueError(
                f"Board {board_id} was not found."
            )

        return boards[0]

    # ---------------------------------------------------------
    # Board items
    # ---------------------------------------------------------

    def get_board_items(self, board_id):
        """
        Fetch items from a Monday.com board.

        Uses cursor-based pagination so the application
        can retrieve all available records rather than
        relying on a fixed 500-row limit.
        """

        all_items = []
        cursor = None

        while True:

            query = """
            query (
                $board_id: ID!,
                $cursor: String
            ) {
                boards(ids: [$board_id]) {
                    items_page(
                        limit: 100,
                        cursor: $cursor
                    ) {
                        cursor

                        items {
                            id
                            name

                            group {
                                id
                                title
                            }

                            column_values {
                                id
                                text
                                value
                                type
                            }
                        }
                    }
                }
            }
            """

            variables = {
                "board_id": str(board_id),
                "cursor": cursor,
            }

            data = self._query(
                query,
                variables,
            )

            boards = data.get("boards", [])

            if not boards:
                raise ValueError(
                    f"Board {board_id} was not found."
                )

            page = boards[0]["items_page"]

            items = page.get("items", [])

            all_items.extend(items)

            cursor = page.get("cursor")

            print(
                f"  Retrieved {len(items)} items "
                f"(total: {len(all_items)})"
            )

            if not cursor or not items:
                break

        return all_items

    # ---------------------------------------------------------
    # Convenience methods
    # ---------------------------------------------------------

    def get_deals(self):
        """Fetch all Deals records."""

        return self.get_board_items(
            DEALS_BOARD_ID
        )

    def get_work_orders(self):
        """Fetch all Work Order records."""

        return self.get_board_items(
            WORK_ORDERS_BOARD_ID
        )


# =============================================================
# Standalone test
# =============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("MONDAY.COM CLIENT TEST")
    print("=" * 60)

    client = MondayClient()

    # ---------------------------------------------------------
    # Deals
    # ---------------------------------------------------------

    print("\nChecking Deals board...")

    deals_board = client.get_board(
        DEALS_BOARD_ID
    )

    print(
        f"Board: {deals_board['name']}"
    )

    print(
        f"ID: {deals_board['id']}"
    )

    print("\nFetching Deals...")

    deals = client.get_deals()

    print(
        f"\n✓ Total Deals: {len(deals)}"
    )

    if deals:
        print("\nFirst 3 Deals:")

        for item in deals[:3]:
            print(
                f"  - {item['name']}"
            )

    # ---------------------------------------------------------
    # Work Orders
    # ---------------------------------------------------------

    print("\nChecking Work Orders board...")

    work_orders_board = client.get_board(
        WORK_ORDERS_BOARD_ID
    )

    print(
        f"Board: {work_orders_board['name']}"
    )

    print(
        f"ID: {work_orders_board['id']}"
    )

    print("\nFetching Work Orders...")

    work_orders = client.get_work_orders()

    print(
        f"\n✓ Total Work Orders: "
        f"{len(work_orders)}"
    )

    if work_orders:
        print("\nFirst 3 Work Orders:")

        for item in work_orders[:3]:
            print(
                f"  - {item['name']}"
            )

    print("\n" + "=" * 60)
    print("MONDAY.COM INTEGRATION SUCCESSFUL ✓")
    print("=" * 60)