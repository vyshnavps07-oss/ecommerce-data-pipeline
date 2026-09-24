import gspread
from google.cloud import bigquery
from google.oauth2.service_account import Credentials
import pandas as pd
import os

# 1. Configuration & Authentication
CREDENTIALS_FILE = "gcp_credentials.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_FILE
PROJECT_ID = "hazel-core-509607-k3"

def extract_and_aggregate_from_bq():
    """Runs a SQL query in BigQuery to calculate daily KPIs."""
    print("Querying BigQuery for aggregated KPIs...")
    client = bigquery.Client()
    
    # We use MAX(daily_ad_spend) because our previous join duplicated the ad spend across every product in a category
    query = f"""
        SELECT 
            category,
            SUM(daily_revenue) as total_revenue,
            MAX(daily_ad_spend) as category_ad_spend,
            transaction_date
        FROM `{PROJECT_ID}.sales_and_marketing.daily_sales_performance`
        GROUP BY category, transaction_date
        ORDER BY total_revenue DESC
    """
    
    df = client.query(query).to_dataframe()
    
    # Calculate Return on Ad Spend (ROAS)
    df['ROAS'] = (df['total_revenue'] / df['category_ad_spend']).round(2)
    
    # Convert date to string so Google Sheets can read it properly
    df['transaction_date'] = df['transaction_date'].astype(str)
    
    print(f"Aggregated {len(df)} category records.")
    return df

def push_to_google_sheets(df):
    """Pushes the aggregated DataFrame to the Google Sheet."""
    print("Connecting to Google Sheets API...")
    
    # gspread requires explicit permission scopes for Drive and Sheets
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    gc = gspread.authorize(creds)
    
    # Open the sheet and select the first tab
    print("Writing data to Ecommerce_KPI_Bridge...")
    workbook = gc.open("Ecommerce_KPI_Bridge")
    sheet = workbook.sheet1
    
    # Clear old data and insert the new data
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())
    print("Data successfully synced to Google Sheets!")

if __name__ == "__main__":
    kpi_df = extract_and_aggregate_from_bq()
    push_to_google_sheets(kpi_df)