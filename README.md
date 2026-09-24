# E-Commerce Analytics: Modern Data Stack Pipeline

## 📌 Executive Summary
This project architects an automated, end-to-end cloud data pipeline (ELT) to solve a common revenue operations problem: siloed data. By extracting real-time e-commerce product catalogs via API and joining them with simulated departmental marketing spend, this pipeline creates a unified source of truth in a cloud data warehouse. 

**Key Business Insight:** Initial data models reveal severe inefficiencies in ad spend. The Jewelry category generated a Return on Ad Spend (ROAS) of ~374x, while Women's Clothing generated only ~21x despite having a 150% higher ad budget. Reallocating spend could immediately increase top-line revenue.

## 🏗️ Architecture & Technology Stack
* **Data Ingestion:** Python (`requests`, `pandas`) pulling from FakeStoreAPI.
* **Cloud Data Warehouse:** Google BigQuery (Serverless data storage & SQL analytics).
* **Data Transformation:** Python and BigQuery SQL.
* **BI Caching Layer:** Google Sheets API (`gspread`).
* **Visualization:** [https://public.tableau.com/views/ecommerce-data-pipeline/Dashboard1?:language=en-US&:sid=&:redirect=auth&:display_count=n&:origin=viz_share_link]

## 🗄️ Data Pipeline Flow
1. **Extract:** Python extracts live JSON product and pricing data from the REST API.
2. **Load:** Raw data is cleaned, typed, and loaded directly into a Google BigQuery dataset.
3. **Transform:** Simulated marketing spend is joined to the sales table using Pandas/SQL.
4. **Serve:** A secondary Python script queries BigQuery for aggregated KPIs (Total Revenue, Ad Spend, ROAS) and pushes the live results to a Google Sheet connected to Tableau.

## 🚀 How to Run the Pipeline
To replicate this environment locally:

1. Clone this repository.
2. Create a virtual environment and install dependencies.
3. Set up a Google Cloud Project with BigQuery and generate a Service Account JSON key.
4. Save the key as `gcp_credentials.json` in the root directory.
5. Execute the pipeline:
   ```bash
   python etl_pipeline.py
   python historical_backfill.py
   python bq_to_sheets.py