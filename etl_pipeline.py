
import os
from pathlib import Path
from datetime import datetime, timezone

import requests
import pandas as pd
import numpy as np
from google.cloud import bigquery


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

SALES_TABLE = "daily_product_sales"
MARKETING_TABLE = "daily_category_marketing"

SALES_TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{SALES_TABLE}"
MARKETING_TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{MARKETING_TABLE}"

API_URL = "https://fakestoreapi.com/products"

BASE_AD_SPEND = {
    "men's clothing": 150.00,
    "women's clothing": 200.00,
    "jewelery": 80.00,
    "electronics": 300.00
}

BQ_LOCATION = "US"


# ============================================================
# 2. EXTRACT DATA FROM FAKESTORE API
# ============================================================

def extract_ecommerce_data():
    """Extract product catalogue from FakeStoreAPI."""

    print("\nExtracting product data from FakeStoreAPI...")

    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()

    products = response.json()

    if not products:
        raise ValueError("FakeStoreAPI returned no products.")

    df = pd.DataFrame(products)

    required_columns = ["id", "title", "price", "category"]

    if not set(required_columns).issubset(df.columns):
        raise ValueError("Required product fields are missing.")

    df = df[required_columns].copy()

    df["id"] = pd.to_numeric(
        df["id"], errors="raise"
    ).astype("int64")

    df["price"] = pd.to_numeric(
        df["price"], errors="raise"
    )

    if df["id"].duplicated().any():
        raise ValueError("Duplicate product IDs found.")

    if df["price"].isna().any() or (df["price"] < 0).any():
        raise ValueError("Invalid product prices found.")

    print(f"Products extracted: {len(df)}")

    return df


# ============================================================
# 3. TRANSFORM SALES AND MARKETING DATA
# ============================================================

def transform_data(products_df):
    """
    Generate separate product-level sales and
    category-level marketing datasets.
    """

    print("\nTransforming sales and marketing data...")

    current_date = datetime.now(timezone.utc).date()

    # Reproducible simulated values for the same date
    seed = int(current_date.strftime("%Y%m%d"))
    rng = np.random.default_rng(seed)

    api_categories = set(products_df["category"].unique())
    budget_categories = set(BASE_AD_SPEND.keys())

    missing_categories = api_categories - budget_categories

    if missing_categories:
        raise ValueError(
            f"Missing marketing budgets: {missing_categories}"
        )

    # --------------------------------------------------------
    # A. PRODUCT-LEVEL SALES
    # --------------------------------------------------------

    sales_records = []

    for product in products_df.itertuples(index=False):

        units_sold = int(rng.integers(5, 50))

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

    sales_df = pd.DataFrame(sales_records)

    # --------------------------------------------------------
    # B. CATEGORY-LEVEL MARKETING
    # --------------------------------------------------------

    is_weekend = current_date.weekday() >= 5
    traffic_multiplier = 1.5 if is_weekend else 1.0

    marketing_records = []

    for category, base_budget in BASE_AD_SPEND.items():

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

    marketing_df = pd.DataFrame(marketing_records)

    print(f"Sales records generated: {len(sales_df)}")
    print(f"Marketing records generated: {len(marketing_df)}")
    print(f"Transaction date: {current_date}")

    return sales_df, marketing_df


# ============================================================
# 4. VALIDATE DAILY DATA
# ============================================================

def validate_data(sales_df, marketing_df):

    print("\nValidating daily data...")

    assert not sales_df.duplicated(
        subset=["product_id", "transaction_date"]
    ).any(), "Duplicate product-date records found."

    assert not marketing_df.duplicated(
        subset=["category", "transaction_date"]
    ).any(), "Duplicate category-date records found."

    assert not sales_df.isnull().any().any(), (
        "Missing values found in sales data."
    )

    assert not marketing_df.isnull().any().any(), (
        "Missing values found in marketing data."
    )

    assert (sales_df["daily_revenue"] >= 0).all()
    assert (marketing_df["daily_ad_spend"] >= 0).all()

    print("Daily data validation passed.")


# ============================================================
# 5. CHECK WHETHER THE DATE ALREADY EXISTS IN BIGQUERY
# ============================================================

def check_existing_records(table_ref, date_column, current_date):

    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
        SELECT COUNT(*) AS record_count
        FROM `{table_ref}`
        WHERE {date_column} = @current_date
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "current_date",
                "DATE",
                current_date
            )
        ]
    )

    query_job = client.query(
        query,
        job_config=job_config,
        location=BQ_LOCATION
    )

    result = list(query_job.result())

    return result[0]["record_count"]


# ============================================================
# 6. LOAD DATA INTO BIGQUERY
# ============================================================

def load_to_bigquery(df, table_ref, schema):

    print(f"\nLoading data into {table_ref}...")

    client = bigquery.Client(project=PROJECT_ID)

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition="WRITE_APPEND"
    )

    job = client.load_table_from_dataframe(
        df,
        table_ref,
        job_config=job_config,
        location=BQ_LOCATION
    )

    job.result()

    print(f"Upload successful: {job.output_rows} rows")


# ============================================================
# 7. MAIN EXECUTION
# ============================================================

if __name__ == "__main__":

    try:

        # Step 1: Extract
        products_df = extract_ecommerce_data()

        # Step 2: Transform
        sales_df, marketing_df = transform_data(products_df)

        # Step 3: Validate
        validate_data(sales_df, marketing_df)

        current_date = sales_df["transaction_date"].iloc[0]

        # Step 4: Define BigQuery schemas
        sales_schema = [
            bigquery.SchemaField("product_id", "INT64"),
            bigquery.SchemaField("title", "STRING"),
            bigquery.SchemaField("price", "FLOAT64"),
            bigquery.SchemaField("category", "STRING"),
            bigquery.SchemaField("units_sold_today", "INT64"),
            bigquery.SchemaField("daily_revenue", "FLOAT64"),
            bigquery.SchemaField("transaction_date", "DATE")
        ]

        marketing_schema = [
            bigquery.SchemaField("category", "STRING"),
            bigquery.SchemaField("daily_ad_spend", "FLOAT64"),
            bigquery.SchemaField("transaction_date", "DATE")
        ]

        # Step 5: Check existing sales records
        existing_sales = check_existing_records(
            SALES_TABLE_REF,
            "transaction_date",
            current_date
        )

        # Step 6: Check existing marketing records
        existing_marketing = check_existing_records(
            MARKETING_TABLE_REF,
            "transaction_date",
            current_date
        )

        print("\nChecking existing BigQuery records...")

        print(f"Existing sales records: {existing_sales}")
        print(f"Existing marketing records: {existing_marketing}")

        # Step 7: Upload sales only if the date is missing
        if existing_sales == 0:

            load_to_bigquery(
                sales_df,
                SALES_TABLE_REF,
                sales_schema
            )

        elif existing_sales == len(sales_df):

            print(
                "\nSales data already exists for this date. "
                "Skipping upload."
            )

        else:

            raise ValueError(
                "Partial sales records exist for this date. "
                "Upload stopped to avoid duplicate records."
            )

        # Step 8: Upload marketing only if the date is missing
        if existing_marketing == 0:

            load_to_bigquery(
                marketing_df,
                MARKETING_TABLE_REF,
                marketing_schema
            )

        elif existing_marketing == len(marketing_df):

            print(
                "\nMarketing data already exists for this date. "
                "Skipping upload."
            )

        else:

            raise ValueError(
                "Partial marketing records exist for this date. "
                "Upload stopped to avoid duplicate records."
            )

        print("\nDaily ETL pipeline completed successfully.")

    except Exception as error:

        print("\nETL PIPELINE FAILED")
        print(f"Error: {error}")

        raise
