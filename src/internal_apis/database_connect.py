from psycopg2 import connect, OperationalError
from pathlib import Path
from dotenv import dotenv_values
from logging import info, warning
from time import sleep
from psycopg2.extensions import cursor, connection


dotenv_path = Path(__file__).parent.parent.parent / '.env'
env_values = dotenv_values(dotenv_path)

db_config = {
    "host": env_values.get('DB_HOST'),
    "dbname": env_values.get('DB_NAME'),
    "user": env_values.get('DB_USER'),
    "password": env_values.get('DB_PASSWORD'),
    "port": env_values.get('DB_PORT')
}


CONNECTION_RETRIES = 3


def connection_generator(retries: int = CONNECTION_RETRIES):
    while retries:
        try:
            consecutive_connection = connect(**db_config)
            yield consecutive_connection
        except OperationalError as e:
            retries -= 1
            warning(f"error connecting to database: {e}")
            continue
        finally:
            info(f'db connection count {CONNECTION_RETRIES - retries + 1}')
    else:
        raise StopIteration


def get_connection_and_cursor():
    connection_gen = connection_generator()
    while True:
        try:
            next_db_connection = next(connection_gen)
            next_db_cursor = next_db_connection.cursor()
            return next_db_connection, next_db_cursor
        except StopIteration:
            warning("no working database connections available")
            raise ConnectionError


def db_connection_and_cursor():
    info('db cursor')
    return get_connection_and_cursor()


def database_exception(func):
    def wrapper(*args, **kwargs):
        try:
            info('db interaction start')

            result = func(*args, **kwargs)

        except Exception as e:
            info(f"an error occurred: {e}")

        else:
            # info("No exceptions occurred")
            return result

        finally:
            # Code to run no matter what, for cleanup, etc.
            info("db cursor closed")

    return wrapper



