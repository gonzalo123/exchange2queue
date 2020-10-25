import logging

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    level='INFO',
    datefmt='%d/%m/%Y %X')

logger = logging.getLogger(__name__)
