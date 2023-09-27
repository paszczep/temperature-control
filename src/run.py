from .execute import run_lambda
import logging
import sys

# logging.basicConfig(
#     stream=sys.stderr,
#     level=logging.INFO,
#     format='%(asctime)s: %(message)s'
# )

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event=None, context=None):
    logging.info('running lambda')
    run_lambda(event, context)

