from shioaji.base import BaseProps
from shioaji.constant import *


class _action(BaseProps):
    Buy = ACTION_BUY
    Sell = ACTION_SELL
    Update_Qty = 'UpdateQty'
    Update_Price = 'UpdatePrice'
    Cancel = 'Cancel'


class _stock_price_type(BaseProps):
    LimitPrice = STOCK_PRICE_TYPE_LIMITPRICE
    Close = STOCK_PRICE_TYPE_CLOSE
    LimitUp = STOCK_PRICE_TYPE_LIMITUP
    LimitDown = STOCK_PRICE_TYPE_LIMITDOWN


class _stock_order_type(BaseProps):
    Common = STOCK_ORDER_TYPE_COMMON
    BlockTrade = STOCK_ORDER_TYPE_BLOCKTRADE
    Fixing = STOCK_ORDER_TYPE_FIXING
    Odd = STOCK_ORDER_TYPE_ODD


class _stock_order_cond(BaseProps):
    Cash = STOCK_ORDER_COND_CASH
    Netting = STOCK_ORDER_COND_NETTING
    MarginTrading = STOCK_ORDER_COND_MARGINTRADING
    ShortSelling = STOCK_ORDER_COND_SHORTSELLING


class _stock_first_sell(BaseProps):
    Yes = STOCK_FIRST_SELL_YES
    No = STOCK_FIRST_SELL_NO


class _StockOrderProps(BaseProps):
    action = _action
    price_type = _stock_price_type
    order_type = _stock_order_type
    order_cond = _stock_order_cond
    first_sell = _stock_first_sell


class _future_price_type(BaseProps):
    LMT = FUTURES_PRICE_TYPE_LMT
    MKT = FUTURES_PRICE_TYPE_MKT
    MKP = FUTURES_PRICE_TYPE_MKP


class _future_order_type(BaseProps):
    ROD = ORDER_TYPE_ROD
    IOC = ORDER_TYPE_IOC
    FOK = ORDER_TYPE_FOK


class _future_octype(BaseProps):
    Auto = FUTURES_OCTYPE_AUTO
    NewPosition = FUTURES_OCTYPE_NEWPOSITION
    Cover = FUTURES_OCTYPE_COVER
    DayTrade = FUTURES_OCTYPE_DAYTRADE


class _future_callput(BaseProps):
    Futures = FUTURES_CALLPUT_FUT
    Call = FUTURES_CALLPUT_CALL
    Put = FUTURES_CALLPUT_PUT


class _FutureOrderPorps(BaseProps):
    action = _action
    price_type = _future_price_type
    order_type = _future_order_type
    octype = _future_octype
    callput = _future_callput
    octype = _future_octype


class OrderProps(BaseProps):
    Stock = _StockOrderProps
    Future = _FutureOrderPorps
