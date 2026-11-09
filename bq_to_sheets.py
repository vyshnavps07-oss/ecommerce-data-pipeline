
import os
from pathlib import Path

import gspread
import pandas as pd

from google.cloud import bigquery
from google.oauth2.service_account import Credentials


# ============================================================
# 1. CONFIGURATION & AUTHENTICATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

CREDENTIALS_FILE = BASE_DIR / "gcp_credentials.json"

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(
    CREDENTIALS_FILE
)

PROJECT_ID = "hazel-core-509607-k3"
DATASET_ID = "sales_and_marketing"

SALES_TABLE = f"{PROJECT_ID}.{DATASET_ID}.daily_product_sales"

MARKETING_TABLE = (
    f"{PROJECT_ID}.{DATASET_ID}.daily_category_marketing"
)

SPREADSHEET_NAME = "Ecommerce_KPI_Bridge"

BQ_LOCATION = "US"


# ============================================================
# 2. EXTRACT AND AGGREGATE DATA FROM BIGQUERY
# ============================================================

def extract_and_aggregate_from_bq():
    """
    Aggregate product-level sales and join with
    category-level marketing spend.
    """

    print("\nQuerying BigQuery for aggregated KPIs...")

    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
        WITH sales_summary AS (

            SELECT
                category,
                transaction_date,
                SUM(daily_revenue) AS total_revenue,
                SUM(units_sold_today) AS total_units_sold

            FROM `{SALES_TABLE}`

            GROUP BY
                category,
                transaction_date
        ),

        marketing_summary AS (

            SELECT
                category,
                transaction_date,
                SUM(daily_ad_spend) AS total_ad_spend

            FROM `{MARKETING_TABLE}`

            GROUP BY
                category,
                transaction_date
        )

        SELECT
            s.category,
            s.transaction_date,
            s.total_revenue,
            s.total_units_sold,
            m.total_ad_spend,

            ROUND(
                SAFE_DIVIDE(
                    s.total_revenue,
                    m.total_ad_spend
                ), 2
            ) AS ROAS

        FROM sales_summary s

        INNER JOIN marketing_summary m

            ON s.category = m.category
            AND s.transaction_date = m.transaction_date

        ORDER BY
            s.transaction_date,
            s.category
    """

    df = client.query(
        query,
        location=BQ_LOCATION
    ).to_dataframe()

    if df.empty:
        raise ValueError(
            "BigQuery returned no reporting records."
        )

    # Convert date into a Google Sheets-compatible string
    df["transaction_date"] = (
        pd.to_datetime(df["transaction_date"])
        .dt.strftime("%Y-%m-%d")
    )

    # Check for missing values
    if df.isnull().any().any():
        raise ValueError(
            "Missing values found in the aggregated KPI dataset."
        )

    print("\nBigQuery aggregation completed.")

    print(f"Total reporting records: {len(df)}")

    print("\nCategory summary:")

    print(
        df.groupby("category").agg(
            total_revenue=("total_revenue", "sum"),
            total_units_sold=("total_units_sold", "sum"),
            total_ad_spend=("total_ad_spend", "sum")
        ).round(2)
    )

    print("\nData preview:")
    print(df.head())

    return df


# ============================================================
# 3. PREPARE DATA FOR GOOGLE SHEETS
# ============================================================

def prepare_sheet_data(df):
    """Convert DataFrame values into Sheets-compatible values."""

    sheet_data = [df.columns.tolist()]

    for row in df.itertuples(index=False, name=None):

        clean_row = []

        for value in row:

            if pd.isna(value):
                clean_row.append("")
            elif hasattr(value, "item"):
                clean_row.append(value.item())
            else:
                clean_row.append(value)

        sheet_data.append(clean_row)

    return sheet_data


# ============================================================
# 4. PUSH AGGREGATED DATA TO GOOGLE SHEETS
# ============================================================

def push_to_google_sheets(df):
    """Replace the existing reporting data in Google Sheets."""

    print("\nConnecting to Google Sheets API...")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_file(
        str(CREDENTIALS_FILE),
        scopes=scopes
    )

    gc = gspread.authorize(creds)

    print(f"Opening spreadsheet: {SPREADSHEET_NAME}")

    workbook = gc.open(SPREADSHEET_NAME)

    sheet = workbook.sheet1

    # Prepare the reporting data
    sheet_data = prepare_sheet_data(df)

    # Clear previous reporting data
    sheet.clear()

    # Upload the latest aggregated records
    sheet.update(
        values=sheet_data,
        range_name="A1"
    )

    print("\nGoogle Sheets synchronization successful!")

    print(f"Records uploaded: {len(df)}")
    print(f"Spreadsheet: {SPREADSHEET_NAME}")


# ============================================================
# 5. MAIN EXECUTION
# ============================================================

if __name__ == "__main__":

    try:

        # Step 1: Extract and aggregate BigQuery data
        kpi_df = extract_and_aggregate_from_bq()

        # Step 2: Push the results to Google Sheets
        push_to_google_sheets(kpi_df)

        print("\nReporting pipeline completed successfully.")

    except Exception as error:

        print("\nREPORTING PIPELINE FAILED")
        print(f"Error: {error}")

        raise
