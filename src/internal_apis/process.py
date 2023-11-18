from src.external_processes.tasking import perform_task
from src.external_processes.setting import perform_setting
from src.internal_processes.checking import perform_check
from src.external_processes.initialize import initialize_database
from src.internal_apis.test import perform_test
from hashlib import sha256
from pathlib import Path
from dotenv import dotenv_values
from logging import info
from typing import Union
from dataclasses import dataclass

root_dir = Path(__file__).parent.parent.parent
dotenv_path = root_dir / '.env'
env_values = dotenv_values(dotenv_path)


@dataclass
class Event:
    key_1: str
    key_2: str
    test: bool
    initialize: bool
    check: bool
    task: Union[None, str]
    setting: Union[None, str]

    @staticmethod
    def event_arguments(event) -> dict:
        return event.get('queryStringParameters') or event

    @staticmethod
    def key_hash(key: str) -> str:
        return sha256(key.encode("utf-8")).hexdigest()

    def __init__(self, event):
        kwargs = self.event_arguments(event)
        self.__dict__.update(kwargs)
        assert self.key_1 == self.key_hash(env_values.get('KEY_1'))
        assert self.key_2 == env_values.get('KEY_2')

    def run_event(self):
        _map = {
            'test': perform_test,
            'initialize': initialize_database,
            'check': perform_check,
            'task': perform_task,
            'set': perform_setting,
        }
        for key, value in self.__dict__.items():
            if 'key_' not in key:
                if value:
                    info(f'process launching {key}')
                    if isinstance(value, bool):
                        _map[key]()
                    elif isinstance(value, str):
                        _map[key](value)
                    break


def run_lambda(event, _):
    Event(event).run_event()
