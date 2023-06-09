import sqlite3
from pathlib import Path
from typing import Union

db_path = Path(__file__).parent.parent.parent / 'temp_ui' / 'instance' / 'db.sqlite'


def db_connection_and_cursor(db_location=db_path):
    db_connection = sqlite3.connect(db_location)
    db_cursor = db_connection.cursor()
    return db_connection, db_cursor


def select_from_db(
        table_name: str,
        columns: Union[list, None] = None,
        keys: bool = True
) -> Union[list, list[dict]]:
    if not columns:
        columns = '*'
    else:
        columns = str(columns)[1:-1]
    select_query = f"""SELECT {columns} FROM {table_name}"""
    print(select_query)
    select_connection, select_cursor = db_connection_and_cursor()
    with select_connection:
        select_cursor.execute(select_query)
        values = select_cursor.fetchall()
        if not keys:
            print(values)
            return values
        names = [description[0] for description in select_cursor.description]
        keyed_values = [dict(zip(names, row)) for row in values]
    print(keyed_values)
    return keyed_values


def insert_multiple_objects_into_db(data_objects: list, table_name: str):
    object_zero = data_objects[0]
    value_keys = tuple(object_zero.__annotations__.keys())
    insert_data = [[row.__dict__[key] for key in value_keys] for row in data_objects]
    insert_query = f"INSERT INTO {table_name} {str(value_keys)} VALUES ({str('?, '*len(value_keys))[:-2]})"
    insert_connection, insert_cursor = db_connection_and_cursor()
    with insert_connection:
        insert_cursor.executemany(insert_query, insert_data)
        insert_connection.commit()


def insert_one_object_into_db(data_object: object, table_name: str):
    value_keys = tuple(data_object.__annotations__.keys())
    insert_data = [data_object.__dict__[key] for key in value_keys]
    insert_query = f"INSERT INTO {table_name} {str(value_keys)} VALUES ({str('?, '*len(value_keys))[:-2]})"
    insert_connection, insert_cursor = db_connection_and_cursor()
    with insert_connection:
        insert_cursor.execute(insert_query, insert_data)
        insert_connection.commit()


def clear_table(table_name: str):
    delete_query = f"""DELETE FROM {table_name}"""
    delete_connection, delete_cursor = db_connection_and_cursor()
    with delete_connection:
        delete_cursor.execute(delete_query)
        delete_connection.commit()


def insert_into_db(data: dict, table_name: str):
    value_keys = tuple(data.keys())
    insert_data = [data[key] for key in value_keys]
    insert_query = f"INSERT INTO {table_name} {str(value_keys)} VALUES ({str('?, '*len(value_keys))[:-2]})"
    insert_connection, insert_cursor = db_connection_and_cursor()
    with insert_connection:
        insert_cursor.execute(insert_query, insert_data)
        insert_connection.commit()
