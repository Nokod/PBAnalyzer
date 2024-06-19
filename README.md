# Power BI Analyzer

This project contains a Python script that interacts with the Power BI API. The main goal of the script is to find unused columns in Power BI reports. The scripts analyze the data model of the reports and identifies columns that are not used in any visualizations. 

Unwanted access to this data can pose a __security risk__, and it is important to identify and remove unused columns to reduce the risk of data breaches.

## Scripts

The runner of the script must have fabric admin or global admin permissions.

- `PowerBI_get_report_used_and_consume_data.py`: This script fetches and analyzes data from Power BI reports that are shared within an organization. It uses an access token for authentication and interacts with the Power BI API. 

## Usage

The script requires the name of the output CSV file as a command-line argument

Example usage:

```bash
python PowerBI_get_report_used_and_consume_data.py --output-csv-filename output.csv
```

## Output
CSV file containing the following columns:
* Report ID
* Number of hidden columns
* All columns
* Unused columns
