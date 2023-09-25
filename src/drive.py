from time import time, sleep
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from tempfile import mkdtemp
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By
from dataclasses import dataclass
from pathlib import Path
from dotenv import dotenv_values
import logging
from typing import Union


dotenv_path = Path(__file__).parent.parent / '.env'
env_values = dotenv_values(dotenv_path)


@dataclass
class Ctrl:
    name: str
    logged: str
    received: str
    power: str
    setpoint: str
    database_time: int


class _ContainerDriver:
    wait_time = 5
    url = env_values['CONTROL_URL']
    login = env_values['CONTROL_LOGIN']
    password = env_values['CONTROL_PASSWORD']
    debug = env_values.get('DEBUG', True)

    def __init__(self):
        options = webdriver.ChromeOptions()
        service = webdriver.ChromeService("/opt/chromedriver")

        options.binary_location = '/opt/chrome/chrome'
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1280x1696")
        options.add_argument("--single-process")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-dev-tools")
        options.add_argument("--no-zygote")
        options.add_argument(f"--user-data-dir={mkdtemp()}")
        options.add_argument(f"--data-path={mkdtemp()}")
        options.add_argument(f"--disk-cache-dir={mkdtemp()}")
        options.add_argument("--remote-debugging-port=9222")

        self.driver = webdriver.Chrome(options=options, service=service)

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

    def click_not_now(self):
        try:
            self.wait_for_element_and_click((By.ID, 'btn_notnow'))
        except TimeoutException:
            pass

    def sign_in(self):
        self.driver.get(self.url)
        sign_in_button = self.wait_for_element_visibility((By.CSS_SELECTOR, 'button.btn.btn-primary'))
        self.find_and_fill_input('Username', self.login)
        self.find_and_fill_input('Password', self.password)
        sign_in_button.click()
        self.click_not_now()


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
        time_now = int(time())
        for row in range(names_number):
            row_values = values[row * column_number:row * column_number + column_number]
            all_data.append(
                Ctrl(
                    name=names.pop(),
                    logged=row_values[0],
                    received=row_values[1],
                    power=row_values[3],
                    setpoint=row_values[5],
                    database_time=time_now
                ))
        return all_data

    def container_values_reading_action(self) -> list[Ctrl]:
        names = self._read_container_names()
        values = self._read_container_values()
        container_data = self._parse_value_table(names, values)
        return container_data

    def read_values(self) -> list[Ctrl]:
        self.sign_in()
        container_data = self.container_values_reading_action()
        self.driver.close()
        return container_data


class ExecuteButtonError(Exception):
    pass


class ContainerSettingsDriver(ContainerValuesDriver):
    def _open_container_commands(self, container_name: str):
        self.wait_for_element_and_click((By.XPATH, f"//*[contains(text(), '{container_name}')]"))
        self.wait_for_element_and_click((By.CSS_SELECTOR, 'div.k-icon.k-collapse-prev'))
        self.wait_for_element_and_click((By.PARTIAL_LINK_TEXT, 'Commands'))

    def _open_temperature_setting_modal(self):
        sleep(self.wait_time/2)
        execute_button = self.driver.find_elements(By.CSS_SELECTOR, "a.k-grid-executeCommand.k-button")[2]
        execute_button.click()

    def _enter_temperature_setting(self, temperature_set_point: str):
        self.find_and_fill_input('Set point', temperature_set_point)
        if not self.debug:
            self.wait_for_element_and_click((By.ID, 'temperatureSetpointExecuteBtn'))
        else:
            commands_dialog = self.driver.find_elements(By.ID, 'commandsDialog')[0]
            commands_dialog.find_elements(By.CSS_SELECTOR, 'button.btn.btn-default')[0].click()

    def _temperature_setting_action(self, container: str, temperature: str):
        self._open_container_commands(container)
        self._open_temperature_setting_modal()
        self._enter_temperature_setting(temperature)

    def _temperature_check_and_setting(self, container: str, temperature: str) -> list[Ctrl]:
        check_values = self.container_values_reading_action()
        container_check = [ctrl for ctrl in check_values if ctrl.name == container].pop()
        logging.info(f'read: {container_check.setpoint}, required: {temperature}')
        if container_check.setpoint != temperature:
            self._temperature_setting_action(container, temperature)
        return check_values

    def check_containers_and_set_temperature0(self, container: str, temperature: str) -> list[Ctrl]:
        self.sign_in()
        try:
            read_settings = self._temperature_check_and_setting(container, temperature)
        except Exception as ex:
            logging.warning(f"{ex}")
            raise ExecuteButtonError
        else:
            return read_settings
        finally:
            self.driver.close()

    def check_containers_and_set_temperature(self, container: str, temperature: str) -> list[Ctrl]:
        self.sign_in()
        read_settings = self._temperature_check_and_setting(container, temperature)
        self.driver.close()
        return read_settings
