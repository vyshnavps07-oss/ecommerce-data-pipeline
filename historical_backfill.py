
import os
from pathlib import Path
from datetime import timedelta

import requests
import pandas as pd
import numpy as np
from google.cloud import bigquery


# ============================================================
# 1. CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

CREDENTIALS_FILE = BASE_DIR / "gcp_credentials.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(CREDENTIALS_FILE)

PROJECT_ID = "hazel-core-509607-k3"
DATASET_ID = "sales_and_marketing"

# New tables: keep the existing table untouched
SALES_TABLE_ID = "daily_product_sales"
MARKETING_TABLE_ID = "daily_category_marketing"

SALES_TABLE_REF = (
    f"{PROJECT_ID}.{DATASET_ID}.{SALES_TABLE_ID}"
)

MARKETING_TABLE_REF = (
    f"{PROJECT_ID}.{DATASET_ID}.{MARKETING_TABLE_ID}"
)

API_URL = "https://fakestoreapi.com/products"

DAYS = 730
RANDOM_SEED = 42

# Keep False initially. Change to True only after
# reviewing the generated data and validation output.
UPLOAD_TO_BIGQUERY = True


# ============================================================
# 2. EXTRACT PRODUCT CATALOG FROM FAKESTORE API
# ============================================================

def extract_base_catalog():
    """Extract product catalogue from FakeStoreAPI."""

    print("\nFetching product catalogue from FakeStoreAPI...")

    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()

    data = response.json()

    if not data:
        raise ValueError("API returned an empty product catalogue.")

    df = pd.DataFrame(data)

    required_columns = ["id", "title", "price", "category"]

    missing_columns = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing API columns: {missing_columns}"
        )

    catalog_df = df[required_columns].copy()

    catalog_df["id"] = pd.to_numeric(
        catalog_df["id"], errors="raise"
    ).astype("int64")

    catalog_df["price"] = pd.to_numeric(
        catalog_df["price"], errors="raise"
    )

    if catalog_df["id"].duplicated().any():
        raise ValueError("Duplicate product IDs found.")

    if catalog_df["price"].isna().any():
        raise ValueError("Missing product prices found.")

    if (catalog_df["price"] < 0).any():
        raise ValueError("Negative product prices found.")

    print(f"Products extracted: {len(catalog_df)}")
    print("Categories:", catalog_df["category"].nunique())

    return catalog_df


# ============================================================
# 3. GENERATE HISTORICAL SALES AND MARKETING DATA
# ============================================================

def generate_historical_data(base_catalog_df, days=730):
    """
    Generate two separate datasets:

    1. Sales: one row per product per date.
    2. Marketing: one row per category per date.
    """

    print(f"\nGenerating {days} days of historical data...")

    rng = np.random.default_rng(RANDOM_SEED)

    # Base daily advertising budget by category
    base_ad_spend = {
        "men's clothing": 150.00,
        "women's clothing": 200.00,
        "jewelery": 80.00,
        "electronics": 300.00
    }

    # Check that all API categories have a budget
    api_categories = set(base_catalog_df["category"].unique())
    budget_categories = set(base_ad_spend.keys())

    missing_budgets = api_categories - budget_categories

    if missing_budgets:
        raise ValueError(
            f"Missing advertising budgets for: {missing_budgets}"
        )

    end_date = pd.Timestamp.now("UTC").date()

    date_list = [
        end_date - timedelta(days=x)
        for x in reversed(range(days))
    ]

    sales_records = []
    marketing_records = []

    # Loop through each date
    for current_date in date_list:

        # Weekend multiplier
        is_weekend = current_date.weekday() >= 5

        traffic_multiplier = 1.5 if is_weekend else 1.0

        # ----------------------------------------------------
        # A. CATEGORY-LEVEL MARKETING DATA
        # One record per category per date
        # ----------------------------------------------------

        for category, base_budget in base_ad_spend.items():

            daily_ad_spend = round(
                base_budget
                * traffic_multiplier
                * rng.uniform(0.9, 1.1),
                2
            )

            marketing_records.append({
                "category": category,
                "daily_ad_spend": daily_ad_spend,
                "transaction_date": current_date
            })

        # ----------------------------------------------------
        # B. PRODUCT-LEVEL SALES DATA
        # One record per product per date
        # ----------------------------------------------------

        for product in base_catalog_df.itertuples(index=False):

            units_sold = int(
                rng.integers(5, 50) * traffic_multiplier
            )

            daily_revenue = round(
                float(product.price) * units_sold,
                2
            )

            sales_records.append({
                "product_id": int(product.id),
                "title": product.title,
                "price": float(product.price),
                "category": product.category,
                "units_sold_today": units_sold,
                "daily_revenue": daily_revenue,
                "transaction_date": current_date
            })

    # Convert records into DataFrames
    sales_df = pd.DataFrame(sales_records)
    marketing_df = pd.DataFrame(marketing_records)

    # Convert date columns to Python date objects
    sales_df["transaction_date"] = pd.to_datetime(
        sales_df["transaction_date"]
    ).dt.date

    marketing_df["transaction_date"] = pd.to_datetime(
        marketing_df["transaction_date"]
    ).dt.date

    print("\nHistorical data generation completed.")

    return sales_df, marketing_df


# ============================================================
# 4. DATA QUALITY VALIDATION
# ============================================================

def validate_data(sales_df, marketing_df, catalog_df, days):

    print("\nRunning data quality checks...")

    expected_sales = len(catalog_df) * days
    expected_marketing = 4 * days

    # Check expected record counts
    assert len(sales_df) == expected_sales, (
        f"Expected {expected_sales} sales records, "
        f"found {len(sales_df)}"
    )

    assert len(marketing_df) == expected_marketing, (
        f"Expected {expected_marketing} marketing records, "
        f"found {len(marketing_df)}"
    )

    # Check sales uniqueness
    assert not sales_df.duplicated(
        subset=["product_id", "transaction_date"]
    ).any(), "Duplicate product-date sales records found."

    # Check marketing uniqueness
    assert not marketing_df.duplicated(
        subset=["category", "transaction_date"]
    ).any(), "Duplicate category-date marketing records found."

    # Check missing values
    assert not sales_df.isnull().any().any(), (
        "Missing values found in sales data."
    )

    assert not marketing_df.isnull().any().any(), (
        "Missing values found in marketing data."
    )

    # Check negative values
    assert (sales_df["units_sold_today"] >= 0).all()
    assert (sales_df["daily_revenue"] >= 0).all()
    assert (marketing_df["daily_ad_spend"] >= 0).all()

    # Check that sales and marketing cover the same dates
    assert set(sales_df["transaction_date"]) == set(
        marketing_df["transaction_date"]
    ), "Sales and marketing date ranges do not match."

    print("All validation checks passed.")

    print("\n------------------------------")
    print("DATA VALIDATION SUMMARY")
    print("------------------------------")

    print(f"Products: {len(catalog_df)}")
    print(f"Days: {days}")
    print(f"Sales records: {len(sales_df)}")
    print(f"Marketing records: {len(marketing_df)}")

    print("\nSales preview:")
    print(sales_df.head())

    print("\nMarketing preview:")
    print(marketing_df.head())

    print("\nSales date range:")
    print(
        sales_df["transaction_date"].min(),
        "to",
        sales_df["transaction_date"].max()
    )

    print("\nMarketing records by category:")
    print(marketing_df.groupby("category").size())


# ============================================================
# 5. LOAD SALES DATA INTO BIGQUERY
# ============================================================

def load_sales_to_bigquery(df):

    print(f"\nLoading sales data into {SALES_TABLE_REF}...")

    client = bigquery.Client(project=PROJECT_ID)

    schema = [
        bigquery.SchemaField("product_id", "INT64"),
        bigquery.SchemaField("title", "STRING"),
        bigquery.SchemaField("price", "FLOAT64"),
        bigquery.SchemaField("category", "STRING"),
        bigquery.SchemaField("units_sold_today", "INT64"),
        bigquery.SchemaField("daily_revenue", "FLOAT64"),
        bigquery.SchemaField("transaction_date", "DATE")
    ]

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition="WRITE_TRUNCATE"
    )

    job = client.load_table_from_dataframe(
        df,
        SALES_TABLE_REF,
        job_config=job_config
    )

    job.result()

    print(f"Sales upload completed: {job.output_rows} rows")


# ============================================================
# 6. LOAD MARKETING DATA INTO BIGQUERY
# ============================================================

def load_marketing_to_bigquery(df):

    print(
        f"\nLoading marketing data into {MARKETING_TABLE_REF}..."
    )

    client = bigquery.Client(project=PROJECT_ID)

    schema = [
        bigquery.SchemaField("category", "STRING"),
        bigquery.SchemaField("daily_ad_spend", "FLOAT64"),
        bigquery.SchemaField("transaction_date", "DATE")
    ]

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition="WRITE_TRUNCATE"
    )

    job = client.load_table_from_dataframe(
        df,
        MARKETING_TABLE_REF,
        job_config=job_config
    )

    job.result()

    print(f"Marketing upload completed: {job.output_rows} rows")


# ============================================================
# 7. MAIN EXECUTION
# ============================================================

if __name__ == "__main__":

    try:

        # Step 1: Extract product catalogue
        catalog_df = extract_base_catalog()

        # Step 2: Generate separate datasets
        sales_df, marketing_df = generate_historical_data(
            catalog_df,
            days=DAYS
        )

        # Step 3: Validate generated data
        validate_data(
            sales_df,
            marketing_df,
            catalog_df,
            DAYS
        )

        # Step 4: Upload only when explicitly enabled
        if UPLOAD_TO_BIGQUERY:

            print("\nBigQuery upload enabled.")

            load_sales_to_bigquery(sales_df)
            load_marketing_to_bigquery(marketing_df)

            print("\nHistorical backfill completed successfully.")

        else:

            print("\nBigQuery upload is disabled.")
            print("Data was generated and validated only.")
            print("No existing BigQuery tables were modified.")

    except Exception as error:

        print("\nPIPELINE FAILED")
        print(f"Error: {error}")

        raise
