from src.external_apis.drive import DriverExecuteError
from src.internal_processes.controlling_new import InvalidSettingRetry
from src.internal_apis.models_data import TaskingValues, CheckValues, ControlValues
from src.internal_apis.database_query import select_from_db
from src.internal_processes.driving import DrivingAction
from src.internal_processes.checking import check_containers
from src.external_processes.tasking_check import TaskingChecking
from logging import info, warning

# from time import time


SETTING_RETRY_ERROR_THRESHOLD = 5


class TaskingControlling(TaskingChecking):

    def verify_task_control(self, verified_controls: list[ControlValues], verified_checks: list[CheckValues]):
        info('checking for errors')
        check_points = [chk.read_setpoint for chk in verified_checks if chk.timestamp > self.start]
        control_points = [ctrl.target_setpoint for ctrl in verified_controls]
        info(f'''controls: {str(control_points)[1:-1].replace("'", "")}''')
        info(f'''checks: {str(check_points)[1:-1].replace("'", "")}''')

        for check_point in check_points:
            control_points.remove(check_point)
        info(f'''error? controls: {str(control_points)[1:-1].replace("'", "")}''')
        if len(control_points) >= SETTING_RETRY_ERROR_THRESHOLD:
            if len(set(control_points[-SETTING_RETRY_ERROR_THRESHOLD:])) == 1:
                raise InvalidSettingRetry

    def _no_controls(self):
        info('no executed controls, or none considered')
        if self.is_heating_up():
            info('control may require starting setting')
            self.intended_setting = self.t_start
            self.set_temperature_if_necessary()
        elif self.may_require_cooling():
            info('control may require cooling')
            self.considering_cooling()
        elif self.may_require_adjusting():
            info('control may require starting setting')
            self.considering_adjusting()
        elif self.is_finished():
            info('control may require freezing setting')
            self.intended_setting = self.t_freeze
            self.set_temperature_if_necessary()
        else:
            info('control unknown, considering adjusting')
            self.considering_adjusting()

    def _existing_control(self):
        info(f'recent controlled temperature {str(self.control)}, '
             f'recent check temperature {str(self.check)}')
        if self.control != self.check:
            info('retrying previous setting')
            DrivingAction(
                container_name=self.container_name,
                process_id=self.id,
                temperature_setting=self.control,
            ).driver_set_go_save_logs()
        else:
            self._no_controls()

    def control_process(self):
        if not self.control:
            self._no_controls()
        else:
            self._existing_control()


class TaskingProcessing(TaskingControlling):

    def task_process(self):
        if not self.checking:
            if not self.has_started_ago(minutes=60):
                info("task just started")
                self.beginning()
            elif self.is_finished():
                info("task is finished")
                self.finishing()
            else:
                info('task setting benchmark required, checking')
                check_containers()
        elif not self.is_finished():
            info("THERE EXISTS A BENCHMARK TO WORK WITH")
            self.control_process()
        else:
            info("finishing task process")
            self.finishing()


def run_task(task_id: str):
    def get_processed_task() -> TaskingProcessing:
        info('fetching processed task')
        return [TaskingProcessing(**s) for s in select_from_db(
            table_name=TaskingValues.__tablename__, where_equals={'id': task_id})].pop()

    info('processing task')
    running_task = get_processed_task()

    if running_task.status == 'running':
        try:
            running_task.task_process()
        except (InvalidSettingRetry, DriverExecuteError) as ex:
            warning(f'{ex}')
            running_task.error_task()
