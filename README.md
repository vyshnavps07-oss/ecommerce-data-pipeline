# E-Commerce Analytics Data Pipeline

An end-to-end data engineering and business intelligence portfolio project that combines an API-sourced product catalogue with simulated daily sales and marketing data, stores the resulting records in Google BigQuery, prepares reporting data in Google Sheets, and presents performance metrics in an interactive Tableau dashboard.

> **Data transparency:** FakeStoreAPI supplies the product catalogue and listed prices. Units sold, daily revenue and advertising spend in this project are simulated for analytical and dashboarding purposes. The resulting revenue, advertising spend and ROAS figures are illustrative—not actual store transactions or real advertising campaign results.

## Dashboard

**[View the interactive Tableau dashboard](https://public.tableau.com/views/ecommerce-data-pipeline/Dashboard1?:language=en-US&:sid=&:redirect=auth&:display_count=n&:origin=viz_share_link)**

The dashboard is designed to explore e-commerce performance through KPI cards, time-series analysis, category comparisons and a category-level performance summary. Available dashboard filters can be used to narrow the reporting period and product category.

## Project objectives

- Retrieve product and pricing information from a public REST API.
- Transform catalogue data into an analytical dataset.
- Generate illustrative daily sales and marketing records.
- Store analytical data in Google BigQuery.
- Aggregate revenue, units, advertising spend and ROAS using SQL.
- Publish reporting data to Google Sheets for Tableau consumption.
- Build an interactive dashboard for category and time-based analysis.

## Architecture

```text
             FakeStoreAPI
                  |
                  v
       Python API extraction
          (requests, pandas)
                  |
                  v
     Data preparation and simulation
       (Pandas, NumPy, Python)
                  |
                  v
           Google BigQuery
        (data storage / SQL)
                  |
                  v
       BigQuery KPI aggregation
                  |
                  v
            Google Sheets
                  |
                  v
          Tableau Dashboard
       (interactive reporting)
```

## Technology stack

| Layer | Tools | Purpose |
|---|---|---|
| API ingestion | FakeStoreAPI, Python `requests` | Retrieve product catalogue data |
| Data transformation | Pandas, NumPy | Clean, shape and generate analytical records |
| Data warehouse | Google BigQuery | Store records and run SQL aggregations |
| Reporting bridge | Google Sheets API, `gspread` | Make aggregated data available to Tableau |
| Data visualisation | Tableau Public / Tableau Desktop | Interactive dashboard and KPI reporting |

## Data and analytical approach

### API-sourced data

The pipeline retrieves the product catalogue from the FakeStoreAPI endpoint:

`https://fakestoreapi.com/products`

The API provides product attributes such as product ID, title, price and category.

### Simulated data

The project generates illustrative transaction and marketing metrics rather than retrieving real transaction or ad-platform data. These include:

- Units sold per product and date.
- Daily revenue, calculated from listed product price and simulated units sold.
- Daily advertising spend by category.
- Weekend uplift and modest variation in simulated advertising spend in the historical data generation script.

The historical backfill script generates a two-year sample (`730` days) and combines it with the available product catalogue. Because the underlying sales and advertising inputs are simulated, any patterns or efficiency comparisons should be interpreted as results of the simulation logic.

### Key metrics

| Metric | Definition |
|---|---|
| Total Revenue | Sum of simulated daily revenue |
| Units Sold | Sum of simulated units sold |
| Advertising Spend | Sum of simulated advertising spend |
| ROAS | Total revenue divided by total advertising spend |

For an overall or multi-day ROAS calculation, use the ratio of sums:

```text
Overall ROAS = SUM(Total Revenue) / SUM(Advertising Spend)
```

Do not calculate overall ROAS by taking a simple average of daily ROAS values, because that gives each day equal weight regardless of its advertising spend.

## Repository contents

| File | Description |
|---|---|
| `etl_pipeline.py` | Extracts the current FakeStoreAPI catalogue, generates a sample of daily sales and marketing data, and loads the resulting records to BigQuery. |
| `historical_backfill.py` | Generates a 730-day historical sample from the product catalogue and loads the generated records to BigQuery. |
| `bq_to_sheets.py` | Queries BigQuery for category/date-level reporting metrics and writes the result to the `Ecommerce_KPI_Bridge` Google Sheet. |
| `.gitignore` | Excludes the local Google Cloud service-account credential file. |

## BigQuery and reporting

The Python scripts use the following Google Cloud project and dataset configuration:

- **Project ID:** `hazel-core-509607-k3`
- **Dataset:** `sales_and_marketing`

The reporting script aggregates records by category and transaction date, calculates ROAS, and writes the reporting output to the first worksheet in the Google spreadsheet named `Ecommerce_KPI_Bridge`.

The Tableau dashboard uses this reporting layer to present the project KPIs and category/time-based analysis.

## Run locally

### 1. Clone the repository

```bash
git clone https://github.com/vyshnavps07-oss/ecommerce-data-pipeline.git
cd ecommerce-data-pipeline
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install requests pandas numpy google-cloud-bigquery pyarrow db-dtypes gspread google-auth
```

### 4. Configure Google Cloud credentials

1. Create or select a Google Cloud project.
2. Enable the BigQuery API and configure access to the target dataset.
3. Create a service account with the required BigQuery permissions.
4. Download its JSON key and save it in the project root as `gcp_credentials.json`.
5. Configure Google Sheets API access and share the `Ecommerce_KPI_Bridge` spreadsheet with the service-account email address.

**Security:** Never commit `gcp_credentials.json`, API secrets or other credentials to GitHub. The repository's `.gitignore` excludes this credential filename. If a credential has ever been committed, revoke or rotate it.

### 5. Run the scripts

Run the historical backfill only when you intend to create and load the historical sample:

```bash
python historical_backfill.py
```

Run the daily pipeline:

```bash
python etl_pipeline.py
```

Refresh the Google Sheets reporting output:

```bash
python bq_to_sheets.py
```

Run the scripts in the order appropriate to your data setup. The historical backfill uses append loading, so do not rerun it casually: repeated runs can append another copy of the generated date range.

## Important implementation notes

- The API source is a product catalogue, not an order-management system or advertising platform.
- Sales volume, revenue and advertising spend are synthetic and are intended to demonstrate a data pipeline and BI workflow.
- The current scripts use BigQuery load jobs with append behaviour. Review the target table and existing records before rerunning a load.
- The reporting script writes to the first worksheet of `Ecommerce_KPI_Bridge` and clears that worksheet before writing the refreshed output.
- A successful local run requires valid Google Cloud credentials, BigQuery permissions, Google Sheets API access and a spreadsheet shared with the service account.

## Future improvements

- Add automated orchestration and scheduled runs.
- Add idempotent load logic and stronger duplicate controls for backfills.
- Separate sales facts and category-level marketing facts to preserve their natural data grain.
- Add automated data-quality tests and reconciliation checks.
- Add a dependency lock file and environment configuration.
- Capture dashboard screenshots and document validated example insights.

## Author

**Vyshnav P S**  
Data Analytics | Python | SQL | BigQuery | Tableau

[GitHub Repository](https://github.com/vyshnavps07-oss/ecommerce-data-pipeline) · [Interactive Tableau Dashboard](https://public.tableau.com/views/ecommerce-data-pipeline/Dashboard1?:language=en-US&:sid=&:redirect=auth&:display_count=n&:origin=viz_share_link)
