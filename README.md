# Power BI Analyzer

This project contains two tools for finding unused data sources in your Power BI (Microsoft Fabric) reports.
These tools analyze the reports' data models and identify columns not used in visualizations.
Unwanted access to this data can pose a __security risk__, and it is essential to identify and remove unused
columns to reduce the risk of data breaches.

BACKGROUND:
On June 19, 2024, Nokod Security published a warning about the easy exploitation of a data leakage vulnerability in the Microsoft Power BI service. This vulnerability potentially affects tens of thousands of organizations and allows anonymous Internet viewers to access sensitive data, including employee and business data, PHI, and PII. For details about the exploit see: https://nokodsecurity.com/blog/in-plain-sight-how-microsoft-power-bi-reports-expose-sensitive-data-on-the-web/

Nokod Security created the “Power BI Analyzer,” as a simple and free tool for organizations to assess their exposure to this vulnerability. 
If you need help with this tool, please contact amichai@nokodsecurity.com or uriya@nokodsecurity.com.

# Installation
To install the package, run the following command:

```bash
pip install power-bi-analyzer
```

## 1st tool - Analyze reports shared with the entire organization
This tool includes a Python module that interacts with the Power BI API. It sends requests to get the list of all reports shared with the entire organization and analyzes them to find any unused data sources.

### Scripts
The script runner must have Fabric Admin (or Global Admin) permissions, the minimum permission required to interact with the Power BI Admin API.

- `SharedReportsAnalyzer`: This module fetches and analyzes data from Power BI reports that are shared within an organization. It uses an access token for authentication and interacts with the Power BI API.

### Usage
You may provide the name of the output CSV file and the summary file as arguments, but they are optional. If you do not provide them, the script will create them in the same directory.

Example usage:

```bash
shared-reports-analyzer --output-folder "path/to/output folder"
```

### Output
CSV file containing the following columns:
* Report ID
* Report name
* Shared by
* Number of hidden columns
* Unused columns

## 2nd tool - Analyze reports that are shared to the web
This tool includes a Python module that gets a CSV file with a list of all the URLs of reports published to the web and analyzes them to find any unused data sources.

### Scripts
The script's runner does not require any permissions or credentials. However, before execution, a Power BI admin needs to export a list of embed codes in your organization.

- `PublicReportsAnalyzer`: This module analyzes data sources of Power BI reports that are shared to the web.

### requirements
To execute this script, a Power BI admin must export a CSV file with all your organization's "Embed Codes."
This CSV contains a list of reports published to the web with their: name, workspace, publisher, status, and public URL
of the report. To export the CSV, use the following link: https://app.powerbi.com/admin-portal/embedCodes and press
'Export' Or navigate in the Power BI UI to 'Settings' -> 'Admin Portal' -> 'Embed Codes' -> 'Export.'
### Usage
The script requires the full path to the Embed Codes CSV file as an argument. You may also provide the name of the output CSV file and the summary file as arguments but 
they are optional. If you do not provide them, the script will create them in the same directory.

Example usage:

```bash
public-reports-analyzer --embed-codes-path "path/to/embed code.csv" --output-folder "path/to/output folder"
```

### Output
CSV file containing the following columns:
* Report name
* Workspace name
* Published by
* Status
* Embed URL
* Number of hidden columns
* Unused columns
