import os

SJCLIENT_SOL_HOST = os.environ.get("SJCLIENT_SOL_HOST", "")
SJCLIENT_SOL_VPN = os.environ.get("SJCLIENT_SOL_VPN", "")
SJCLIENT_SOL_USER = os.environ.get("SJCLIENT_SOL_USER", "")
SJCLIENT_SOL_PASSWORD = os.environ.get("SJCLIENT_SOL_PASSWORD", "")

SJCLIENT_SOL_CONNECT_TIMEOUT_MS = int(
    os.environ.get("SJCLIENT_SOL_CONNECT_TIMEOUT_MS", 3000)
)
SJCLIENT_SOL_RECONNECT_RETRIES = int(
    os.environ.get("SJCLIENT_SOL_RECONNECT_RETRIES", 10)
)
SJCLIENT_SOL_KEEP_ALIVE_MS = int(os.environ.get("SJCLIENT_SOL_KEEP_ALIVE_MS", 3000))
SJCLIENT_SOL_RECONNECT_RETRY_WAIT = int(
    os.environ.get("SJCLIENT_SOL_RECONNECT_RETRY_WAIT", 3000)
)
SJCLIENT_SOL_KEEP_ALIVE_LIMIT = int(os.environ.get("SJCLIENT_SOL_KEEP_ALIVE_LIMIT", 3))


SJCLIENT_SOL_HOST_STAG = os.environ.get("SJCLIENT_SOL_HOST_STAG", "")
SJCLIENT_SOL_VPN_STAG = os.environ.get("SJCLIENT_SOL_VPN_STAG", "")
SJCLIENT_SOL_USER_STAG = os.environ.get("SJCLIENT_SOL_USER_STAG", "")
SJCLIENT_SOL_PASSWORD_STAG = os.environ.get("SJCLIENT_SOL_PASSWORD_STAG", "")

SJCLIENT_SOL_CONNECT_TIMEOUT_MS_STAG = int(
    os.environ.get("SJCLIENT_SOL_CONNECT_TIMEOUT_MS_STAG", 3000)
)
SJCLIENT_SOL_RECONNECT_RETRIES_STAG = int(
    os.environ.get("SJCLIENT_SOL_RECONNECT_RETRIES_STAG", 10)
)
SJCLIENT_SOL_KEEP_ALIVE_MS_STAG = int(
    os.environ.get("SJCLIENT_SOL_KEEP_ALIVE_MS_STAG", 3000)
)
SJCLIENT_SOL_RECONNECT_RETRY_WAIT_STAG = int(
    os.environ.get("SJCLIENT_SOL_RECONNECT_RETRY_WAIT_STAG", 3000)
)
SJCLIENT_SOL_KEEP_ALIVE_LIMIT_STAG = int(
    os.environ.get("SJCLIENT_SOL_KEEP_ALIVE_LIMIT_STAG", 3)
)