from src.external_processes.tasking_execute import TaskingExecute
from logging import info
from decimal import Decimal


class TaskingDecide(TaskingExecute):

    def task_beginning(self):
        _t_start = self.task.t_start
        info(f'decide start setting: {self.log_setting(_t_start)}')
        if isinstance(self.checking.recent, Decimal):
            self.drive_consider_setting_save_log(_t_start)
        else:
            self.drive_setting_save_logs(_t_start)

    def task_consider_cooling(self):
        info('decide anticipating maximum temperature')
        if self.is_at_maximum():
            info('decide maximum temperature reached')
            self.drive_consider_setting_save_log(self.task.t_start - self.COOLING_DELTA)
        else:
            info('decide supposedly temperature is still rising')
            self.drive_consider_setting_save_log(self.task.t_start)

    def _check_for_benchmark(self):
        info(f'decide check point: {self.log_setting(self.checking.recent)}')
        if not isinstance(self.checking.recent, Decimal):
            info('decide benchmark required')
            self.driver_check_containers()

    def task_adjusting(self):
        info('decide measuring temperature for potential adjustment')
        self._check_for_benchmark()
        if self.is_at_minimum():
            info('decide minimum temperature reached')
            self.drive_setting_save_logs(self.checking.recent + 1)
        elif self.is_at_maximum():
            info('decide maximum temperature reached')
            self.drive_setting_save_logs(self.checking.recent - 1)
        else:
            info('decide temperature setting is ok')
            self.controlling.save_task_control(self.checking.recent)

    def task_consider_adjusting(self):
        info('decide task considering adjusting')
        if self.has_been_cooled_down():
            info('decide cooldown event detected, proceeding with setting adjustment')
            self.task_adjusting()
        else:
            info('decide supposedly a cooling has not yet been set')
            self.task_consider_cooling()

    def task_finishing(self):
        _t_freeze = self.task.t_freeze
        _t_check = self.checking.recent
        info(f'decide finished task, setting t freeze: {self.log_setting(_t_freeze)}')
        self.drive_consider_setting_save_log(_t_freeze)
        if _t_check == _t_freeze:
            info('decide task finished, ending temperature set')
            self.drive_end_task()
        else:
            info(f'checked set point: {_t_check}, '
                 f'desired end setting: {_t_freeze}, '
                 f'setting may be retried')
