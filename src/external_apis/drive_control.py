from time import sleep
from src.external_apis.drive_check import CheckContainersDriver, DriverCheck
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException
from selenium.webdriver.common.by import By
from logging import info, warning
from decimal import Decimal
from typing import Union


class DriverExecuteError(Exception):
    def __init__(self, message):
        warning('driver execute error')
        self.message = message
        super().__init__(self.message)


class ControlContainersDriver(CheckContainersDriver):
    container: str
    temperature: str
    debug: bool = False
    if debug:
        warning('debug active')

    def _open_container_commands(self):
        info('driver opening container commands')
        self.wait_for_element_and_click((By.XPATH, f"//*[contains(text(), '{self.container}')]"))
        self.wait_for_element_and_click((By.CSS_SELECTOR, 'div.k-icon.k-collapse-prev'))
        self.wait_for_element_and_click((By.PARTIAL_LINK_TEXT, 'Commands'))

    def _open_temperature_setting_modal(self):
        info('driver opening settings modal')
        execute_button = self.driver.find_elements(By.CSS_SELECTOR, "a.k-grid-executeCommand.k-button")[2]
        execute_button.click()

    def _enter_temperature_setting(self):
        info('driver entering temperature setting')
        self.find_and_fill_input('Set point', self.temperature)
        if not self.debug:
            self.wait_for_element_and_click((By.ID, 'temperatureSetpointExecuteBtn'))
            info('driver click! Execute button')
            sleep(max(0.5, self.wait_time / 5))
        else:
            commands_dialog = self.driver.find_elements(By.ID, 'commandsDialog')[0]
            cancel_button = commands_dialog.find_elements(By.CSS_SELECTOR, 'button.btn.btn-default')[0]
            warning(f'driver debug mode, clicking "{cancel_button.text}"')
            cancel_button.click()

    def _wait_for_commands_menu(self):
        menu_wait = self.wait_time * 1.2
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
            sleep(max(0.5, self.wait_time / 5))
            sure_modal = self.wait_for_element_visibility((By.ID, 'confirmationDialog'))
            sure_ok_button = sure_modal.find_element(By.CSS_SELECTOR, "button.btn.btn-primary")
            info(f'driver click "{sure_ok_button.text}"')
            ActionChains(self.driver).move_to_element(sure_ok_button).click(sure_ok_button).perform()
            self._wait_for_commands_menu()

    def _previous_setting_awaiting_confirmation(self):
        self.driver.find_element(By.XPATH, f"//*[contains(text(), 'Awaiting confirmation')]")
        info('driver: "Awaiting previous setting confirmation"')

    def _temperature_setting_action(self):
        info(f'driver setting: {self.temperature}°C in container: {self.container}')
        self._open_container_commands()
        self._wait_for_commands_menu()
        self._cancel_previous_setting()
        try:
            self._previous_setting_awaiting_confirmation()
        except NoSuchElementException:
            self._open_temperature_setting_modal()
            self._enter_temperature_setting()

    def _check_driven_container(self) -> Union[Decimal, None, DriverExecuteError]:
        info('driver container check')

        def _log_container():
            info(f'   set point: {_set_point}')
            info(f'   power: {_power}')
            info(f'   logged: {check_container.logged}')

        check_container = [chk for chk in self.check_values if chk.name == self.container].pop()
        _power = check_container.power
        _set_point = check_container.setpoint
        _log_container()
        if _power == 'On':
            if _set_point != '':
                return Decimal(_set_point)
            else:
                warning('driver no active check set point available')
                raise RuntimeError
        elif _power == 'Off':
            warning('driver container unavailable for settings')
            raise DriverExecuteError

    def _temperature_check_and_setting(self):
        self._container_values_reading_action()
        checked_setting = self._check_driven_container()
        intended_setting = Decimal(self.temperature)
        info(f'driver setting read: {checked_setting}, required: {intended_setting}')
        if checked_setting != intended_setting:
            try:
                info('driver attempted setting')
                self._temperature_setting_action()
            except ElementNotInteractableException:
                warning('driver setting unavailable')
                pass

    def check_containers_and_set_temperature(self, container: str, temperature: str) -> list[DriverCheck]:
        self.container = container
        self.temperature = temperature
        info('driver check containers and set temperature')
        self.sign_in()
        try:
            self._temperature_check_and_setting()
        except RuntimeError:
            warning('driver setting unavailable')
            pass
        finally:
            info('driver closing')
            self.driver.close()
            return self.check_values
