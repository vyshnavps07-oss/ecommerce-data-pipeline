import requests
import pandas as pd
import numpy as np
from google.cloud import bigquery
import os
from datetime import datetime, timedelta

# 1. Configuration & Authentication
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcp_credentials.json"

PROJECT_ID = "hazel-core-509607-k3" 
DATASET_ID = "sales_and_marketing"
TABLE_ID = "daily_sales_performance"
TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

def extract_base_catalog():
    """Extracts the base product catalog from FakeStoreAPI just once."""
    print("Fetching base product catalog...")
    url = "https://fakestoreapi.com/products"
    response = requests.get(url)
    response.raise_for_status()
    
    df = pd.DataFrame(response.json())
    return df[['id', 'title', 'price', 'category']]

def generate_historical_data(base_catalog_df, days=730):
    """Simulates 2 years of daily transactions and marketing spend."""
    print(f"Generating {days} days of historical transaction data...")
    
    # Generate a list of dates for the last 2 years
    end_date = pd.Timestamp.now('UTC').date()
    date_list = [end_date - timedelta(days=x) for x in range(days)]
    
    historical_records = []
    
    # Base marketing spend by category
    base_ad_spend = {
        "men's clothing": 150.00, 
        "women's clothing": 200.00, 
        "jewelery": 80.00, 
        "electronics": 300.00
    }

    # Loop through each day to simulate sales
    for current_date in date_list:
        # Simulate weekend traffic spikes (higher sales, higher ad spend)
        is_weekend = current_date.weekday() >= 5
        traffic_multiplier = 1.5 if is_weekend else 1.0
        
        for _, product in base_catalog_df.iterrows():
            # Randomize units sold with the traffic multiplier
            units_sold = int(np.random.randint(5, 50) * traffic_multiplier)
            daily_revenue = product['price'] * units_sold
            
            # Fluctuate daily ad spend slightly for realism (+/- 10%)
            cat = product['category']
            daily_ad_spend = round(base_ad_spend[cat] * traffic_multiplier * np.random.uniform(0.9, 1.1), 2)
            
            historical_records.append({
                'id': product['id'],
                'title': product['title'],
                'price': product['price'],
                'category': cat,
                'units_sold_today': units_sold,
                'daily_revenue': daily_revenue,
                'daily_ad_spend': daily_ad_spend,
                'transaction_date': current_date
            })

    # Convert the massive list of dictionaries into a Pandas DataFrame
    final_df = pd.DataFrame(historical_records)
    
    # Ensure correct data types
    final_df['transaction_date'] = pd.to_datetime(final_df['transaction_date'])
    
    print(f"Generated {len(final_df)} total records across {days} days.")
    return final_df

def load_to_bigquery(df):
    """Appends the massive DataFrame to the BigQuery table."""
    print(f"Loading {len(df)} rows to BigQuery table: {TABLE_REF}...")
    client = bigquery.Client()
    
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_APPEND", 
        autodetect=True 
    )
    
    job = client.load_table_from_dataframe(df, TABLE_REF, job_config=job_config)
    job.result() 
    print("Historical backfill completed successfully!")

if __name__ == "__main__":
    catalog_df = extract_base_catalog()
    historical_df = generate_historical_data(catalog_df, days=730)
    load_to_bigquery(historical_df)