import csv
import json
import re
from typing import Dict, List, Union

from pb_analyzer.const import ResponseKeys


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
    columns = []
    for schema in response.get('schemas', [{}]):
        if schema.get('error'):
            break
        for entity in schema.get('schema', {}).get('Entities', []):
            table_name = entity.get('Name', 'UnknownTable')
            for prop in entity.get('Properties', []):
                column_name = prop.get('Name', 'UnknownColumn')
                columns.append({'table': table_name, 'column': column_name})

    return columns


def fetch_columns_and_tables(conceptual_schema: dict):
    """
    Extracts and filters the tables and columns from the conceptual schema response.

    Parameters:
    conceptual_schema (dict): The conceptual schema response as a dictionary.
    """
    extracted_cols_and_tables = _extract_tables_and_columns(conceptual_schema)
    filtered_cols_and_tables = [item for item in extracted_cols_and_tables if
                                "DateTableTemplate" not in item.get('table') and "LocalDateTable" not in item.get(
                                    'table')]
    return filtered_cols_and_tables


def get_classified_columns(report_columns: List[dict], json_string: dict, ) -> tuple[str, List[dict]]:
    """
    Filters out strings from the list that are not found in the JSON string.

    Args:
        report_columns (List[dict]): The list of strings to filter.
        json_string (dict): The JSON string to check against.

    Returns:
        tuple[str, str, List[dict]]: A tuple containing the unused columns and all columns.
    """
    json_str: str = json.dumps(json_string)
    normalized_json_string: str = json_str.replace('"', '').replace("'", '')
    unused_columns_and_tables = [column for column in report_columns if
                                 f'{column[ResponseKeys.TABLE]}.{column[ResponseKeys.COLUMN]}' not in normalized_json_string]
    tables = {}
    for column in report_columns:
        if column[ResponseKeys.TABLE] not in tables:
            tables[column[ResponseKeys.TABLE]] = []
        tables[column[ResponseKeys.TABLE]].append(column[ResponseKeys.COLUMN])

    unused_columns = []
    for table, columns in tables.items():
        table_unused_columns = [column[ResponseKeys.COLUMN] for column in unused_columns_and_tables if
                                column[ResponseKeys.TABLE] == table]
        if not table_unused_columns:
            continue
        columns.sort()
        table_unused_columns.sort()
        if table_unused_columns == columns:
            unused_columns.append(f'{table}: [.*]')
        elif any([False if column in table_unused_columns else True for column in columns]):
            unused_columns.append(f'{table}: [{", ".join(table_unused_columns)}]')

    for column in report_columns:
        column['used'] = False
        for unused_column in unused_columns_and_tables:
            if column[ResponseKeys.TABLE] == unused_column[ResponseKeys.TABLE] and column[ResponseKeys.COLUMN] == \
                    unused_column[ResponseKeys.COLUMN]:
                column[ResponseKeys.UNUSED] = True
                break

    return ', '.join(unused_columns), report_columns


def write_to_csv(file_path: str, values: List[List], overwrite: bool = False) -> None:
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
        writer.writerows(values)


def write_to_txt(file_path: str, values: List[str]) -> None:
    """
    Writes values to a text file.

    Args:
        file_path (str): The path to the text file.
        values (List[str]): The values to write to the text file.
    """
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write('\n'.join(values))


def split_and_format(text):
    split_text = re.sub(r'(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', ' ', text)
    return split_text
