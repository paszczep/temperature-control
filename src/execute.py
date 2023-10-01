from .tasking import task_process
from .setting import set_process
from .checking import check_containers
from .initialize import initialize_database
from hashlib import sha256
from pathlib import Path
from dotenv import dotenv_values
import logging


dotenv_path = Path(__file__).parent.parent / '.env'
env_values = dotenv_values(dotenv_path)


def key_hash(key: str) -> str:
    return sha256(key.encode("utf-8")).hexdigest()


def run_lambda(event, context):
    got_event = event.get('queryStringParameters')
    if got_event:
        event = got_event
    if event:
        key_1 = event.get('key_1', None)
        key_2 = event.get('key_2', None)
        initialize = event.get('initialize', None)
        check = event.get('check', None)
        task = event.get('task', None)
        setting = event.get('set', None)

        if key_1 == key_hash(env_values.get('KEY_1')) and key_2 == env_values.get('KEY_2'):
            if initialize:
                logging.info(f'initializing database')
                initialize_database()
            elif task:
                logging.info(f'running task')
                task_process(task_id=task)
            elif setting:
                logging.info(f'running setting')
                set_process(set_id=setting)
            elif check:
                logging.info(f'just checking')
                check_containers()
    return event
