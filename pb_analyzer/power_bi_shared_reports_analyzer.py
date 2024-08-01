import argparse
import json
import os
from datetime import datetime
from urllib.parse import urlparse

import msal
import requests
from alive_progress import alive_bar
from colorama import Fore

from pb_analyzer.BaseAnalyzer import BaseAnalyzer
from pb_analyzer.const import Requests, ResponseKeys, SHARED_TO_ORG_HEADERS
from pb_analyzer.utils import count_hidden_true_in_dict, fetch_columns_and_tables, get_classified_columns, \
    write_to_csv


class SharedReportsAnalyzer(BaseAnalyzer):
    def __init__(self, results_output_path: str = None, summary_output_path: str = None,
                 debug: bool = False):
        """

        Args:
            results_output_path: The path to the output CSV file.
            summary_output_path: The path to the summary TXT file.

        Example usage:
        SharedToWholeOrganizationAnalyzer('C:/Users/username/Downloads/Output.csv', 'C:/Users/username/Downloads/Results.txt').analyze()
        """
        time = int(round(datetime.now().timestamp()))
        is_default_result_path = True
        if results_output_path:
            if not results_output_path.endswith('.csv'):
                raise ValueError('Output file must be a CSV file.')
            is_default_result_path = False
        else:
            results_output_path = os.path.join(os.path.dirname(__file__), f'SharedReportsWithUnusedData_{time}.csv')

        is_default_summary_path = True
        if summary_output_path:
            if not summary_output_path.endswith('.txt'):
                raise ValueError('Output file must be a TXT file.')
            is_default_summary_path = False
        else:
            summary_output_path = os.path.join(os.path.dirname(__file__), f'PBAnalyzerResults_{time}.txt')

        self._debug = debug
        super().__init__('Reports shared to whole organization analyzer', results_output_path, is_default_result_path,
                         summary_output_path, is_default_summary_path)

    @staticmethod
    def _extract_artifact_ids(response: dict):
        artifact_ids = [
            (entity[ResponseKeys.ARTIFACT_ID], entity.get(ResponseKeys.SHARER).get(ResponseKeys.DISPLAY_NAME),
             entity.get(ResponseKeys.DISPLAY_NAME)
             ) for entity in
            response.get(ResponseKeys.ARTIFACT_ACCESS_ENTITIES, [])]
        return artifact_ids

    @staticmethod
    def _get_token():
        """
        Acquires an access token using the Microsoft Authentication Library (MSAL).
        """
        app = msal.PublicClientApplication(Requests.CLIENT_ID, authority=Requests.AUTHORITY)
        result = app.acquire_token_interactive(scopes=Requests.SCOPE)

        if ResponseKeys.ACCESS_TOKEN in result:
            return result[ResponseKeys.ACCESS_TOKEN]
        else:
            raise Exception("Failed to acquire token: %s" % result.get("error_description"))

    @staticmethod
    def _reports_published_to_web_api(token: str):
        headers = {'authorization': f'Bearer {token}'}
        response = requests.get(Requests.PUBLISHED_TO_WEB_URL, headers=headers)

        if response.status_code == 200:
            response_data = response.json()
            return response_data
        else:
            return None

    @staticmethod
    def _links_shared_to_whole_organization_api(token: str):
        headers = {'authorization': f'Bearer {token}'}
        response = requests.get(Requests.SHARED_TO_ORG_URL, headers=headers)

        if response.status_code == 200:
            response_data = response.json()
            return response_data
        else:
            return None

    @staticmethod
    def _send_push_access_request(token: str, report_id: str, region: str):
        headers = {'authorization': f'Bearer {token}'}
        response = requests.post(Requests.PUSH_ACCESS_URL.format(region, report_id), headers=headers)

        if response.status_code == 200:
            response_data = response.json()
            return response_data
        else:
            return None

    @staticmethod
    def _send_exploration_request(token: str, artifact_id: str, region: str):
        headers = {'authorization': f'Bearer {token}'}
        response = requests.get(Requests.EXPLORATION_URL.format(region, artifact_id), headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f'Failed to send exploration request. Status code: {response.status_code}')

    @staticmethod
    def _send_conceptual_schema_request(token: str, model_id: str, region: str):
        headers = {'authorization': f'Bearer {token}', 'content-type': 'application/json; charset=UTF-8'}
        data = {"modelIds": [model_id], "userPreferredLocale": "en-US"}
        response = requests.post(Requests.CONCEPTUAL_SCHEMA_URL.format(region), headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f'Failed to send conceptual schema request. Status code: {response.status_code}')

    @staticmethod
    def _extract_region(response: dict):
        url = urlparse(response.get(ResponseKeys.REGION))
        return url.netloc

    def _run_analysis(self, region, reports, token):
        success_count = 0
        with alive_bar(len(reports)) as bar:
            start_time = datetime.now()
            for report_id, sharer_name, name in reports:
                try:
                    response_data = self._send_push_access_request(token, report_id, region)
                    if response_data:
                        conceptual_schema, exploration_response = self._get_report_data(region, response_data, token)
                        num_of_hidden = count_hidden_true_in_dict(conceptual_schema)
                        columns_and_tables = fetch_columns_and_tables(conceptual_schema)
                        unused_message, all_columns = get_classified_columns(columns_and_tables, exploration_response)
                        self._insert_all_columns(all_columns, num_of_hidden)
                        if unused_message:
                            self._reports_with_unused_columns += 1
                            write_to_csv(self.result_output_path,
                                         [report_id, name, sharer_name, num_of_hidden, unused_message])
                        success_count += 1
                except Exception as e:
                    if self._debug:
                        print(Fore.RED + str(e))
                bar()
            end_time = datetime.now()
        return end_time, reports, start_time, success_count

    def _intro(self):
        self._handle_input()
        print(
            Fore.CYAN + 'This tool will analyze reports shared to the whole organization. You will need to sign in to '
                        'your Power BI account to proceed.')
        input(Fore.CYAN + 'Press Enter to start the analysis process..')
        token = self._get_token()
        all_shared_res = self._links_shared_to_whole_organization_api(token)
        reports = self._extract_artifact_ids(all_shared_res)
        region = self._extract_region(all_shared_res)
        write_to_csv(self.result_output_path, SHARED_TO_ORG_HEADERS, True)
        average_time_per_report = 3
        estimated_time = len(reports) * average_time_per_report
        print(Fore.GREEN + f'Found {len(reports)} reports shared to whole organization.')
        print(Fore.YELLOW + f'Estimated time to analyze all reports: {estimated_time} seconds.')
        return region, reports, token

    def _get_report_data(self, region, response_data, token):
        artifact_id = response_data['entityKey']['id']
        model_id = next(item['id'] for item in response_data['relatedEntityKeys'] if item['type'] == 4)
        conceptual_schema = self._send_conceptual_schema_request(token, model_id, region)
        exploration_response = self._send_exploration_request(token, artifact_id, region)
        return conceptual_schema, exploration_response

    def analyze(self):
        try:
            self.welcome_text()
            region, reports, token = self._intro()
            end_time, reports, start_time, success_count = (
                self._run_analysis(region, reports, token))
            self.outro(end_time, reports, start_time, success_count)
        except Exception as e:
            print(Fore.RED + 'Exiting due to an error.')
            if self._debug:
                raise

