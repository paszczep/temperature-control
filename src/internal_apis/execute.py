from src.external_processes.tasking_process import task_process
from src.external_processes.setting import set_process
from src.internal_processes.checking import check_containers
from src.external_processes.initializing import initialize_database
from hashlib import sha256
from pathlib import Path
from dotenv import dotenv_values
from logging import info

root_dir = Path(__file__).parent.parent.parent
dotenv_path = root_dir / '.env'
env_values = dotenv_values(dotenv_path)


def key_hash(key: str) -> str:
    return sha256(key.encode("utf-8")).hexdigest()


def parse_event(event):
    return event.get('queryStringParameters') or event


def run_lambda(event, _):
    event = parse_event(event)
    if event:
        key_1 = event.get('key_1', None)
        key_2 = event.get('key_2', None)
        initialize = event.get('initialize', None)
        check = event.get('check', None)
        task = event.get('task', None)
        setting = event.get('set', None)

        if key_1 == key_hash(env_values.get('KEY_1')) and key_2 == env_values.get('KEY_2'):
            if initialize:
                info(f'initializing database')
                initialize_database()
            elif task:
                info(f'running task')
                task_process(task_id=task)
            elif setting:
                info(f'running setting')
                set_process(set_id=setting)
            elif check:
                info(f'just checking')
                check_containers()
    return event
