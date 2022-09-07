from shioaji.base import BaseModel
from shioaji.constant import Action, StockOrderCond, TradeType


class Position(BaseModel):
    code: str
    direction: Action
    quantity: int
    price: float
    last_price: float
    pnl: float
    yd_quantity: int
    cond: StockOrderCond = StockOrderCond.Cash


class StockPosition(Position):
    margin_purchase_amount: int
    collateral: int
    short_sale_margin: int
    interest: int


class FuturePosition(Position):
    pass


class ProfitLoss(BaseModel):
    id: int
    code: str
    seqno: str
    dseq: str
    quantity: int
    price: float
    pnl: float
    pr_ratio: float
    cond: StockOrderCond
    date: str


class Settlement(BaseModel):
    t_money: float
    t1_money: float
    t2_money: float
    t_day: str
    t1_day: str
    t2_day: str


class AccountBalance(BaseModel):
    acc_balance: float
    date: str
    errmsg: str


class ProfitLossDetail(BaseModel):
    date: str
    cond: StockOrderCond
    code: str
    quantity: int
    price: float
    cost: int
    dseq: str
    rep_margintrading_amt: int
    rep_collateral: int
    rep_margin: int
    fee: int
    interest: int
    tax: int
    shortselling_fee: int
    currency: str
    trade_type: TradeType
