from src.external_apis.drive_web import _BrowserDriver
from time import time, sleep
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from dataclasses import dataclass
from logging import info, warning
from typing import Union


@dataclass(frozen=True)
class DriverCheck:
    name: str
    logged: str
    received: str
    power: str
    setpoint: str
    database_time: int


class _ContainersDriver(_BrowserDriver):

    def find_and_fill_input(self, field: str, input_value: str):
        input_field = self.wait_for_element_and_click((By.XPATH, f"//input[@placeholder='{field}']"))
        input_field.send_keys(input_value)

    def click_not_now(self):
        info('driver not now refresh password')
        try:
            self.driver.find_element(By.ID, 'btn_notnow').click()
            warning('refresh password required !')
        except NoSuchElementException:
            pass

    def sign_in(self):
        info('driver signing in!')
        self.driver.get(self.url)
        sign_in_button = self.wait_for_element_visibility((By.CSS_SELECTOR, 'button.btn.btn-primary'))
        self.find_and_fill_input('Username', self.login)
        self.find_and_fill_input('Password', self.password)
        sign_in_button.click()
        self.click_not_now()


class CheckContainersDriver(_ContainersDriver):
    check_values: Union[None, list[DriverCheck]] = None

    def _read_container_names(self) -> list:
        info('driver reading container names')
        container_label_keys = (By.CSS_SELECTOR, "span.emerson-menu-cursor.emerson-container-item-label")
        self.wait_for_element_visibility(container_label_keys)
        item_labels = self.driver.find_elements(*container_label_keys)
        name_elements = [element.text.strip() for element in item_labels][::-1]
        return name_elements

    def _read_container_values(self) -> list:
        info('driver reading container values')
        values_table = self.driver.find_elements(By.CSS_SELECTOR, "table.k-selectable")[-1]
        invisible_cells = values_table.find_elements(By.XPATH, "//td[@style='display:none']")
        all_cells = values_table.find_elements(By.XPATH, "//td[@role='gridcell']")
        value_cells = [cell.text for cell in all_cells if cell not in invisible_cells]
        return value_cells

    @staticmethod
    def _parse_value_table(names: list, all_values: list) -> list[DriverCheck]:
        names_number = len(names)
        values = all_values[names_number:]
        column_number = len(values) // names_number
        all_data = []
        time_now = int(time())
        for row in range(names_number):
            row_values = values[row * column_number:row * column_number + column_number]
            all_data.append(
                DriverCheck(
                    name=names.pop(),
                    logged=row_values[0],
                    received=row_values[1],
                    power=row_values[3],
                    setpoint=row_values[5],
                    database_time=time_now
                ))
        return all_data

    def _container_values_reading_action(self) -> list[DriverCheck]:
        info('driver reading container data')
        names = self._read_container_names()
        values = self._read_container_values()
        self.check_values = self._parse_value_table(names, values)
        return self.check_values

    def _load_data_table(self, retry: int = 5):
        while retry:
            try:
                info('driver loading data table')
                return self._container_values_reading_action()
            except TimeoutException:
                retry -= 1
                retry_count = 5 - retry
                table_wait = 0.5 * retry_count
                info(f'retry {retry_count}, waiting {table_wait}')
                sleep(table_wait)
                return self._container_values_reading_action()
        else:
            warning('driver failed to load container service table')

    def read_values(self) -> list[DriverCheck]:
        info('driver reading container values process start')
        self.sign_in()
        container_data = self._load_data_table()
        self.driver.close()
        return container_data
