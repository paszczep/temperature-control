from typing import Union
from psycopg2 import connect
from .api import Set, Task
from pathlib import Path
from dotenv import dotenv_values
from psycopg2.extras import execute_values
import logging


dotenv_path = Path(__file__).parent.parent / '.env'
env_values = dotenv_values(dotenv_path)


db_config = {
    "host": env_values.get('DB_HOST'),
    "dbname": env_values.get('DB_NAME'),
    "user": env_values.get('DB_USER'),
    "password": env_values.get('DB_PASSWORD'),
    "port": env_values.get('DB_PORT')
}

db_connection = connect(**db_config)
logging.info('initiated database connection')


def db_connection_and_cursor():
    logging.info('db cursor')
    db_cursor = db_connection.cursor()
    return db_connection, db_cursor


def select_from_db(
        table_name: str,
        columns: Union[list, None] = None,
        where_equals: Union[dict[str, str], None] = None,
        where_in: Union[dict[str, list], None] = None,
        keys: bool = True
) -> Union[list, list[dict]]:

    def col_str(select_columns: list):
        if not select_columns:
            select_columns = '*'
        else:
            select_columns = str(select_columns)[1:-1].replace("'", '')
        return select_columns

    def where_clause() -> str:
        if where_equals:
            return f" WHERE {list(where_equals.keys())[0]} = '{list(where_equals.values())[0]}'"
        elif where_in:
            return f" WHERE {list(where_in.keys())[0]} IN {str(set(where_equals.values()))}"
        else:
            return ''

    select_query = f"""SELECT {col_str(columns)} FROM {table_name}{where_clause()}"""
    select_connection, select_cursor = db_connection_and_cursor()

    with select_cursor:
        select_cursor.execute(select_query)
        values = select_cursor.fetchall()
        if not keys:
            return_values = [val[0] for val in values]
        elif keys:
            names = [description[0] for description in select_cursor.description]
            return_values = [dict(zip(names, row)) for row in values]

    return return_values


def insert_many_notes(cur):
    execute_values(
        cur,
        "INSERT INTO test (id, v1, v2) VALUES %s",
        [(1, 2, 3), (4, 5, 6), (7, 8, 9)])


def insert_multiple_objects_into_db(data_objects: list, table_name: str):
    object_zero = data_objects[0]
    logging.info(f'inserting multiple {type(object_zero)} objects into db')
    value_keys = tuple(object_zero.__annotations__.keys())
    insert_data = [[row.__dict__[key] for key in value_keys] for row in data_objects]
    insert_query = f"""
        INSERT INTO {table_name} {str(value_keys).replace("'", "")} VALUES ({str('%s, '*len(value_keys))[:-2]})"""
    insert_connection, insert_cursor = db_connection_and_cursor()
    with insert_cursor:
        insert_cursor.executemany(insert_query, insert_data)
        insert_connection.commit()


def insert_one_object_into_db(data_object: object, table_name: str):
    logging.info(f'inserting {type(data_object)} object into db')
    value_keys = tuple(data_object.__annotations__.keys())
    insert_data = [data_object.__dict__[key] for key in value_keys]
    insert_query = f"""
        INSERT INTO {table_name} {str(value_keys).replace("'", "")} VALUES ({str('%s, '*len(value_keys))[:-2]})"""
    insert_connection, insert_cursor = db_connection_and_cursor()
    with insert_cursor:
        insert_cursor.execute(insert_query, insert_data)
        insert_connection.commit()


def clear_table(table_name: str):
    logging.info(f'clearing table {table_name}')
    delete_query = f"""DELETE FROM {table_name}"""
    delete_connection, delete_cursor = db_connection_and_cursor()
    with delete_cursor:
        delete_cursor.execute(delete_query)
        delete_connection.commit()


def update_status_in_db(update_object: Union[Task, Set]):
    logging.info(f'updating status in db to {update_object.status}')
    insert_connection, insert_cursor = db_connection_and_cursor()
    update_query = f"""
        UPDATE {update_object.__tablename__} SET status='{update_object.status}' WHERE id='{update_object.id}'
        """
    with insert_cursor:
        insert_cursor.execute(update_query)
        insert_connection.commit()


def delete_from_table(table_name: str, where: dict):
    logging.info(f'deleting from table {table_name} with a condition')
    delete_connection, delete_cursor = db_connection_and_cursor()
    delete_query = f"""DELETE FROM {table_name} WHERE {list(where.keys())[0]} = '{list(where.values())[0]}'"""
    with delete_cursor:
        delete_cursor.execute(delete_query)
        delete_connection.commit()
