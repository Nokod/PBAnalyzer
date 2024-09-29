import argparse
import base64
import csv
import json
import os
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Union
from urllib.parse import urlparse, parse_qs, ParseResult

import requests
from colorama import Fore

from pb_analyzer.base_analyzer import BaseAnalyzer
from pb_analyzer.const import PublicRequests, REGEX_BI_REQUEST, NEW_HEADERS, ResponseKeys, ExplorationRequestError
from pb_analyzer.utils import count_hidden_true_in_dict, get_classified_columns, \
    write_to_csv, fetch_columns_and_tables


class PublicReportsAnalyzer(BaseAnalyzer):
    def __init__(self, embed_codes_file_path: str, output_folder: str = None, debug: bool = False):
        """
        Args:
            embed_codes_file_path:  The full path to the Power BI Reports CSV file.
            output_folder: The path to the output folder.

        Example usage:
        PublicReportAnalyzer('C:/Users/username/Downloads/PowerBIReports.csv', 'C:/Users/username/Downloads/Output.csv').analyze()
        """
        time = int(round(datetime.now().timestamp()))
        try:
            self._validate_embed_codes_file(embed_codes_file_path)
        except (FileNotFoundError, ValueError) as e:
            print(Fore.RED + str(e))
            exit(1)
        self._embed_codes_file_path = embed_codes_file_path
        is_default_results_path = True

        results_output_path = os.path.join(os.getcwd(), f'PublicReportsWithUnusedData_{time}.csv')
        summary_output_path = os.path.join(os.getcwd(), f'PBAnalyzerResults_{time}.txt')

        if output_folder:
            if '.' in os.path.basename(output_folder):
                print(Fore.RED + 'Invalid output folder path. Using default path.')
            if not os.path.isdir(output_folder):
                os.makedirs(output_folder)
            is_default_results_path = False
            results_output_path = os.path.join(output_folder, f'PublicReportsWithUnusedData_{time}.csv')
            summary_output_path = os.path.join(output_folder, f'PBAnalyzerResults_{time}.txt')

        super().__init__('Analyze Public Reports', results_output_path,
                         is_default_results_path, summary_output_path, debug)

    @staticmethod
    def _validate_embed_codes_file(embed_codes_path: str):
        if not os.path.isfile(embed_codes_path):
            raise FileNotFoundError(f'File not found: {embed_codes_path}')

        if not embed_codes_path.lower().endswith('.csv'):
            raise ValueError(f'File must be a CSV: {embed_codes_path}')

        expected_headers = ['Report name', 'Workspace name', 'Published by', 'Status', 'Embed URL']

        with open(embed_codes_path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.reader(file)
            headers = next(reader, None)

            if headers != expected_headers:
                raise ValueError(
                    f'CSV file does not have the expected headers. Are you sure this is an Embed Codes CSV file?')

    @staticmethod
    def _send_power_bi_request(url: str) -> Optional[str]:
        response: requests.Response = requests.get(url)
        if response.status_code == 200:
            match: Optional[re.Match] = re.search(REGEX_BI_REQUEST, response.text)
            if match:
                return match.group(1)

    @staticmethod
    def _send_exploration_request(region_url: str, resource_key: str) -> Optional[Dict]:
        headers: Dict[str, str] = {'X-PowerBI-ResourceKey': resource_key}
        response: requests.Response = requests.get(
            PublicRequests.EXPLORATION_URL.format(region_url, resource_key),
            headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise ExplorationRequestError(f'Failed to get exploration data. Status code: {response.status_code}',
                                          response.json()['error']['code'])

    @staticmethod
    def _get_model_id(json_response: Union[str, Dict]) -> Optional[str]:
        try:
            data: Dict = json.loads(json_response) if isinstance(json_response, str) else json_response
            models: List[Dict] = data.get(ResponseKeys.MODELS, [{}])
            if models:
                return models[0].get(ResponseKeys.ID)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            return None

    @staticmethod
    def _send_conceptual_schema_request(region_url: str, model_id: str, resource_key: str) -> Optional[Dict]:
        headers: Dict[str, str] = {'X-PowerBI-ResourceKey': resource_key}
        payload: Dict[str, List[str]] = {'modelIds': [model_id]}
        response: requests.Response = requests.post(PublicRequests.CONCEPTUAL_SCHEMA_URL.format(region_url),
                                                    headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()

    @staticmethod
    def _decode_url(encoded_url: str) -> dict:
        parsed_url: ParseResult = urlparse(encoded_url)
        encoded_bytes: str = parse_qs(parsed_url.query)['r'][0]
        decoded_bytes: bytes = base64.b64decode(encoded_bytes)
        decoded_url: str = decoded_bytes.decode('utf-8')
        return json.loads(decoded_url)

    def _process_report(self, row, bar, start_time, *args):
        try:
            if datetime.now() - start_time > timedelta(minutes=10):
                raise TimeoutError('Passes the 10 minutes mark.')

            conceptual_schema, exploration_response = self._get_report_data(row)
            report_columns = fetch_columns_and_tables(conceptual_schema)
            num_of_hidden = count_hidden_true_in_dict(conceptual_schema)
            report_with_unused, all_columns = get_classified_columns(report_columns, exploration_response)
            self._insert_all_columns(all_columns, num_of_hidden)
            self._success_count += 1
            if report_with_unused:
                self._reports_with_unused_columns += 1
                self._results.append(row[:-1] + [num_of_hidden, report_with_unused])
        except ExplorationRequestError as e:
            if self._debug:
                print(Fore.RED + str(e))
            self._errors.append([row[0], e.args[1]])
        except TimeoutError as e:
            raise e
        except Exception as e:
            if self._debug:
                print(Fore.RED + str(e))
        bar()
        return

    def _intro(self):
        self._handle_input()
        rows = []
        with open(self._embed_codes_file_path, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            headers = next(reader)
            [rows.append(row) for row in reader]
        write_to_csv(self._result_output_path, [headers + NEW_HEADERS], True)
        average_time_per_report = 0.4
        estimated_time = round(len(rows) * average_time_per_report, 2)
        print(Fore.GREEN + f'Found {len(rows)} reports to analyze.')
        print(Fore.YELLOW + f'Estimated time to analyze all reports: {estimated_time} seconds.')
        if estimated_time > 60 * 10:
            print(Fore.RED + f'Scan will stop after approximately 10 minutes.')
        input(Fore.CYAN + "Press Enter to start the analysis...")
        print()
        print(Fore.BLUE + 'Analyzing reports...')
        return rows

    def _get_report_data(self, row):
        region_url = self._send_power_bi_request(row[4])
        region_url = region_url.replace('redirect', 'api')
        decoded_url = self._decode_url(row[4])
        exploration_response = self._send_exploration_request(region_url, decoded_url['k'])
        model_id = self._get_model_id(exploration_response)
        conceptual_schema = self._send_conceptual_schema_request(region_url, model_id, decoded_url['k'])
        return conceptual_schema, exploration_response

    def analyze(self):
        try:
            self._welcome_text()
            rows = self._intro()
            end_time, rows, start_time = self._run_analysis(rows)
            self._outro(end_time, rows, start_time)
        except Exception as e:
            print(Fore.RED + 'Exiting due to an error.')
            if self._debug:
                print(Fore.RED + str(e))


def main():
    parser = argparse.ArgumentParser(description='Analyze Public Power BI Reports')
    parser.add_argument('--embed-codes-path', type=str, help='Path to the Power BI Reports CSV file', required=True)
    parser.add_argument('--output-folder', type=str, help='The path to the output folder')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()

    analyzer = PublicReportsAnalyzer(
        embed_codes_file_path=args.embed_codes_path,
        output_folder=args.output_folder,
        debug=args.debug
    )
    analyzer.analyze()
