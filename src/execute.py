import argparse
from control import initialize_database, read_relevant_temperature, set_process, check_containers
from pathlib import Path
from dotenv import load_dotenv
from os import getenv
from hashlib import sha256

dotenv_path = Path(__file__).parent.parent / 'prod.env'

load_dotenv(dotenv_path)


def key_hash(key: str) -> str:
    return sha256(key.encode("utf-8")).hexdigest()


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key_1", action='store', help="protect and serve")
    parser.add_argument("--key_2", action='store', help="protect and serve")
    parser.add_argument("--initialize", action='store_true', help="initialize database")
    parser.add_argument("--check", action='store_true', help="check and update containers")
    parser.add_argument("--task", action='store', help="read and control task id")
    parser.add_argument("--set", action='store', help="set id")

    args = parser.parse_args()

    if args.key_1 == key_hash(getenv('KEY_1')) and args.key_2 == getenv('KEY_2'):
        if args.initialize:
            initialize_database()
        elif args.task:
            read_relevant_temperature(task_id=args.task)
        elif args.set:
            set_process(set_id=args.set)
        elif args.check:
            check_containers()


if __name__ == '__main__':
    run()
