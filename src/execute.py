import argparse
from control import initialize_database, read_temperature

parser = argparse.ArgumentParser()
parser.add_argument("--initialize", help="initialize database")
parser.add_argument("task", help="read and control task id", type=int)
args = parser.parse_args()
if args.initialize:
    initialize_database()

if args.task:
    print(args.task)
    read_temperature(task_id=args.task)