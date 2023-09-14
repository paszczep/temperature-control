from .execute import run_lambda
import logging

logging.basicConfig(
    format='%(asctime)s: %(message)s',
    level=logging.INFO,
)


def handler(event=None, context=None):
    run_lambda(event, context)

