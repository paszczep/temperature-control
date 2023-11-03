from psycopg2 import connect, OperationalError
from pathlib import Path
from dotenv import dotenv_values
from logging import info, warning
from time import sleep


dotenv_path = Path(__file__).parent.parent.parent / '.env'
env_values = dotenv_values(dotenv_path)

db_config = {
    "host": env_values.get('DB_HOST'),
    "dbname": env_values.get('DB_NAME'),
    "user": env_values.get('DB_USER'),
    "password": env_values.get('DB_PASSWORD'),
    "port": env_values.get('DB_PORT')
}


RETRIES = 10


def establish_db_connection(retries=RETRIES):
    while retries:
        try:
            info('initiating database connection')
            established_db_connection = connect(**db_config)
            return established_db_connection
        except OperationalError as e:
            retries -= 1
            warning(f"(Attempt {retries}) Error connecting to the database: {e}")
            sleep(3)
            return establish_db_connection(retries)
    else:
        info("max retries reached, unable to establish a connection")
        raise Exception("unable to connect to the database")


db_connection = establish_db_connection()


def cursor_try_except(func, retry=RETRIES):
    while retry:
        try:
            return func()
        except OperationalError as ex:
            warning(f'cursor error:{ex}')
            sleep(2)
            retry -= 1


def db_connection_and_cursor():
    info('db cursor')
    db_cursor = cursor_try_except(db_connection.cursor)
    return db_connection, db_cursor




