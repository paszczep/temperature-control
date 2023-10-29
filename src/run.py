from src.internal_apis.execute import run_lambda
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event=None, context=None):
    logging.info('running lambda')
    run_lambda(event, context)
