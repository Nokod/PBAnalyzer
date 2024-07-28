import csv
import json
from typing import Dict, List, Union


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
                if key == 'Name' and isinstance(value, str) and (
                        value.startswith('DateTableTemplate') or value.startswith('LocalDateTable')):
                    skip_entity = True
                if key == 'Hidden' and value is True and not skip_entity:
                    count += 1
                count += recursive_count(value, skip_entity)
        elif isinstance(data, list):
            for item in data:
                count += recursive_count(item, skip_entity)
        return count

    return recursive_count(response)


def _extract_tables_and_columns(response: dict):
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
    extracted_cols_and_tables = _extract_tables_and_columns(conceptual_schema)
    filtered_cols_and_tables = [item for item in extracted_cols_and_tables if
                                "DateTableTemplate" not in item and "LocalDateTable" not in item]
    return filtered_cols_and_tables


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
