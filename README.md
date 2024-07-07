# Power BI Analyzer

This project contains two tools for finding unused data sources in your Power BI (Microsoft Fabric) reports.
These tools analyze the reports' data models and identify columns not used in visualizations.
Unwanted access to this data can pose a __security risk__, and it is essential to identify and remove unused
columns to reduce the risk of data breaches.
## 1st tool - Analyze reports shared with the entire organization
This tool includes a Python script that interacts with the Power BI API. It sends requests to get the list of all reports shared with the entire organization and analyzes them to find any unused data sources.

### Scripts
The script runner must have Fabric Admin (or Global Admin) permissions, the minimum permission required to interact with the Power BI Admin API.

- `power_bi_get_report_used_and_consume_data.py`: This script fetches and analyzes data from Power BI reports that are shared within an organization. It uses an access token for authentication and interacts with the Power BI API.

### Usage

The script requires the name of the output CSV file as a command-line argument.


Example usage:

```bash
python power_bi_get_report_used_and_consume_data.py --output-csv-filename output.csv
```

### Output
CSV file containing the following columns:
* Report ID
* Number of hidden columns
* All columns
* Unused columns

## 2nd tool - Analyze reports that are shared to the web
This tool includes a Python script that gets a CSV file with a list of all the URLs of reports published to the web and analyzes them to find any unused data sources.

### Scripts
The script's runner does not require any permissions or credentials. However, before execution, a Power BI admin needs to export a list of embed codes in your organization.

- `power_bi_find_columns_in_reports.py`: This script analyzes data sources of Power BI reports that are shared to the web.

### requirements
To execute this script, a Power BI admin must export a CSV file with all your organization's "Embed Codes."
This CSV contains a list of reports published to the web with their: name, workspace, publisher, status, and public URL
of the report. To export the CSV, use the following link: https://app.powerbi.com/admin-portal/embedCodes and press
'Export' Or navigate in the Power BI UI to 'Settings' -> 'Admin Portal' -> 'Embed Codes' -> 'Export.'
### Usage

The script requires the name of the output CSV file as a command-line argument and the full path to the Embed Codes CSV file.

Example usage:

```bash
python power_bi_find_columns_in_reports.py --exported-embed-codes-table "C:\Users\MyUserName\Downloads\Embed Codes.csv" --output-csv-filename "C:\Users\MyUserName\Downloads\output.csv"
```

### Output
CSV file containing the following columns:
* Report name 
* Workspace name
* Published by
* Status
* Embed URL
* Number of hidden columns
* All columns
* Unused columns