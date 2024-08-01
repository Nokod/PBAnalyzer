import argparse
import base64
import csv
import json
import os
import re
from datetime import datetime
from typing import List, Optional, Dict, Union
from urllib.parse import urlparse, parse_qs, ParseResult

import requests
from alive_progress import alive_bar
from colorama import Fore

from pb_analyzer.BaseAnalyzer import BaseAnalyzer
from pb_analyzer.const import PublicRequests, REGEX_BI_REQUEST, NEW_HEADERS
from pb_analyzer.utils import count_hidden_true_in_dict, get_classified_columns, \
    write_to_csv, fetch_columns_and_tables


class PublicReportsAnalyzer(BaseAnalyzer):
    def __init__(self, embed_codes_path: str, results_output_path: str = None, summary_output_path: str = None,
                 debug: bool = False):
        """
        Args:
            embed_codes_path:  The full path to the Power BI Reports CSV file.
            results_output_path:  The path to the output CSV file.
            summary_output_path:  The path to the summary TXT file.

        Example usage:
        PublicReportAnalyzer('C:/Users/username/Downloads/PowerBIReports.csv', 'C:/Users/username/Downloads/Output.csv').analyze()
        """

        time = int(round(datetime.now().timestamp()))
        self.csv_file_path = embed_codes_path
        is_default_results_path = True
        if results_output_path:
            if not results_output_path.endswith('.csv'):
                raise ValueError('Output file must be a CSV file.')
            is_default_results_path = False
        else:
            results_output_path = os.path.join(os.path.dirname(__file__), f'SharedReportsWithUnusedData_{time}.csv')

        is_default_summary_path = True
        if summary_output_path:
            if not summary_output_path.endswith('.txt'):
                raise ValueError('Output file must be a TXT file.')
            self.is_default_result_path = False
        else:
            summary_output_path = os.path.join(os.path.dirname(__file__), f'PBAnalyzerResults_{time}.txt')

        super().__init__('Analyze Reports Shared with the Entire Organization', results_output_path,
                         is_default_results_path, summary_output_path, is_default_summary_path)
        self._all_columns = []
        self._reports_with_unused_columns = 0
        self._reports_with_hidden_columns = 0
        self._debug = debug

    @staticmethod
    def _send_power_bi_request(url: str) -> Optional[str]:
        response: requests.Response = requests.get(url)
        if response.status_code == 200:
            match: Optional[re.Match] = re.search(REGEX_BI_REQUEST, response.text)
            if match:
                return match.group(1)
            else:
                return None
        else:
            return None

    @staticmethod
    def _send_exploration_request(region_url: str, resource_key: str) -> Optional[Dict]:
        headers: Dict[str, str] = {'X-PowerBI-ResourceKey': resource_key}
        response: requests.Response = requests.get(
            PublicRequests.EXPLORATION_URL.format(region_url, resource_key),
            headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            return None

    @staticmethod
    def _get_model_id(json_response: Union[str, Dict]) -> Optional[str]:
        try:
            data: Dict = json.loads(json_response) if isinstance(json_response, str) else json_response
            models: List[Dict] = data.get('models', [])
            if models:
                return models[0].get('id')
            else:
                return None
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
            return None

    @staticmethod
    def _decode_url(encoded_url: str) -> dict:
        parsed_url: ParseResult = urlparse(encoded_url)
        encoded_bytes: str = parse_qs(parsed_url.query)['r'][0]
        decoded_bytes: bytes = base64.b64decode(encoded_bytes)
        decoded_url: str = decoded_bytes.decode('utf-8')
        return json.loads(decoded_url)

    def _run_analysis(self, rows):
        start_time = datetime.now()
        success_count = 0
        with alive_bar(len(rows), bar='blocks') as bar:
            for row in rows:
                try:
                    conceptual_schema, exploration_response = self._get_report_data(row)
                    report_columns = fetch_columns_and_tables(conceptual_schema)
                    num_of_hidden = count_hidden_true_in_dict(conceptual_schema)
                    unused_message, all_columns = get_classified_columns(report_columns, exploration_response)
                    self._insert_all_columns(all_columns, num_of_hidden)
                    if unused_message:
                        self._reports_with_unused_columns += 1
                        write_to_csv(self.result_output_path, row[:-1] + [num_of_hidden, unused_message])
                    success_count += 1
                except Exception as e:
                    if self._debug:
                        print(Fore.RED + f'Failed to analyze report: {row[1]}. Error: {str(e)}')
                bar()
            end_time = datetime.now()
        return end_time, rows, start_time, success_count

    def _intro(self):
        self._handle_input()
        rows = []
        with open(self.csv_file_path, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            headers = next(reader)
            [rows.append(row) for row in reader]
        write_to_csv(self.result_output_path, headers + NEW_HEADERS, True)
        average_time_per_report = 1.5
        estimated_time = len(rows) * average_time_per_report
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
            self.welcome_text()
            rows = self._intro()
            end_time, rows, start_time, success_count = self._run_analysis(rows)
            self.outro(end_time, rows, start_time, success_count)
        except Exception as e:
            print(Fore.RED + 'Exiting due to an error.')
            if self._debug:
                print(Fore.RED + str(e))
