import argparse
from control import initialize_database, read_temperature, set_temperature


def deffo_run():
    parser = argparse.ArgumentParser()

    function_map = {'initialize': initialize_database,
                    'task': read_temperature,
                    'set': set_temperature
                    }

    parser.add_argument('command', choices=function_map.keys())
    parser.add_argument("id", help="task or set id", type=str, required=False, default=None)

    args = parser.parse_args()

    func = function_map[args.command]
    func()


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--initialize", action='store_true', help="initialize database")
    parser.add_argument("--task", action='store_true', help="read and control task id")
    parser.add_argument("--set", action='store_true', help="set id")

    args = parser.parse_args()
    if args.initialize:
        initialize_database()

    if args.task:
        read_temperature(task_id=args.id)

    if args.set:
        set_temperature(set_id=args.id)


if __name__ == '__main__':
    run()
