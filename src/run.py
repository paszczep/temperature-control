from .execute import run_lambda
import logging
import sys

logging.basicConfig(
    stream=sys.stdout, level=logging.DEBUG,
    format='%(asctime)s: %(message)s'
)


def handler(event=None, context=None):
    logging.info('running lambda')
    run_lambda(event, context)

