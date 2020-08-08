import asyncio
import logging
import os
import pathlib
import sys
from logging import handlers

import coloredlogs

logging.TRACE = 5
logging.addLevelName(logging.TRACE, 'TRACE')


def trace_logger(self: logging.Logger, msg: str, *args, **kwargs) -> None:
    """Log messages with the `TRACE` level."""
    if self.isEnabledFor(logging.TRACE):
        self._log(logging.TRACE, msg, args, **kwargs)


logging.Logger.trace = trace_logger

LOG_LEVEL = getattr(logging, os.environ.get('PDRP_LOG_LEVEL', ''), logging.INFO)
LOG_FORMAT = '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
log_formatter = logging.Formatter(LOG_FORMAT)

log_file = pathlib.Path('logs', 'prdp.log')
log_file.parent.mkdir(exist_ok=True)

file_handler = handlers.RotatingFileHandler(
    log_file,
    maxBytes=8388608,
    backupCount=7,
    encoding='utf-8'
)
file_handler.setFormatter(log_formatter)

root_logger = logging.getLogger()
root_logger.setLevel(LOG_LEVEL)
root_logger.addHandler(file_handler)

coloredlogs.DEFAULT_LEVEL_STYLES = {
    **coloredlogs.DEFAULT_LEVEL_STYLES,
    'trace': {'color': 246},
    'critical': {'background': 'red'},
    'debug': coloredlogs.DEFAULT_LEVEL_STYLES['info']
}
coloredlogs.DEFAULT_LOG_FORMAT = LOG_FORMAT

coloredlogs.install(logger=root_logger, stream=sys.stdout, level=LOG_LEVEL)

log = logging.getLogger(__name__)
log.setLevel(LOG_LEVEL)

if os.name == 'nt':
    log.info(
        'Setting WindowsSelectorEventLoopPolicy as Plex Discord Rich Presence is running on Windows'
    )
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
