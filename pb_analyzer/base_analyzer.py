import concurrent.futures
import os.path
from abc import abstractmethod
from datetime import datetime
from time import sleep

from alive_progress import alive_bar
from colorama import Fore, init

from pb_analyzer.const import ResponseKeys
from pb_analyzer.utils import write_to_txt, write_to_csv, split_and_format


class BaseAnalyzer:
    def __init__(self, tool: str, result_output_path: str, is_default_results_path: bool, results_output_path: str,
                 debug: bool = False):
        self._debug = debug
        self._result_output_path = result_output_path
        self._summary_output_path = results_output_path
        self._is_default_results_path = is_default_results_path
        self._results = []
        self._tool = tool
        self._unused_columns = []
        self._total_columns_scanned = 0
        self._reports_with_hidden_columns = 0
        self._reports_with_unused_columns = 0
        self._success_count = 0
        self._errors = []

    def _insert_all_columns(self, all_columns, num_of_hidden):
        if num_of_hidden > 0:
            self._reports_with_hidden_columns += 1

        for column in all_columns:
            if not any(existing_column[ResponseKeys.TABLE] == column[ResponseKeys.TABLE] and existing_column[
                ResponseKeys.COLUMN] == column[ResponseKeys.COLUMN] for
                       existing_column in self._unused_columns):
                self._unused_columns.append(column)
            else:
                for existing_column in self._unused_columns:
                    if (existing_column[ResponseKeys.TABLE] == column[ResponseKeys.TABLE]
                            and existing_column[ResponseKeys.COLUMN] == column[ResponseKeys.COLUMN]):
                        existing_column[ResponseKeys.UNUSED] = True

    @staticmethod
    def _insert_new_path(path, suffix: str):
        print(Fore.YELLOW + f'Default output {suffix.upper()} file: {path}')
        print(Fore.YELLOW + f'Press Enter to continue with the default path or type a new path.')
        user_input = input()
        if user_input:
            if user_input.endswith(f'.{suffix}'):
                print(Fore.YELLOW + f'Output {suffix.upper()} file: {user_input}')
                return user_input
            else:
                print(Fore.RED + 'Invalid file path. Using default path.')
        return path

    @abstractmethod
    def _intro(self):
        pass

    def _handle_input(self):
        if not self._is_default_results_path:
            return

        print(Fore.YELLOW + f'Default output directory: {os.path.dirname(self._result_output_path)}')
        print(Fore.YELLOW + f'Press Enter to continue with the default directory or type a new directory.')
        user_input = input()
        if user_input:
            if '.' in user_input.split('/')[-1]:
                print(Fore.RED + 'Invalid directory. Using default paths.')
                return
            if os.path.isdir(user_input) or not os.path.exists(user_input):
                os.makedirs(user_input, exist_ok=True)
                self._result_output_path = os.path.join(user_input, os.path.basename(self._result_output_path))
                self._summary_output_path = os.path.join(user_input, os.path.basename(self._summary_output_path))
        print(Fore.GREEN + f'Output directory: {os.path.dirname(self._result_output_path)}')
        print()

    @abstractmethod
    def _process_report(self, row, bar, start_time, *args):
        raise NotImplementedError

    def _run_analysis(self, rows, *args):
        start_time = datetime.now()
        timed_out = False

        with alive_bar(len(rows), bar='blocks') as bar:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(self._process_report, row, bar, start_time, *args) for row in rows]
                for future in concurrent.futures.as_completed(futures):
                    try:
                        future.result()
                    except TimeoutError as e:
                        if self._debug:
                            print(Fore.RED + str(e))
                        timed_out = True
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
            write_to_csv(self._result_output_path, self._results)
        if timed_out:
            print(Fore.RED + 'Passed the 10 minutes mark. Stopped the analysis.')
            sleep(1)
        end_time = datetime.now()
        return end_time, rows, start_time

    def _welcome_text(self):
        init(autoreset=True)

        print(Fore.CYAN + "=" * 65)
        print(Fore.YELLOW + "Welcome to Power BI Analyzer - Report Analysis Tool".center(65))
        print(Fore.CYAN + "=" * 65)
        sleep(0.3)
        print()
        print(Fore.GREEN + "Project: Power BI Analyzer")
        sleep(0.3)
        print(Fore.GREEN + f"Tool: {self._tool}")
        print()
        sleep(0.3)
        print(Fore.WHITE + "This tool is part of the Power BI Analyzer project, which aims to help")
        sleep(0.2)
        print(Fore.WHITE + "organizations identify unused data sources in their Power BI reports.")
        sleep(0.2)
        print(Fore.WHITE + "Unused columns in your reports can pose a security risk, and it is")
        sleep(0.2)
        print(Fore.WHITE + "essential to identify and remove them to prevent data breaches.")
        print()
        sleep(0.5)
        print(Fore.MAGENTA + "BACKGROUND:")
        sleep(0.1)
        print(Fore.WHITE + "On June 19, 2024, Nokod Security published a warning about a data leakage")
        sleep(0.1)
        print(Fore.WHITE + "vulnerability in the Microsoft Power BI service. For more details, visit:")
        sleep(0.1)
        print(
            Fore.BLUE + "https://nokodsecurity.com/blog/in-plain-sight-how-microsoft-power-bi-reports-expose-sensitive-data-on-the-web/")
        print()
        sleep(0.5)
        print(Fore.WHITE + "Nokod Security created the \"Power BI Analyzer\" as a simple and free tool")
        sleep(0.1)
        print(Fore.WHITE + "for organizations to assess their exposure to this vulnerability. If you")
        sleep(0.1)
        print(Fore.WHITE + "need help with this tool, please contact amichai@nokodsecurity.com or")
        sleep(0.1)
        print(Fore.WHITE + "uriya@nokodsecurity.com.")
        print(Fore.CYAN + "=" * 65)
        sleep(0.5)

    def _outro(self, end_time, rows, start_time):
        print()
        print(Fore.CYAN + "=" * 65)
        print(Fore.MAGENTA + "Results".center(65))
        print(Fore.CYAN + "=" * 65)
        results = [
            f'Number of reports analyzed successfully: {self._success_count}/{len(rows)}',
            'Total tables scanned: ' + str(len(set([column['table'] for column in self._unused_columns]))),
            'Unique columns scanned: ' + str(len(self._unused_columns)),
            'Unused columns found: ' + str(
                len([column for column in self._unused_columns if column.get(ResponseKeys.UNUSED)])),
            'Reports with unused columns: ' + str(self._reports_with_unused_columns),
            'Reports with hidden columns: ' + str(self._reports_with_hidden_columns),
            'Scan time: ' + str(end_time - start_time),
            ''
        ]

        for line in results:
            print(Fore.WHITE + line)

        error_messages = []
        if self._success_count != len(rows):
            if self._errors:
                error_messages = [f'Failed to analyze "{row[0]}". Error: "{split_and_format(row[1])}"' for row in
                                  self._errors]

        title = ['', 'Project: Power BI Analyzer', f'Tool: {self._tool}', '']
        header = ['=' * 65, 'Results'.center(65), '=' * 65, '']
        closing = ['=' * 65]
        footer = ['', 'Full analysis saved to ' + self._result_output_path]
        write_to_txt(self._summary_output_path, title + header + results + closing + error_messages + footer)
        print(Fore.CYAN + "=" * 65)
        print()
        [print(Fore.RED + line) for line in error_messages]
        print()
        print(Fore.GREEN + 'Full analysis saved to ' + self._result_output_path)
        print(Fore.GREEN + 'Results saved to ' + self._summary_output_path)
