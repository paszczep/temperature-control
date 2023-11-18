from psycopg2 import connect, OperationalError, InternalError
from pathlib import Path
from dotenv import dotenv_values
from logging import info, warning
from psycopg2.extensions import cursor, connection
from time import sleep
from functools import wraps


dotenv_path = Path(__file__).parent.parent.parent / '.env'
env_values = dotenv_values(dotenv_path)

db_config = {
    "host": env_values.get('DB_HOST'),
    "dbname": env_values.get('DB_NAME'),
    "user": env_values.get('DB_USER'),
    "password": env_values.get('DB_PASSWORD'),
    "port": env_values.get('DB_PORT')
}


CONNECTION_RETRIES = 5


def connection_generator(retries: int = CONNECTION_RETRIES):
    while retries:
        try:
            consecutive_connection = connect(**db_config)
            yield consecutive_connection
        except OperationalError as e:
            retries -= 1
            warning(f"db error connecting to database: {e}")
            sleep(1)
            info(f'db connection count {CONNECTION_RETRIES - retries + 1}')
            continue
    else:
        raise ConnectionError("Database connection error")


connection_gen = connection_generator()


def db_connection_and_cursor() -> tuple[connection, cursor]:
    for next_db_connection in connection_gen:
        next_db_cursor = next_db_connection.cursor()
        return next_db_connection, next_db_cursor


def db_retry_on_exception(
        max_retries: int = CONNECTION_RETRIES,
        exceptions=(OperationalError, InternalError,)):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    result = func(*args, **kwargs)
                    return result
                except exceptions as e:
                    warning(f"Function {func.__name__}. Exception {e} occurred. Retrying...")
                    retries += 1
            raise Exception(f"Function {func.__name__} exceeded maximum retries.")

        return wrapper

    return decorator
