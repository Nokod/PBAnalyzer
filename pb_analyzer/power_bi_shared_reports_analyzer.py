import argparse
import json
import os
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse

import msal
import requests
from colorama import Fore

from pb_analyzer.base_analyzer import BaseAnalyzer
from pb_analyzer.const import Requests, ResponseKeys, SHARED_TO_ORG_HEADERS
from pb_analyzer.utils import count_hidden_true_in_dict, fetch_columns_and_tables, get_classified_columns, \
    write_to_csv


class SharedReportsAnalyzer(BaseAnalyzer):
    def __init__(self, output_folder: str = None, debug: bool = False, extended_time_limit: bool = False):
        """

        Args:
            output_folder: The path to the output folder.
            debug: Enable debug mode.
            extended_time_limit: If True, extends the time limit from 10 minutes to 60 minutes.

        Example usage:
        SharedToWholeOrganizationAnalyzer('C:/Users/username/Downloads/Output.csv', 'C:/Users/username/Downloads/Results.txt').analyze()
        """
        self._time_limit_minutes = 60 if extended_time_limit else 10
        time = int(round(datetime.now().timestamp()))
        is_default_result_path = True

        results_output_path = os.path.join(os.getcwd(), f'SharedReportsWithUnusedData_{time}.csv')
        summary_output_path = os.path.join(os.getcwd(), f'PBAnalyzerResults_{time}.txt')

        if output_folder:
            if '.' in os.path.basename(output_folder):
                print(Fore.RED + 'Invalid output folder path. Using default path.')
            if not os.path.isdir(output_folder):
                os.makedirs(output_folder)
            is_default_result_path = False
            results_output_path = os.path.join(output_folder, f'SharedReportsWithUnusedData_{time}.csv')
            summary_output_path = os.path.join(output_folder, f'PBAnalyzerResults_{time}.txt')

        super().__init__('Reports shared to whole organization analyzer', results_output_path, is_default_result_path,
                         summary_output_path, debug)

    def _extract_artifact_ids(self, response: dict):
        try:
            artifact_ids = [
                (entity[ResponseKeys.ARTIFACT_ID],
                 entity.get(ResponseKeys.SHARER, {}).get(ResponseKeys.DISPLAY_NAME, {}),
                 entity.get(ResponseKeys.DISPLAY_NAME, {})
                 ) for entity in
                response.get(ResponseKeys.ARTIFACT_ACCESS_ENTITIES, [])]
            if not artifact_ids:
                raise Exception('No reports shared to whole organization found.')
            return artifact_ids
        except Exception as e:
            print(Fore.RED + 'Failed to extract artifact IDs.')
            if self._debug:
                print(Fore.RED + str(e))
                print(Fore.RED + 'response:', response)
            exit(1)

    @staticmethod
    def _get_token():
        """
        Acquires an access token using the Microsoft Authentication Library (MSAL).
        """
        app = msal.PublicClientApplication(Requests.CLIENT_ID, authority=Requests.AUTHORITY)
        result = app.acquire_token_interactive(scopes=Requests.SCOPE, prompt='login')

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

    def _links_shared_to_whole_organization_api(self, token: str):
        headers = {'authorization': f'Bearer {token}'}
        response = requests.get(Requests.SHARED_TO_ORG_URL, headers=headers)

        if response.status_code == 200:
            response_data = response.json()
            if self._debug:
                print(Fore.GREEN + 'Successfully fetched shared reports.')
            return response_data
        else:
            raise Exception(f'Failed to get shared reports. Status code: {response.status_code}', response.json())

    @staticmethod
    def _send_push_access_request(token: str, report_id: str, region: str):
        headers = {'authorization': f'Bearer {token}'}
        response = requests.post(Requests.PUSH_ACCESS_URL.format(region, report_id), headers=headers)

        if response.status_code == 200:
            response_data = response.json()
            return response_data

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
        max_retries = 5
        backoff_factor = 5

        for attempt in range(max_retries):
            response = requests.post(Requests.CONCEPTUAL_SCHEMA_URL.format(region), headers=headers,
                                     data=json.dumps(data))

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                message = response.json().get('message')
                if message and 'Retry in' in message:
                    wait_time = int(message.split('Retry in ')[1].split(' seconds')[0])
                    print(Fore.YELLOW + f'Rate limit exceeded. Retrying in {wait_time} seconds...')
                else:
                    wait_time = backoff_factor * (2 ** attempt)
                    print(Fore.YELLOW + f'Rate limit exceeded. Retrying in {wait_time} seconds...')
                time.sleep(wait_time)
            else:
                raise Exception(f'Failed to send conceptual schema request. Status code: {response.status_code}')

        raise Exception('Max retries exceeded for conceptual schema request.')

    def _extract_region(self, response: dict):
        try:
            url = urlparse(response.get(ResponseKeys.REGION))
            region = url.netloc
            if self._debug:
                print(Fore.GREEN + f'Extracted region: {region}')
            return region
        except Exception as e:
            print(Fore.RED + 'Failed to extract region.')
            if self._debug:
                print(Fore.RED + str(e))
            exit(1)

    def _process_report(self, report, bar, start_time, *args):
        region, token = args
        report_id, sharer_name, name = report
        try:
            if datetime.now() - start_time > timedelta(minutes=self._time_limit_minutes):
                print(Fore.RED + f'Passed the {self._time_limit_minutes} minutes mark. Stopped the analysis.')
                raise TimeoutError(f'Passed the {self._time_limit_minutes} minutes mark.')

            response_data = self._send_push_access_request(token, report_id, region)
            if response_data:
                conceptual_schema, exploration_response = self._get_report_data(region, response_data, token)
                num_of_hidden = count_hidden_true_in_dict(conceptual_schema)
                columns_and_tables = fetch_columns_and_tables(conceptual_schema)
                unused_message, all_columns = get_classified_columns(columns_and_tables, exploration_response)
                self._insert_all_columns(all_columns, num_of_hidden)
                self._success_count += 1
                if unused_message:
                    self._reports_with_unused_columns += 1
                    self._results.append([report_id, name, sharer_name, num_of_hidden, unused_message])
        except Exception as e:
            if self._debug:
                print(Fore.RED + str(e))
        bar()

    def _intro(self):
        self._handle_input()
        print(
            Fore.CYAN + 'This tool will analyze reports shared to the whole organization. You will need to sign in to '
                        'your Power BI account to proceed.')
        input(Fore.CYAN + 'Press Enter to start the analysis process..')
        token = self._get_token()
        all_shared_res = self._links_shared_to_whole_organization_api(token)
        reports = self._extract_artifact_ids(all_shared_res)
        print(Fore.GREEN + f'Found {len(reports)} reports shared to whole organization.')
        region = self._extract_region(all_shared_res)
        write_to_csv(self._result_output_path, [SHARED_TO_ORG_HEADERS], True)
        average_time_per_report = 0.5
        estimated_time = len(reports) * average_time_per_report
        print(Fore.YELLOW + f'Estimated time to analyze all reports: {estimated_time} seconds.')
        return region, reports, token

    def _get_report_data(self, region, response_data, token):
        artifact_id = response_data.get(ResponseKeys.ENTITY_KEY, {}).get(ResponseKeys.ID)
        model_id = next(item.get(ResponseKeys.ID) for item in response_data.get(ResponseKeys.RELATED_ENTITY_KEY) if
                        item.get(ResponseKeys.TYPE) == 4)
        conceptual_schema = self._send_conceptual_schema_request(token, model_id, region)
        exploration_response = self._send_exploration_request(token, artifact_id, region)
        return conceptual_schema, exploration_response

    def analyze(self):
        try:
            self._welcome_text()
            region, reports, token = self._intro()
            end_time, reports, start_time = (self._run_analysis(reports, region, token))
            self._outro(end_time, reports, start_time)
        except Exception as e:
            print(Fore.RED + 'Exiting due to an error.')
            if self._debug:
                print(Fore.RED + str(e))


def main():
    parser = argparse.ArgumentParser(description='Analyze Shared Power BI Reports')
    parser.add_argument('--output-folder', type=str, help='The path to the output folder')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--extended-time', action='store_true', help='Extend time limit from 10 to 60 minutes')
    args = parser.parse_args()

    analyzer = SharedReportsAnalyzer(
        output_folder=args.output_folder,
        debug=args.debug,
        extended_time_limit=args.extended_time
    )
    analyzer.analyze()
