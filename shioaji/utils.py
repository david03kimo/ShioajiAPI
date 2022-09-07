import os
import logging
import sentry_sdk
from sentry_sdk.integrations.logging import SentryHandler
from shioaji.error import TokenError, SystemMaintenance
from pysolace import SolClient

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
SENTRY_URI = os.environ.get(
    "SENTRY_URI", "https://6aec6ef8db7148aa979a17453c0e44dd@sentry.io/1371618"
)
LOG_SENTRY = os.environ.get("LOG_SENTRY", "True")
SENTRY_LOG_LEVEL = os.environ.get("SENTRY_LOG_LEVEL", "ERROR").upper()
SJ_LOG_PATH = os.environ.get("SJ_LOG_PATH", "shioaji.log")

allow_log_level = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
assert LOG_LEVEL in allow_log_level, "LOG_LEVEL not allow, choice {}".format(
    (", ").join(allow_log_level)
)
LOGGING_LEVEL = getattr(logging, LOG_LEVEL)

log = logging.getLogger("shioaji")
log.setLevel(LOGGING_LEVEL)

console_handler = logging.FileHandler(SJ_LOG_PATH)
console_handler.setLevel(LOGGING_LEVEL)
log_formatter = logging.Formatter(
    "[%(levelname)1.1s %(asctime)s %(pathname)s:%(lineno)d:%(funcName)s] %(message)s"
)
console_handler.setFormatter(log_formatter)
log.addHandler(console_handler)


def set_error_tracking(simulation: bool, error_tracking: bool):
    if LOG_SENTRY and not simulation and error_tracking:
        sentry_sdk.init(SENTRY_URI)
        sentry_handeler = SentryHandler()
        sentry_handeler.setLevel(SENTRY_LOG_LEVEL)
        sentry_handeler.setFormatter(log_formatter)
        log.addHandler(sentry_handeler)


def raise_resp_error(status_code: int, resp: dict, session: SolClient):
    log.error(resp)
    detail = resp.get("response", {}).get("detail", "")
    if status_code == 401:
        session.disconnect()
        raise TokenError(status_code, detail)
    elif status_code == 503:
        raise SystemMaintenance(status_code, detail)
    else:
        raise Exception(resp)
