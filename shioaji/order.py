import typing
import datetime

from shioaji.base import BaseModel, conint, StrictInt, constr
from shioaji.account import Account
from shioaji.contracts import Contract, ComboContract
from shioaji.constant import (
    Action,
    FuturesPriceType,
    FuturesOrderType,
    FuturesOCType,
    StockPriceType,
    StockOrderType,
    StockOrderCond,
    StockFirstSell,
    Status,
    TFTStockOrderLot,
    TFTOrderType,
    TFTStockPriceType,
)


class Deal(BaseModel):
    seq: str
    price: typing.Union[StrictInt, float]
    quantity: int
    ts: int


class OrderStatus(BaseModel):
    id: str = ""
    status: Status
    status_code: str = ""
    web_id: str = "" 
    order_datetime: datetime.datetime = None
    msg: str = ""
    modified_time: datetime.datetime = None
    modified_price: typing.Union[StrictInt, float] = 0
    order_quantity: int = 0
    deal_quantity: int = 0
    cancel_quantity: int = 0
    deals: typing.List[Deal] = None


class ComboStatus(OrderStatus):
    deals: typing.Dict[str, typing.List[Deal]] = None


class BaseOrder(BaseModel):
    action: Action
    price: typing.Union[StrictInt, float]
    quantity: conint(gt=0)
    id: str = ""
    seqno: str = ""
    ordno: str = ""
    account: Account = None
    custom_field: constr(max_length=6) = ""
    ca: str = ""

    def __repr_args__(self):
        return [
            (k, v)
            for k, v in self._iter(to_dict=False, exclude_defaults=True, exclude={"ca"})
        ]


class FuturesOrder(BaseOrder):
    price_type: FuturesPriceType
    order_type: FuturesOrderType
    octype: FuturesOCType = FuturesOCType.Auto


class StockOrder(BaseOrder):
    price_type: StockPriceType
    order_type: StockOrderType
    order_cond: StockOrderCond = StockOrderCond.Cash
    first_sell: StockFirstSell = StockFirstSell.No


class TFTStockOrder(BaseOrder):
    price_type: TFTStockPriceType
    order_type: TFTOrderType
    order_lot: TFTStockOrderLot = TFTStockOrderLot.Common
    order_cond: StockOrderCond = StockOrderCond.Cash
    first_sell: StockFirstSell = StockFirstSell.No


class Order(StockOrder, FuturesOrder, TFTStockOrder):
    price_type: typing.Union[StockPriceType, FuturesPriceType, TFTStockPriceType]
    order_type: typing.Union[StockOrderType, FuturesOrderType, TFTOrderType]

    def __init__(
        self,
        price: typing.Union[StrictInt, int],
        quantity: conint(gt=0),
        action: Action,
        price_type: typing.Union[StockPriceType, FuturesPriceType, TFTStockPriceType],
        order_type: typing.Union[StockOrderType, FuturesOrderType, TFTOrderType],
        **kwargs
    ):
        super().__init__(
            **{
                **dict(
                    price=price,
                    quantity=quantity,
                    action=action,
                    price_type=price_type,
                    order_type=order_type,
                ),
                **kwargs,
            }
        )


class ComboOrder(FuturesOrder):
    action: Action = Action.Sell

    def __init__(
        self,
        price: typing.Union[StrictInt, int],
        quantity: conint(gt=0),
        price_type: FuturesPriceType,
        order_type: FuturesOrderType,
        action: Action = Action.Sell,
        **kwargs
    ):
        super().__init__(
            **{
                **dict(
                    price=price,
                    quantity=quantity,
                    action=action,
                    price_type=price_type,
                    order_type=order_type,
                ),
                **kwargs,
            }
        )


class Trade(BaseModel):
    contract: Contract
    order: BaseOrder
    status: OrderStatus

    def __init__(self, contract: Contract, order: BaseOrder, status: OrderStatus):
        super().__init__(**dict(contract=contract, order=order, status=status))


class ComboTrade(BaseModel):
    contract: ComboContract
    order: BaseOrder
    status: ComboStatus

    def __init__(self, contract: ComboContract, order: BaseOrder, status: ComboStatus):
        super().__init__(**dict(contract=contract, order=order, status=status))
