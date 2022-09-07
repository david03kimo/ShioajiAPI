def inject_libpath():
    import os
    import sys
    from pathlib import Path

    dir_path = Path(__file__).parent
    libs_path = dir_path.joinpath(".libs")
    os.environ["PATH"] = ";".join(
        [p for p in [os.environ.get("PATH", ""), libs_path.as_posix()] if p]
    )
    os.environ["LD_LIBRARY_PATH"] = ";".join(
        [
            p
            for p in [
                os.environ.get("LD_LIBRARY_PATH", ""),
                libs_path.as_posix(),
            ]
            if p
        ]
    )
    if sys.version_info.major == 3 and sys.version_info.minor >= 8:
        if sys.platform == "win32":
            os.add_dll_directory(libs_path.as_posix())


inject_libpath()
del inject_libpath

from shioaji.shioaji import Shioaji
from shioaji.constant import Exchange
from shioaji.account import Account
from shioaji.backend.utils import on_quote, on_event
from shioaji.stream_data_type import (
    TickSTKv1,
    TickFOPv1,
    BidAskSTKv1,
    BidAskFOPv1,
    QuoteSTKv1,
)
from . import config
from .order import Order
from ._version import __version__
