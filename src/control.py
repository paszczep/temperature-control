from drive import ContainerValuesDriver
from measure import read_all_thermometers, Measure
from database import insert_multiple_objects_into_db, clear_table, select_from_db
from api import Container, Thermometer, Task


def initialize_database():
    containers = [Container(name=container.name) for container in ContainerValuesDriver().read_values()]
    clear_table(container_table := Container.__tablename__)
    insert_multiple_objects_into_db(containers, container_table)

    thermometers = [
        Thermometer(
            device_id=thermometer.device_id,
            device_name=thermometer.device_name
        ) for thermometer in read_all_thermometers()]
    clear_table(thermometer_table := Thermometer.__tablename__)
    insert_multiple_objects_into_db(thermometers, thermometer_table)


def relevant_thermometers(the_container_id) -> list[int]:
    relationships = select_from_db(Thermometer.__relationship__)
    print(relationships)
    thermometers = [rel['measure_id'] for rel in relationships]
    return thermometers


def retrieve_tasks(task_id: int = 1):
    tasks = [Task(**task) for task in select_from_db(Task.__tablename__)]
    task = [task for task in tasks if task.id == task_id].pop()
    print(task)
    relationships = select_from_db(Task.__relationship__)
    container = [rel['container_id'] for rel in relationships if rel['task_id'] == task_id].pop()
    print(container)
    relevant_ids = relevant_thermometers(container)
    relevant_measures = [measure for measure in read_all_thermometers() if measure.device_id in relevant_ids]
    print(relevant_measures)


if __name__ == "__main__":
    retrieve_tasks()
