import argparse
from control import initialize_database, read_temperature, set_temperature, check_containers


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--initialize", action='store_true', help="initialize database")
    parser.add_argument("--check", action='store_true', help="check and update containers")
    parser.add_argument("--task", action='store', help="read and control task id")
    parser.add_argument("--set", action='store', help="set id")

    args = parser.parse_args()

    if args.initialize:
        initialize_database(),
    elif args.task:
        read_temperature(task_id=args.task)
    elif args.set:
        print(args.set)
        set_temperature(set_id=args.set)
    elif args.check:
        check_containers()


if __name__ == '__main__':
    run()
