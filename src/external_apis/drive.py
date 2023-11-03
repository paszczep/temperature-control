from time import time, sleep
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException, TimeoutException
from tempfile import mkdtemp
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By
from dataclasses import dataclass
from pathlib import Path
from dotenv import dotenv_values
from logging import info, warning
from decimal import Decimal

dotenv_path = Path(__file__).parent.parent.parent / '.env'
env_values = dotenv_values(dotenv_path)


class BrowserDriver:
    wait_time = 5
    url = env_values['CONTROL_URL']
    login = env_values['CONTROL_LOGIN']
    password = env_values['CONTROL_PASSWORD']
    debug = False

    def __init__(self):
        options = webdriver.ChromeOptions()
        service = webdriver.ChromeService("/opt/chromedriver")

        options.binary_location = '/opt/chrome/chrome'
        options.add_argument("--headless=new")
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


@dataclass
class Ctrl:
    name: str
    logged: str
    received: str
    power: str
    setpoint: str
    database_time: int


class _ContainerDriver(BrowserDriver):

    def find_and_fill_input(self, field: str, input_value: str):
        input_field = self.wait_for_element_and_click((By.XPATH, f"//input[@placeholder='{field}']"))
        input_field.send_keys(input_value)

    def click_not_now(self):
        info('driver not now refresh password')
        try:
            self.driver.find_element(By.ID, 'btn_notnow').click()
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


class ContainerValuesDriver(_ContainerDriver):
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
        info('driver reading container data')
        names = self._read_container_names()
        values = self._read_container_values()
        container_data = self._parse_value_table(names, values)
        return container_data

    def load_data_table(self, retry: int = 5):
        while retry:
            try:
                info('driver loading data table')
                return self.container_values_reading_action()
            except TimeoutException:
                retry -= 1
                retry_count = 5 - retry
                table_wait = self.wait_time * 0.2 * retry_count
                info(f'retry {retry_count}, waiting {table_wait}')
                sleep(table_wait)
                return self.container_values_reading_action()
        else:
            warning('driver failed to load container service table')

    def read_values(self) -> list[Ctrl]:
        info('driver reading container values process start')
        self.sign_in()
        container_data = self.load_data_table()
        self.driver.close()
        return container_data


class DriverExecuteError(Exception):
    def __init__(self, message):
        warning('driver execute error')
        self.message = message
        super().__init__(self.message)


class ContainerSettingsDriver(ContainerValuesDriver):

    def _open_container_commands(self, container_name: str):
        info('driver opening container commands')
        self.wait_for_element_and_click((By.XPATH, f"//*[contains(text(), '{container_name}')]"))
        self.wait_for_element_and_click((By.CSS_SELECTOR, 'div.k-icon.k-collapse-prev'))
        self.wait_for_element_and_click((By.PARTIAL_LINK_TEXT, 'Commands'))

    def _open_temperature_setting_modal(self):
        info('driver opening settings modal')
        execute_button = self.driver.find_elements(By.CSS_SELECTOR, "a.k-grid-executeCommand.k-button")[2]
        execute_button.click()

    def _enter_temperature_setting(self, temperature_set_point: str):
        info('driver entering temperature setting')
        self.find_and_fill_input('Set point', temperature_set_point)
        if not self.debug:
            self.wait_for_element_and_click((By.ID, 'temperatureSetpointExecuteBtn'))
            info('driver click! Execute button')
            sleep(1)
        else:
            info('driver debug mode, clicking Cancel')
            commands_dialog = self.driver.find_elements(By.ID, 'commandsDialog')[0]
            commands_dialog.find_elements(By.CSS_SELECTOR, 'button.btn.btn-default')[0].click()

    def _wait_for_commands_menu(self):
        menu_wait = self.wait_time + 3
        info(f'driver shamefully implicitly waiting for commands menu {menu_wait} seconds')
        # loading_image = self.driver.find_element(By.CSS_SELECTOR, "div.k-loading-image")
        # logging.info(f'{loading_image.get_attribute("outerHTML")}')
        # self.driver_wait().until(ec.invisibility_of_element_located((By.CSS_SELECTOR, "div.k-loading-image")))
        sleep(menu_wait)

    def _cancel_previous_setting(self):
        info('driver attempted canceling previous setting')
        commands_grid = self.driver.find_element(By.ID, "container-grid-detail-commands")
        all_cancel_buttons = commands_grid.find_elements(By.CSS_SELECTOR, "a.k-grid-cancelCommand.k-button")
        invisible_elements = commands_grid.find_elements(By.XPATH, "//*[@style='display: none;']")
        cancel_buttons = [b for b in all_cancel_buttons if b not in invisible_elements]
        if cancel_buttons:
            info('driver canceling previous setting')
            cancel_button = cancel_buttons.pop()
            info(f'driver click "{cancel_button.text}"')
            cancel_button.click()
            sleep(1)
            sure_modal = self.wait_for_element_visibility((By.ID, 'confirmationDialog'))
            sure_ok_button = sure_modal.find_element(By.CSS_SELECTOR, "button.btn.btn-primary")
            info(f'driver click "{sure_ok_button.text}"')
            ActionChains(self.driver).move_to_element(sure_ok_button).click(sure_ok_button).perform()
            self._wait_for_commands_menu()

    def _previous_setting_awaiting_confirmation(self):
        self.driver.find_element(By.XPATH, f"//*[contains(text(), 'Awaiting confirmation')]")
        info('driver: "Awaiting previous setting confirmation"')

    def _temperature_setting_action(self, container: str, temperature: str):
        info(f'driver setting {temperature}°C in container {container}')
        self._open_container_commands(container)
        self._wait_for_commands_menu()
        self._cancel_previous_setting()
        try:
            self._previous_setting_awaiting_confirmation()
        except NoSuchElementException:
            self._open_temperature_setting_modal()
            self._enter_temperature_setting(temperature)

    def _temperature_check_and_setting(self, container: str, temperature: str) -> list[Ctrl]:
        check_values = self.container_values_reading_action()
        container_check = [ctrl for ctrl in check_values if ctrl.name == container].pop()
        info(f'driver setting read: {container_check.setpoint}, required: {temperature}')
        if Decimal(container_check.setpoint) != Decimal(temperature):
            try:
                self._temperature_setting_action(container, temperature)
            except ElementNotInteractableException:
                warning('driver setting unavailable')
                pass
        return check_values

    def check_containers_and_set_temperature(self, container: str, temperature: str) -> list[Ctrl]:
        info('driver check containers and set temperature')
        self.sign_in()
        read_settings = self._temperature_check_and_setting(container, temperature)
        info('closing web driver')
        self.driver.close()
        return read_settings
