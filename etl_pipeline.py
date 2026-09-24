import requests
import pandas as pd
import numpy as np
from google.cloud import bigquery
import os
from datetime import datetime

# 1. Configuration & Authentication
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcp_credentials.json"

PROJECT_ID = "hazel-core-509607-k3" 
DATASET_ID = "sales_and_marketing"
TABLE_ID = "daily_sales_performance"
TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

def extract_ecommerce_data():
    """Extracts product and sales data from FakeStoreAPI."""
    print("Extracting sales data from FakeStoreAPI...")
    url = "https://fakestoreapi.com/products"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def transform_data(raw_products):
    """Flattens JSON, cleans data, and joins simulated marketing spend."""
    print("Transforming and unifying data...")
    df = pd.DataFrame(raw_products)
    
    # Select only necessary columns
    df = df[['id', 'title', 'price', 'category']]
    
    # Simulate today's transaction volume
    np.random.seed(int(datetime.now().timestamp()))
    df['units_sold_today'] = np.random.randint(5, 50, size=len(df))
    df['daily_revenue'] = df['price'] * df['units_sold_today']
    
    # Simulate siloed Marketing Spend data 
    marketing_data = {
        'category': ["men's clothing", "women's clothing", "jewelery", "electronics"],
        'daily_ad_spend': [150.00, 200.00, 80.00, 300.00]
    }
    marketing_df = pd.DataFrame(marketing_data)
    
    # Join Sales Data with Marketing Data on 'category'
    final_df = pd.merge(df, marketing_df, on='category', how='left')
    
    # Add a timestamp for time-series analysis in Tableau
    final_df['transaction_date'] = pd.Timestamp.now('UTC').date()
    final_df['transaction_date'] = pd.to_datetime(final_df['transaction_date'])
    
    print(f"Transformed {len(final_df)} product records.")
    return final_df

def load_to_bigquery(df):
    """Appends the unified DataFrame to the BigQuery table."""
    print(f"Loading data to BigQuery table: {TABLE_REF}...")
    client = bigquery.Client()
    
    # Configure job to append data and auto-detect schema on the first run
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_APPEND", 
        autodetect=True 
    )
    
    job = client.load_table_from_dataframe(df, TABLE_REF, job_config=job_config)
    job.result() 
    print("Sales and Marketing data loaded successfully!")

if __name__ == "__main__":
    raw_data = extract_ecommerce_data()
    clean_df = transform_data(raw_data)
    load_to_bigquery(clean_df)