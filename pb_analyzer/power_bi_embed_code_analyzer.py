import argparse
import base64
import csv
import json
import re
from typing import List, Optional, Dict, Union
from urllib.parse import urlparse, parse_qs, ParseResult

import requests

from pb_analyzer.utils import count_hidden_true_in_dict, filter_strings_not_in_json, \
    write_to_csv, fetch_columns_and_tables

NEW_HEADERS = ['# of hidden columns', 'All columns', 'Unused columns']
REGEX_BI_REQUEST = r"var resolvedClusterUri = '(.*?)';"


class EmbedCodeAnalyzer:
    def __init__(self, embed_codes_path: str, output_file_path: str):
        """
        Args:
            embed_codes_path:  The full path to the Power BI Reports CSV file.
            output_file_path:  The path to the output CSV file.
        """
        self.csv_file_path = embed_codes_path
        self.output_file_path = output_file_path

    @staticmethod
    def _send_power_bi_request(url: str) -> Optional[str]:
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
            match: Optional[re.Match] = re.search(REGEX_BI_REQUEST, response.text)
            if match:
                return match.group(1)
            else:
                print("resolvedClusterUri not found in the response.")
                return None
        else:
            print(f"Request failed with status code: {response.status_code}")
            return None

    @staticmethod
    def _send_exploration_request(region_url: str, resource_key: str) -> Optional[Dict]:
        """
        Sends an exploration request to the Power BI service.

        Args:
            region_url (str): The base URL for the Power BI service.
            resource_key (str): The resource key for the report.

        Returns:
            Optional[Dict]: The JSON response if the request was successful, None otherwise.
        """
        url: str = f'{region_url}public/reports/{resource_key}/modelsAndExploration?preferReadOnlySession=true'
        headers: Dict[str, str] = {'X-PowerBI-ResourceKey': resource_key}
        response: requests.Response = requests.get(url, headers=headers)
        if response.status_code == 200:
            print('Exploration request was successful.')
            return response.json()
        else:
            print(f'Failed to send exploration request. Status code: {response.status_code}')
            print('Response:', response.text)
            return None

    @staticmethod
    def _get_model_id(json_response: Union[str, Dict]) -> Optional[str]:
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

    @staticmethod
    def _send_conceptual_schema_request(region_url: str, model_id: str, resource_key: str) -> Optional[Dict]:
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

    @staticmethod
    def _decode_url(encoded_url: str) -> dict:
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

    def analyze(self):
        rows = []
        with open(self.csv_file_path, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            headers = next(reader)
            for row in reader:
                rows.append(row)

        write_to_csv(self.output_file_path, headers + NEW_HEADERS,
                     True)
        for row in rows:
            try:
                region_url = self._send_power_bi_request(row[4])
                region_url = region_url.replace('redirect', 'api')
                decoded_url = self._decode_url(row[4])
                exploration_response = self._send_exploration_request(region_url, decoded_url['k'])
                model_id = self._get_model_id(exploration_response)
                conceptual_schema = self._send_conceptual_schema_request(region_url, model_id, decoded_url['k'])
                columns_and_tables_list = fetch_columns_and_tables(conceptual_schema)
                num_of_hidden = count_hidden_true_in_dict(conceptual_schema)
                unused_column = filter_strings_not_in_json(columns_and_tables_list, exploration_response)
                write_to_csv(self.output_file_path,
                             row[:-1] + [num_of_hidden, columns_and_tables_list, unused_column])
            except Exception as e:
                print(f"An error occurred: {e}")
                write_to_csv(self.output_file_path, row[:-1] + ['', '', ''])
