import argparse
import json
from urllib.parse import urlparse

import msal
import requests

from pb_analyzer.utils import count_hidden_true_in_dict, fetch_columns_and_tables, filter_strings_not_in_json, \
    write_to_csv


class SharedToWholeOrganizationAnalyzer:
    def __init__(self, output_path: str):
        self.output_path = output_path

    @staticmethod
    def _extract_artifact_ids(response: dict):
        """
        Extracts the artifactId values from the given API response.

        Args:
            response (dict): The API response in dictionary format.
        """
        artifact_ids = [entity['artifactId'] for entity in response.get('ArtifactAccessEntities', [])]
        return artifact_ids

    @staticmethod
    def _get_token():
        """
        Acquires an access token using the Microsoft Authentication Library (MSAL).
        """
        authority = "https://login.microsoftonline.com/common"
        client_id = "23d8f6bd-1eb0-4cc2-a08c-7bf525c67bcd"
        scope = ['https://analysis.windows.net/powerbi/api/.default openid profile offline_access']

        app = msal.PublicClientApplication(client_id, authority=authority)
        result = app.acquire_token_interactive(scopes=scope)

        if "access_token" in result:
            return result["access_token"]
        else:
            raise Exception("Failed to acquire token: %s" % result.get("error_description"))

    @staticmethod
    def _reports_published_to_web_api(token: str):
        """
        Sends a GET request to the Power BI API to retrieve the list of reports published to the web.

        Args:
            token (str): The access token to use for authentication.

        """
        url = 'https://api.powerbi.com/v1.0/myorg/admin/widelySharedArtifacts/publishedToWeb'
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

    @staticmethod
    def _links_shared_to_whole_organization_api(token: str):
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

    @staticmethod
    def _send_push_access_request(token: str, report_id: str, region: str):
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

    @staticmethod
    def _send_exploration_request(token: str, artifact_id: str, region: str):
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

    @staticmethod
    def _send_conceptual_schema_request(token: str, model_id: str, region: str):
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

    @staticmethod
    def _extract_region(response: dict):
        """
        Extracts the region from the given API response.

        Args:
            response (dict): The API response in dictionary format.
        """
        url = urlparse(response.get('@odata.context'))
        return url.netloc

    def analyze(self):
        token = self._get_token()
        all_shared_res = self._links_shared_to_whole_organization_api(token)
        report_list = self._extract_artifact_ids(all_shared_res)

        published_to_web_res = self._reports_published_to_web_api(token)
        published_to_web_ids = self._extract_artifact_ids(published_to_web_res)

        region = self._extract_region(all_shared_res)

        write_to_csv(self.output_path, ['Report ID', 'Number of hidden columns', 'All columns', 'Unused columns',
                                        'Published to web'], True)
        for reportID in report_list:
            try:
                print(f'Processing report ID: {reportID}')
                response_data = self._send_push_access_request(token, reportID, region)
                if response_data:
                    artifact_id = response_data['entityKey']['id']
                    model_id = next(item['id'] for item in response_data['relatedEntityKeys'] if item['type'] == 4)
                    print(f'Extracted artifact_id: {artifact_id}, model_id: {model_id}')
                    conceptual_schema = self._send_conceptual_schema_request(token, model_id, region)
                    num_of_hidden = count_hidden_true_in_dict(conceptual_schema)
                    print("There are " + str(num_of_hidden) + " Hidden column in this report")
                    exploration_response = self._send_exploration_request(token, artifact_id, region)
                    columns_and_tables = fetch_columns_and_tables(conceptual_schema)
                    unused_column = filter_strings_not_in_json(columns_and_tables, exploration_response)
                    write_to_csv(self.output_path,
                                 [reportID, str(num_of_hidden), ', '.join(columns_and_tables), ', '.join(unused_column),
                                  reportID in published_to_web_ids])
            except Exception as e:
                print(f"An error occurred while processing report ID {reportID}: {e}")
