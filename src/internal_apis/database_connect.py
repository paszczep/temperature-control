from psycopg2 import connect, OperationalError
from pathlib import Path
from dotenv import dotenv_values
import logging
import time


dotenv_path = Path(__file__).parent.parent.parent / '.env'
env_values = dotenv_values(dotenv_path)

db_config = {
    "host": env_values.get('DB_HOST'),
    "dbname": env_values.get('DB_NAME'),
    "user": env_values.get('DB_USER'),
    "password": env_values.get('DB_PASSWORD'),
    "port": env_values.get('DB_PORT')
}


def establish_db_connection(retries=5):
    while retries:
        try:
            logging.info('initiating database connection')
            established_db_connection = connect(**db_config)
            return established_db_connection
        except OperationalError as e:
            retries -= 1
            logging.warning(f"(Attempt {retries}) Error connecting to the database: {e}")
            time.sleep(10)
            return establish_db_connection(retries)
    else:
        logging.info("max retries reached, unable to establish a connection")
        raise Exception("unable to connect to the database")


db_connection = establish_db_connection()


def db_connection_and_cursor():
    logging.info('db connection and cursor')
    db_cursor = db_connection.cursor()
    return db_connection, db_cursor




