from src.internal_processes.controlling import save_task_control
from src.external_processes.tasking_execute import TaskingExecution
from logging import info


class TaskingChecking(TaskingExecution):

    def beginning(self):
        info('setting start temperature if necessary')
        self.intended_setting = self.t_start
        if self.check:
            self.set_temperature_if_necessary()
        else:
            self.set_temperature()

    def considering_cooling(self):
        info('anticipating maximum temperature')
        if self.is_at_maximum(self.measurements):
            info('maximum temperature reached')
            self.intended_setting = self.t_min - 5
            self.set_temperature_if_necessary()
        else:
            info('supposedly temperature is still rising')
            self.intended_setting = self.t_start
            self.set_temperature_if_necessary()

    def considering_adjusting(self):
        info('measure temperature and decide')
        if self.is_at_minimum(self.measurements):
            info('minimum temperature reached')
            self.intended_setting = self.check + 1
            self.set_temperature()
        elif self.is_at_maximum(self.measurements):
            info('maximum temperature reached')
            self.intended_setting = self.check + 1
            self.set_temperature()
        else:
            info('temperature setting is ok')
            save_task_control(self.check, self.id)

    def finishing(self):
        info('finished task, setting t freeze')
        self.intended_setting = self.t_freeze
        self.set_temperature_if_necessary()
        if self.check == self.t_freeze:
            info('task finished, ending temperature set')
            self.end_task()
