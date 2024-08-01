from abc import abstractmethod
from time import sleep
from colorama import Fore, init
from pb_analyzer.const import ResponseKeys
from pb_analyzer.utils import write_to_txt


class BaseAnalyzer:
    def __init__(self, tool: str, result_output_path: str, is_default_results_path: bool, results_output_path: str, is_default_summary_path: bool):
        self.result_output_path = result_output_path
        self.summary_output_path = results_output_path
        self.is_default_results_path = is_default_results_path
        self.is_default_summary_path = is_default_summary_path
        self.tool = tool
        self._unused_columns = []
        self._total_columns_scanned = 0
        self._reports_with_hidden_columns = 0
        self._reports_with_unused_columns = 0

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

    @abstractmethod
    def _intro(self):
        pass

    def _handle_input(self):
        if self.is_default_results_path:
            print(Fore.YELLOW + f'Default output CSV file: {self.result_output_path}')
            print(Fore.YELLOW + f'Press Enter to continue with the default path or type a new path.')
            user_input = input()
            if user_input:
                self.result_output_path = user_input
        if self.is_default_summary_path:
            print(Fore.YELLOW + f'Results TXT file: {self.summary_output_path}')
            print(Fore.YELLOW + f'Press Enter to continue with the default path or type a new path.')
            user_input = input()
            if user_input:
                self.summary_output_path = user_input

    def _collect_path(self):
        print(Fore.YELLOW + f'Press Enter to continue with the default path or type a new path.')
        user_input = input()
        if user_input:
            self.result_output_path = user_input

    def welcome_text(self):
        init(autoreset=True)

        print(Fore.CYAN + "=" * 65)
        print(Fore.YELLOW + "Welcome to Power BI Analyzer - Report Analysis Tool".center(65))
        print(Fore.CYAN + "=" * 65)
        sleep(0.3)
        print()
        print(Fore.GREEN + "Project: Power BI Analyzer")
        sleep(0.3)
        print(Fore.GREEN + f"Tool: {self.tool}")
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

    def outro(self, end_time, rows, start_time, success_count):
        print()
        print(Fore.CYAN + "=" * 65)
        print(Fore.MAGENTA + "Results".center(65))
        print(Fore.CYAN + "=" * 65)
        results = [
            f'Number of reports analyzed successfully: {success_count}/{len(rows)}',
            'Total tables scanned: ' + str(len(set([column['table'] for column in self._unused_columns]))),
            'Unique columns scanned: ' + str(len(self._unused_columns)),
            'Total unused columns found: ' + str(
                len([column for column in self._unused_columns if column.get(ResponseKeys.UNUSED)])),
            'Total reports with unused columns: ' + str(self._reports_with_unused_columns),
            'Total reports with hidden columns: ' + str(self._reports_with_hidden_columns),
            'Total time taken: ' + str(end_time - start_time),
        ]

        for line in results:
            print(Fore.WHITE + line)

        title = ['', 'Project: Power BI Analyzer', f'Tool: {self.tool}', '']
        header = ['=' * 65, 'Results'.center(65), '=' * 65, '']
        footer = ['=' * 65, '', 'Full analysis saved to ' + self.result_output_path]
        write_to_txt(self.summary_output_path, title + header + results + footer)
        print(Fore.CYAN + "=" * 65)
        print()
        print(Fore.GREEN + 'Full analysis saved to ' + self.result_output_path)
        print(Fore.GREEN + 'Results saved to ' + self.summary_output_path)
