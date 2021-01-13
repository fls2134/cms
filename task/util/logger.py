import logging

"""
    Formatter
"""
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d:%H:%M:%S')

"""
    Set task logger
"""

logger = logging.getLogger('TASK_LOG')
logger.setLevel(logging.DEBUG)
stream_log = logging.StreamHandler()
stream_log.setFormatter(formatter)
logger.addHandler(stream_log)
# if disabled
# logger.disabled = True
