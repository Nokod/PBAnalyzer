import argparse
import json
from urllib.parse import urlparse

import msal
import requests

from pb_analyzer.utils import filter_strings_not_in_json, write_to_csv, count_hidden_true_in_dict


def extract_artifact_ids(response: dict):
    """
    Extracts the artifactId values from the given API response.

    Args:
        response (dict): The API response in dictionary format.
    """
    artifact_ids = [entity['artifactId'] for entity in response.get('ArtifactAccessEntities', [])]
    return artifact_ids


def get_token():
    """
    Acquires an access token using the Microsoft Authentication Library (MSAL).
    """
    authority = "https://login.microsoftonline.com/common"

    client_id = "23d8f6bd-1eb0-4cc2-a08c-7bf525c67bcd"
    scope = ['https://analysis.windows.net/powerbi/api/.default openid profile offline_access']

    app = msal.PublicClientApplication(client_id, authority='https://login.microsoftonline.com/common')
    result = app.acquire_token_interactive(scopes=scope)

    if "access_token" in result:
        return result["access_token"]
    else:
        raise Exception("Failed to acquire token: %s" % result.get("error_description"))


def links_shared_to_whole_organization_api(token: str):
    """
    Sends a GET request to the Power BI API to retrieve the list of widely shared artifacts.

    Args:
        token (str): The access token to use for authentication.

    """
    url = f'https://api.powerbi.com/v1.0/myorg/admin/widelySharedArtifacts/linksSharedToWholeOrganization'
    headers = {'authorization': f'Bearer {token}'}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print('Request was successful.')
        response_data = response.json()
        return response_data
    else:
        print(f'Failed to send request. Status code: {response.status_code}')
        print('Response:', response.text)
        return None


def send_push_access_request(token: str, report_id: str, region: str):
    """
    Sends a POST request to the Power BI API to push access to a report.

    Args:
        token (str): The access token to use for authentication.
        report_id (str): The ID of the report to push access to.
        region (str): The region to use for the request.

    """
    url = f'https://{region}/metadata/access/reports/{report_id}/pushaccess?forceRefreshGroups=true'

    headers = {'authorization': f'Bearer {token}'}
    response = requests.post(url, headers=headers)

    if response.status_code == 200:
        print('Request was successful.')
        response_data = response.json()
        return response_data
    else:
        print(f'Failed to send request. Status code: {response.status_code}')
        print('Response:', response.text)
        return None


def send_exploration_request(token: str, artifact_id: str, region: str):
    """
    Sends an exploration request to the Power BI API and returns the response.

    Args:
        token (str): The access token to use for authentication.
        artifact_id (str): The ID of the artifact to explore.
        region (str): The region to use for the request.
    """
    url = f'https://{region}/explore/reports/{artifact_id}/exploration'
    headers = {'authorization': f'Bearer {token}'}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print('Exploration request was successful.')
        return response.json()
    else:
        print(f'Failed to send exploration request. Status code: {response.status_code}')
        print('Response:', response.text)


def send_conceptual_schema_request(token: str, model_id: str, region: str):
    """
    Sends a POST request to the Power BI API to retrieve the conceptual schema of a model.

    Args:
        token (str): The access token to use for authentication.
        model_id (str): The ID of the model to retrieve the conceptual schema for.
        region (str): The region to use for the request.
    """
    url = f'https://{region}/explore/conceptualschema'
    headers = {
        'authorization': f'Bearer {token}',
        'content-type': 'application/json; charset=UTF-8',
    }

    data = {
        "modelIds": [model_id],
        "userPreferredLocale": "en-US"
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        print('Conceptual schema request was successful.')
        return response.json()
    else:
        print(f'Failed to send conceptual schema request. Status code: {response.status_code}')
        print('Response:', response.text)


def extract_tables_and_columns(response: dict):
    """
    Extracts the tables and columns from the conceptual schema response.

    Args:
        response (dict): The conceptual schema response as a dictionary.

    """
    tables_and_columns = []

    for schema in response.get('schemas', []):
        for entity in schema.get('schema', {}).get('Entities', []):
            table_name = entity.get('Name', 'UnknownTable')
            for prop in entity.get('Properties', []):
                column_name = prop.get('Name', 'UnknownColumn')
                tables_and_columns.append(f"{table_name}.{column_name}")

    return tables_and_columns


def fetch_columns_and_tables(conceptual_schema: dict):
    """
    Extracts and filters the tables and columns from the conceptual schema response.

    Parameters:
    conceptual_schema (dict): The conceptual schema response as a dictionary.
    """
    extracted_cols_and_tables = extract_tables_and_columns(conceptual_schema)
    filtered_cols_and_tables = [item for item in extracted_cols_and_tables if
                                "DateTableTemplate" not in item and "LocalDateTable" not in item]
    return filtered_cols_and_tables

def extract_region(response: dict):
    """
    Extracts the region from the given API response.

    Args:
        response (dict): The API response in dictionary format.
    """
    url = urlparse(response.get('@odata.context'))
    return url.netloc


def main(output_path: str):
    token = get_token()
    all_shared_res = links_shared_to_whole_organization_api(token)

    report_list = extract_artifact_ids(all_shared_res)
    region = extract_region(all_shared_res)

    write_to_csv(output_path, 'Report ID', 'Number of hidden columns', ['All columns'], ['Unused columns'], True)
    for reportID in report_list:
        response_data = send_push_access_request(token, reportID, region)
        if response_data:
            artifact_id = response_data['entityKey']['id']
            model_id = next(item['id'] for item in response_data['relatedEntityKeys'] if item['type'] == 4)
            print(f'Extracted artifact_id: {artifact_id}, model_id: {model_id}')
            conceptual_schema = send_conceptual_schema_request(token, model_id, region)
            num_of_hidden = count_hidden_true_in_dict(conceptual_schema)
            print("There are " + str(num_of_hidden) + " Hidden column in this report")
            exploration_query = send_exploration_request(token, artifact_id, region)
            columns_and_tables = fetch_columns_and_tables(conceptual_schema)
            unused_column = filter_strings_not_in_json(columns_and_tables, exploration_query)
            write_to_csv(output_path, reportID, str(num_of_hidden), columns_and_tables, unused_column)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-csv-filename", required=True, type=str, help="The name of the output CSV file.")
    args = parser.parse_args()

    main(args.output_csv_filename)
