from .drive import ContainerSettingsDriver, Ctrl
from .database import select_from_db, update_status_in_db, insert_one_object_into_db
from .api import Control, ContainerSet, Set, SetControl
from .checking import create_and_save_checks, create_and_save_control
import logging

logger = logging.getLogger()


def set_process(set_id: str):
    def get_performed_set() -> Set:
        logger.info('fetching setting parameters for execution')
        select_sets = select_from_db(table_name=Set.__tablename__, where_equals={'id': set_id})
        if select_sets:
            return [Set(**s) for s in select_sets].pop()
        else:
            exit()

    def get_set_container_relationship() -> ContainerSet:
        logger.info('fetching target container')
        return [ContainerSet(**c) for c in select_from_db(
            table_name=ContainerSet.__tablename__, where_equals={'set_id': set_id})].pop()

    def create_set_control_pairing(performed_set_control: Control, related_set: Set):
        logger.info('pairing setting with created control')
        performed_control_relationship = SetControl(
            control_id=performed_set_control.id,
            set_id=related_set.id)
        insert_one_object_into_db(performed_control_relationship, SetControl.__tablename__)

    def end_set(finnish_set: Set):
        logger.info('ending setting')
        finnish_set.status = 'ended'
        update_status_in_db(finnish_set)

    def get_setting_control(all_controls: list[Ctrl], pairing: ContainerSet) -> Ctrl:
        logger.info('fetching working temperature setting value for comparison')
        return [c for c in all_controls if c.name == pairing.container_id].pop()

    def run_set(go_set: Set):
        logger.info('running setting of temperature')

        def driver_check_containers_and_execute_set(container_name: str, temp_setting: str) -> list[Ctrl]:
            logger.info(f'launching webdriver to set {temp_setting} in {container_name}')
            return ContainerSettingsDriver().check_containers_and_set_temperature(
                container=container_name,
                temperature=temp_setting)

        set_container_pairing = get_set_container_relationship()
        container_controls = driver_check_containers_and_execute_set(
            container_name=set_container_pairing.container_id,
            temp_setting=(set_temperature := f'{str(go_set.temperature)}.0'))
        create_and_save_checks(container_controls)
        performed_control = create_and_save_control(set_temperature)
        create_set_control_pairing(performed_control, go_set)
        setting_ctrl = get_setting_control(container_controls, set_container_pairing)
        if setting_ctrl.setpoint == set_temperature:
            end_set(go_set)

    performed_set = get_performed_set()
    logger.info(f'performed setting status: "{performed_set.status}"')

    if performed_set.status == 'running':
        run_set(performed_set)
