from src.external_apis.drive import ContainerSettingsDriver, Ctrl
from src.internal_processes.reading import task_relevant_temperature_reading
from src.internal_processes.checking import create_and_save_checks
from src.internal_processes.controlling import create_and_save_control, create_task_control_pairing

import logging


def driver_check_and_introduce_setting(container_name: str, temp_setting: str) -> list[Ctrl]:
    logging.info(f'launching webdriver to set {temp_setting} in {container_name}')
    return ContainerSettingsDriver().check_containers_and_set_temperature(
        container=container_name,
        temperature=temp_setting)


def driver_set_go_save_checks_and_control(
        temperature_setting: int,
        task_id: str,
        task_container_name: str
):
    task_relevant_temperature_reading(task_id)
    logging.info(f'initiating driver to set {str(temperature_setting)}')
    driver_checks = driver_check_and_introduce_setting(
        container_name=task_container_name,
        temp_setting=(temperature_setting := f'{str(temperature_setting)}.0'))
    create_and_save_checks(driver_checks)
    performed_control = create_and_save_control(temperature_setting)
    create_task_control_pairing(performed_control, task_id)


def set_temperature_if_necessary(
        task_id: str,
        task_container_name: str,
        existing_check_temperature: int,
        temperature_setting: int):
    logging.info(f'considering {str(temperature_setting)}, provided {str(existing_check_temperature)}')
    if temperature_setting != existing_check_temperature:
        driver_set_go_save_checks_and_control(temperature_setting, task_id, task_container_name)
    else:
        logging.info('desired setting already active')
