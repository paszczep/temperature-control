from .execute import run_lambda


def handler(event=None, context=None):
    run_lambda(event, context)

