from dotenv import dotenv_values
import time
from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By
# from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
import os


@dataclass
class Control:
    name: str
    logged: str
    received: str
    power: str
    setpoint: str
    database_time: int


dotenv_path = Path(__file__).parent.parent / '.env'

env_values = dotenv_values(dotenv_path)


class _ContainerDriver:
    wait_time = 15
    url = env_values['CONTROL_URL']
    login = env_values['CONTROL_LOGIN']
    password = env_values['CONTROL_PASSWORD']
    binary = FirefoxBinary(env_values['FIREFOX_LOCATION'])
    headless = True
    debug = True

    def __init__(self):
        options = Options()
        options.headless = self.headless
        service = Service(log_path=os.devnull)
        self.driver = webdriver.Firefox(options=options, service=service)

    def driver_wait(self):
        return WebDriverWait(self.driver, self.wait_time)

    def wait_for_element_and_click(self, *args, click: bool = True):
        element = self.driver_wait().until(ec.element_to_be_clickable(*args))
        if click:
            element.click()
        return element

    def wait_for_element_visibility(self, *args):
        return self.driver_wait().until(ec.visibility_of_element_located(*args))

    def find_and_fill_input(self, field: str, input_value: str):
        input_field = self.wait_for_element_and_click((By.XPATH, f"//input[@placeholder='{field}']"))
        input_field.send_keys(input_value)

    def sign_in(self):
        self.driver.get(self.url)
        sign_in_button = self.wait_for_element_visibility((By.CSS_SELECTOR, 'button.btn.btn-primary'))
        self.find_and_fill_input('Username', self.login)
        self.find_and_fill_input('Password', self.password)
        sign_in_button.click()


class ContainerSettingsDriver(_ContainerDriver):
    def _open_container_commands(self, container_name: str):
        self.wait_for_element_and_click((By.XPATH, f"//*[contains(text(), '{container_name}')]"))
        self.wait_for_element_and_click((By.CSS_SELECTOR, 'div.k-icon.k-collapse-prev'))
        self.wait_for_element_and_click((By.PARTIAL_LINK_TEXT, 'Commands'))

    def _open_temperature_setting_modal(self):
        time.sleep(self.wait_time)
        execute_button = self.driver.find_elements(By.CSS_SELECTOR, "a.k-grid-executeCommand.k-button")[2]
        execute_button.click()

    def _enter_temperature_setting(self, temperature_set_point: str):
        self.find_and_fill_input('Set point', temperature_set_point)
        self.wait_for_element_and_click((By.ID, 'temperatureSetpointExecuteBtn'), click=not self.debug)

    def set_temperature(self, container: str, temperature: str):
        self.sign_in()
        self._open_container_commands(container)
        self._open_temperature_setting_modal()
        self._enter_temperature_setting(temperature)
        self.driver.close()


class ContainerValuesDriver(_ContainerDriver):
    def _read_container_names(self) -> list:
        container_label_keys = (By.CSS_SELECTOR, "span.emerson-menu-cursor.emerson-container-item-label")
        self.wait_for_element_visibility(container_label_keys)
        item_labels = self.driver.find_elements(*container_label_keys)
        name_elements = [element.text.strip() for element in item_labels][::-1]
        return name_elements

    def _read_container_values(self) -> list:
        values_table = self.driver.find_elements(By.CSS_SELECTOR, "table.k-selectable")[-1]
        invisible_cells = values_table.find_elements(By.XPATH, "//td[@style='display:none']")
        all_cells = values_table.find_elements(By.XPATH, "//td[@role='gridcell']")
        value_cells = [cell.text for cell in all_cells if cell not in invisible_cells]
        return value_cells

    @staticmethod
    def _parse_value_table(names: list, all_values: list) -> list:
        names_number = len(names)
        values = all_values[names_number:]
        column_number = len(values) // names_number
        all_data = []
        time_now = int(time.time())
        for row in range(names_number):
            row_values = values[row * column_number:row * column_number + column_number]
            all_data.append(
                Control(
                    name=names.pop(),
                    logged=row_values[0],
                    received=row_values[1],
                    power=row_values[3],
                    setpoint=row_values[5],
                    database_time=time_now
                ))
        return all_data

    def read_values(self) -> list[Control]:
        self.sign_in()
        names = self._read_container_names()
        values = self._read_container_values()
        container_data = self._parse_value_table(names, values)
        self.driver.close()
        return container_data
