import typing
from datetime import datetime

from shioaji.base import BaseModel, StrictInt
from shioaji.account import Account
from shioaji.contracts import Contract
from shioaji.error import BaseError


class ErrorResponse(BaseModel):
    status_code: str
    detail: str = ""


class ReserveStockSummary(BaseModel):
    contract: Contract
    available_share: int
    reserved_share: int


class ReserveStocksSummary(BaseModel):
    stocks: typing.List[ReserveStockSummary]
    account: Account


class ReserveStocksSummaryResponse(BaseModel):
    response: ReserveStocksSummary
    error: ErrorResponse = None


class ReserveStockDetail(BaseModel):
    contract: Contract
    share: int
    order_datetime: datetime
    status: bool
    info: str


class ReserveStocksDetail(BaseModel):
    stocks: typing.List[ReserveStockDetail]
    account: Account


class ReserveStocksDetailResponse(BaseModel):
    response: ReserveStocksDetail
    error: ErrorResponse = None


class CASign(BaseModel):
    signature: str
    plain_text: str


class ReserveOrder(BaseModel):
    share: int
    ca: CASign


class ReserveOrderResp(BaseModel):
    contract: Contract
    account: Account
    share: int
    status: bool
    info: str


class ReserveStockResponse(BaseModel):
    response: ReserveOrderResp
    error: ErrorResponse = None


class EarmarkStockDetail(BaseModel):
    contract: Contract
    share: int
    price: typing.Union[StrictInt, float]
    amount: int
    order_datetime: datetime
    status: bool
    info: str

class EarmarkStocksDetail(BaseModel):
    stocks: typing.List[EarmarkStockDetail]
    account: Account

class EarmarkStocksDetailResponse(BaseModel):
    response: EarmarkStocksDetail
    error: ErrorResponse = None


class EarmarkingOrder(BaseModel):
    share: int
    price: typing.Union[StrictInt, float]
    ca: CASign


class EarmarkingOrderResp(BaseModel):
    contract: Contract
    account: Account
    share: int
    price: typing.Union[StrictInt, float]
    status: bool
    info: str

class ReserveEarmarkingResponse(BaseModel):
    response: EarmarkingOrderResp
    error: ErrorResponse = None