import argparse
import base64
import csv
import json
import re
from typing import List, Optional, Dict, Union
from urllib.parse import urlparse, parse_qs, ParseResult

import requests


def write_to_csv(file_path: str, values: List[str], overwrite: bool = False) -> None:
    """
    Writes values to a CSV file.

    Args:
        file_path (str): The path to the CSV file.
        values (List[str]): The values to write to the CSV file.
        overwrite (bool): Whether to overwrite the file or append to it. Default is False.
    """
    mode: str = 'w' if overwrite else 'a'
    with open(file_path, mode=mode, newline='', encoding='utf-8') as file:
        writer: csv.writer = csv.writer(file)
        writer.writerow(values)


def send_power_bi_request(url: str) -> Optional[str]:
    """
    Sends a request to the Power BI service and extracts the resolved cluster URI.

    Args:
        url (str): The URL to send the request to.

    Returns:
        Optional[str]: The resolved cluster URI if found, None otherwise.
    """
    response: requests.Response = requests.get(url)
    if response.status_code == 200:
        print("Request was successful!")
        match: Optional[re.Match] = re.search(r"var resolvedClusterUri = '(.*?)';", response.text)
        if match:
            return match.group(1)
        else:
            print("resolvedClusterUri not found in the response.")
            return None
    else:
        print(f"Request failed with status code: {response.status_code}")
        return None


def send_exploration_request(region_url: str, resourceKey: str) -> Optional[Dict]:
    """
    Sends an exploration request to the Power BI service.

    Args:
        region_url (str): The base URL for the Power BI service.
        resourceKey (str): The resource key for the report.

    Returns:
        Optional[Dict]: The JSON response if the request was successful, None otherwise.
    """
    url: str = f'{region_url}public/reports/{resourceKey}/modelsAndExploration?preferReadOnlySession=true'
    headers: Dict[str, str] = {'X-PowerBI-ResourceKey': resourceKey}
    response: requests.Response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print('Exploration request was successful.')
        return response.json()
    else:
        print(f'Failed to send exploration request. Status code: {response.status_code}')
        print('Response:', response.text)
        return None


def get_model_id(json_response: Union[str, Dict]) -> Optional[str]:
    """
    Extracts and returns the model ID from a given JSON response.

    Args:
        json_response (Union[str, Dict]): A string containing the JSON response or a dictionary.

    Returns:
        Optional[str]: The model ID if found, otherwise None.
    """
    try:
        data: Dict = json.loads(json_response) if isinstance(json_response, str) else json_response
        models: List[Dict] = data.get('models', [])
        if models:
            return models[0].get('id')
        else:
            return None
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"An error occurred: {e}")
        return None


def count_hidden_true_in_dict(response: Dict) -> int:
    """
    Counts the number of occurrences of the key-value pair "'Hidden': True" in the given dictionary response,
    ignoring entities where the name starts with 'DateTableTemplate'.

    Args:
        response (Dict): The API response as a dictionary.

    Returns:
        int: The number of occurrences of "'Hidden': True" in the response, excluding entities named 'DateTableTemplate*'.
    """

    def recursive_count(data: Union[Dict, List], skip_entity: bool = False) -> int:
        count: int = 0
        if isinstance(data, dict):
            for key, value in data.items():
                if key == 'Name' and isinstance(value, str) and value.startswith('DateTableTemplate'):
                    skip_entity = True
                if key == 'Hidden' and value is True and not skip_entity:
                    count += 1
                count += recursive_count(value, skip_entity)
        elif isinstance(data, list):
            for item in data:
                count += recursive_count(item, skip_entity)
        return count

    return recursive_count(response)


def send_conceptual_schema_request(region_url: str, model_id: str, resource_key: str) -> Optional[Dict]:
    """
    Sends a request to retrieve the conceptual schema for a given model ID.

    Args:
        region_url (str): The base URL for the Power BI service.
        model_id (str): The model ID to retrieve the schema for.
        resource_key (str): The resource key for the report.

    Returns:
        Optional[Dict]: The JSON response if the request was successful, None otherwise.
    """
    url: str = f'{region_url}public/reports/conceptualschema'
    headers: Dict[str, str] = {'X-PowerBI-ResourceKey': resource_key}
    payload: Dict[str, List[str]] = {'modelIds': [model_id]}
    response: requests.Response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()
        return None


def extract_tables_and_columns(response: dict) -> List[str]:
    """
    Extracts tables and columns from the given response.

    Args:
        response (dict): The response from which to extract tables and columns.

    Returns:
        List[str]: A list of strings, each representing a table and column in the format "TableName.ColumnName".
    """
    tables_and_columns: List[str] = []

    for schema in response.get('schemas', []):
        for entity in schema.get('schema', {}).get('Entities', []):
            table_name: str = entity.get('Name', 'UnknownTable')
            for prop in entity.get('Properties', []):
                column_name: str = prop.get('Name', 'UnknownColumn')
                tables_and_columns.append(f"{table_name}.{column_name}")

    return tables_and_columns


def filter_strings_not_in_json(strings_list: List[str], json_string: dict) -> List[str]:
    """
    Filters out strings from the list that are not found in the JSON string.

    Args:
        strings_list (List[str]): The list of strings to filter.
        json_string (dict): The JSON string to check against.

    Returns:
        List[str]: A list of strings that are not found in the JSON string.
    """
    json_str: str = json.dumps(json_string)
    normalized_json_string: str = json_str.replace('"', '').replace("'", '')

    return [string for string in strings_list if string not in normalized_json_string]


def decode_url(encoded_url: str) -> dict:
    """
    Decodes a base64-encoded URL and returns the decoded URL as a dictionary.

    Args:
        encoded_url (str): The base64-encoded URL.

    Returns:
        dict: The decoded URL as a dictionary.
    """
    parsed_url: ParseResult = urlparse(encoded_url)
    encoded_bytes: str = parse_qs(parsed_url.query)['r'][0]
    decoded_bytes: bytes = base64.b64decode(encoded_bytes)
    decoded_url: str = decoded_bytes.decode('utf-8')
    return json.loads(decoded_url)


def main(csv_file_path: str, output_file_path: str):
    rows = []
    with open(csv_file_path, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        headers = next(reader)
        for row in reader:
            rows.append(row)

    write_to_csv(output_file_path, headers + ['# of hidden columns', 'All columns', 'Unused columns'],
                 True)
    for row in rows:
        try:
            region_url = send_power_bi_request(row[4])
            region_url = region_url.replace('redirect', 'api')
            decoded_url = decode_url(row[4])
            response_data = send_exploration_request(region_url, decoded_url['k'])
            model_id = get_model_id(response_data)
            conceptual_schema = send_conceptual_schema_request(region_url, model_id, decoded_url['k'])
            columns_and_tables_list = extract_tables_and_columns(conceptual_schema)
            num_of_hidden = count_hidden_true_in_dict(conceptual_schema)
            unused_column = filter_strings_not_in_json(columns_and_tables_list, response_data)
            write_to_csv(output_file_path,
                         row[:-1] + [num_of_hidden, columns_and_tables_list, unused_column])
        except Exception as e:
            print(f"An error occurred: {e}")
            write_to_csv(output_file_path, row[:-1] + ['', '', ''])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--exported-power-bi-reports", help="The path to the Power BI reports summary CSV file.")
    parser.add_argument("--output-file-path", help="The path to the output CSV file.")
    args = parser.parse_args()
    try:
        main(args.exported_power_bi_reports, args.output_file_path)
    except Exception as e:
        print(f"Failed to process the Power BI reports: {e}")
