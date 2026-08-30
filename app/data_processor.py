import math
from datetime import datetime

import pandas as pd


# ============================================================
# Monday.com column IDs → clean application field names
# ============================================================

DEALS_COLUMNS = {
    "color_mm6q5djh": "owner_code",
    "dropdown_mm6qvkkr": "client_code",
    "color_mm6qtr3d": "deal_status",
    "date_mm6q93wm": "close_date",
    "color_mm6qm4f7": "closure_probability",
    "numeric_mm6qfn8z": "deal_value",
    "date_mm6qxt7r": "tentative_close_date",
    "color_mm6qcmwf": "deal_stage",
    "color_mm6qc70w": "product_deal",
    "color_mm6qfczm": "sector_service",
    "date_mm6qkjq": "created_date",
}


WORK_ORDER_COLUMNS = {
    "dropdown_mm6qntvq": "customer_code",
    "dropdown_mm6q2v7q": "serial_number",
    "color_mm6q33nj": "nature_of_work",
    "color_mm6qg2t6": "last_executed_month",
    "color_mm6qzsn4": "execution_status",
    "date_mm6qcgst": "data_delivery_date",
    "date_mm6q3tqh": "po_loi_date",
    "color_mm6qtsxc": "document_type",
    "date_mm6q77ma": "probable_start_date",
    "date_mm6qydmg": "probable_end_date",
    "color_mm6qc0ew": "bd_kam_code",
    "color_mm6qejaj": "sector",
    "color_mm6q42ev": "type_of_work",
    "color_mm6qavqj": "skylark_platform",
    "date_mm6qv6hd": "last_invoice_date",
    "dropdown_mm6qqrvr": "latest_invoice_number",
    "numeric_mm6qva24": "amount_excl_gst",
    "numeric_mm6qj4qw": "amount_incl_gst",
    "numeric_mm6qym99": "billed_value_excl_gst",
    "numeric_mm6qrqzh": "billed_value_incl_gst",
    "numeric_mm6qh2r5": "collected_amount",
    "numeric_mm6qm4wp": "amount_to_bill_excl_gst",
    "numeric_mm6q6ra5": "amount_to_bill_incl_gst",
    "numeric_mm6qnw8t": "amount_receivable",
    "color_mm6qqsm9": "ar_priority",
    "numeric_mm6qdjye": "quantity_by_ops",
    "dropdown_mm6qvppf": "quantity_as_per_po",
    "numeric_mm6qgqwh": "quantity_billed",
    "numeric_mm6q71wq": "balance_quantity",
    "color_mm6qah4r": "invoice_status",
    "text_mm6qe9nj": "expected_billing_month",
    "color_mm6qh326": "actual_billing_month",
    "text_mm6q8jk1": "actual_collection_month",
    "color_mm6qsy6q": "wo_status_billed",
    "text_mm6qggbc": "collection_status",
    "text_mm6qse5f": "collection_date",
    "color_mm6qa2vq": "billing_status",
}


# ============================================================
# Basic cleaning helpers
# ============================================================

NULL_VALUES = {
    "",
    " ",
    "-",
    "--",
    "n/a",
    "na",
    "null",
    "none",
    "nan",
}


def clean_text(value):
    """Normalize text values and convert empty values to None."""

    if value is None:
        return None

    value = str(value).strip()

    if value.lower() in NULL_VALUES:
        return None

    return value


def clean_number(value):
    """Convert messy numeric values into float."""

    if value is None:
        return None

    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)

    text = str(value).strip()

    if text.lower() in NULL_VALUES:
        return None

    # Remove common formatting characters.
    text = (
        text.replace(",", "")
        .replace("₹", "")
        .replace("Rs.", "")
        .replace("Rs", "")
    )

    try:
        return float(text)
    except ValueError:
        return None


def clean_date(value):
    """
    Normalize date values.

    Returns ISO format:
        YYYY-MM-DD

    Invalid or missing dates become None.
    """

    if value is None:
        return None

    text = str(value).strip()

    if text.lower() in NULL_VALUES:
        return None

    parsed = pd.to_datetime(
        text,
        errors="coerce",
        dayfirst=False,
    )

    if pd.isna(parsed):
        return None

    return parsed.strftime("%Y-%m-%d")


# ============================================================
# Field categories
# ============================================================

DEAL_NUMERIC_FIELDS = {
    "deal_value",
}

DEAL_DATE_FIELDS = {
    "close_date",
    "tentative_close_date",
    "created_date",
}

WORK_ORDER_NUMERIC_FIELDS = {
    "amount_excl_gst",
    "amount_incl_gst",
    "billed_value_excl_gst",
    "billed_value_incl_gst",
    "collected_amount",
    "amount_to_bill_excl_gst",
    "amount_to_bill_incl_gst",
    "amount_receivable",
    "quantity_by_ops",
    "quantity_billed",
    "balance_quantity",
}

WORK_ORDER_DATE_FIELDS = {
    "data_delivery_date",
    "po_loi_date",
    "probable_start_date",
    "probable_end_date",
    "last_invoice_date",
    "collection_date",
}


# ============================================================
# Item processing
# ============================================================

def process_item(item, column_mapping):
    """
    Convert one raw Monday item into a clean dictionary.
    """

    result = {
        "id": item.get("id"),
        "name": clean_text(item.get("name")),
    }

    for column in item.get("column_values", []):

        column_id = column.get("id")

        field_name = column_mapping.get(column_id)

        if not field_name:
            continue

        value = column.get("text")

        # Numeric fields
        if field_name in (
            DEAL_NUMERIC_FIELDS
            | WORK_ORDER_NUMERIC_FIELDS
        ):
            result[field_name] = clean_number(value)

        # Date fields
        elif field_name in (
            DEAL_DATE_FIELDS
            | WORK_ORDER_DATE_FIELDS
        ):
            result[field_name] = clean_date(value)

        # Text / status / dropdown fields
        else:
            result[field_name] = clean_text(value)

    return result


def process_board(items, column_mapping):
    """
    Process a list of raw Monday.com items.

    The Monday client is responsible for retrieving
    all records. This function is responsible only
    for transforming them into clean application data.
    """

    if not items:
        return []

    return [
        process_item(item, column_mapping)
        for item in items
    ]


# ============================================================
# Data quality analysis
# ============================================================

def find_missing_fields(records):
    """
    Identify fields that are frequently missing.

    Returns:
        {
            "field_name": missing_count
        }
    """

    if not records:
        return {}

    dataframe = pd.DataFrame(records)

    missing = {}

    for column in dataframe.columns:

        count = dataframe[column].isna().sum()

        if count > 0:
            missing[column] = int(count)

    return missing


def create_dataframe(records):
    """
    Convert processed records into a Pandas DataFrame.
    """

    dataframe = pd.DataFrame(records)

    if dataframe.empty:
        return dataframe

    return dataframe


def generate_data_quality_report(records):
    """
    Generate a concise data-quality summary.
    """

    if not records:
        return {
            "record_count": 0,
            "missing_fields": {},
            "message": "No records were returned from Monday.com.",
        }

    dataframe = pd.DataFrame(records)

    missing_fields = {}

    for column in dataframe.columns:

        missing_count = int(
            dataframe[column].isna().sum()
        )

        if missing_count:
            missing_fields[column] = {
                "missing": missing_count,
                "percentage": round(
                    missing_count
                    / len(dataframe)
                    * 100,
                    2,
                ),
            }

    return {
        "record_count": len(dataframe),
        "field_count": len(dataframe.columns),
        "missing_fields": missing_fields,
    }