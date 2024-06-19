import csv
import json


def filter_strings_not_in_json(strings_list: list, json_string: str):
    """
    Filters a list of strings based on whether they are present in a JSON string.

    Args:
        strings_list (list): A list of strings to filter.
        json_string (str): A JSON string to compare the strings against.
    """
    json_str = json.dumps(json_string)
    normalized_json_string = json_str.replace('"', '').replace("'", '')

    return [string for string in strings_list if string not in normalized_json_string]


def write_to_csv(file_path, value1, value2, value3, value4, overwrite=False):
    """
    Writes values to a CSV file.

    Args:
        file_path (str): The path to the CSV file.
        value1 (str): The first value to write.
        value2 (str): The second value to write.
        value3 (list): The third value to write.
        value4 (list): The fourth value to write.
        overwrite (bool): Whether to overwrite the file or append to it. Default is False.

    """
    value4_str = ", ".join(value4)
    value3_str = ", ".join(value3)
    mode = 'w' if overwrite else 'a'
    with open(file_path, mode=mode, newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # write header while deleting past data
        writer.writerow([value1, value2, value3_str, value4_str])


def count_hidden_true_in_dict(response):
    """
    Counts the number of occurrences of the key-value pair "'Hidden': True" in the given dictionary response,
    ignoring entities where the name starts with 'DateTableTemplate'.

    Parameters:
    response (dict): The API response as a dictionary.

    Returns:
    int: The number of occurrences of "'Hidden': True" in the response, excluding entities named 'DateTableTemplate*'.
    """

    def recursive_count(data, skip_entity=False):
        count = 0
        if isinstance(data, dict):
            for key, value in data.items():
                # Skip counting if we are in an entity that should be ignored
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
