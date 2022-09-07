import time
import typing
from shioaji.base import BaseModel, StrictInt
from shioaji.constant import (
    Action,
    Currency,
    Exchange,
    OptionRight,
    SecurityType,
    DayTrade,
)
from enum import Enum

__all__ = (
    "BaseContract",
    "Contract",
    "Index",
    "Stock",
    "Future",
    "Option",
    "Contracts",
    "ComboBase",
    "ComboContract",
)


class FetchStatus(str, Enum):
    Fetched = "Fetched"
    Fetching = "Fetching"
    Unfetch = "Unfetch"


class BaseContract(BaseModel):
    security_type: SecurityType
    exchange: Exchange
    code: str

    def astype(self):
        return _CONTRACTTYPE.get(self.security_type, self.__class__)(**self.dict())

    def __getattr__(self, attr):
        if not attr.startswith("_"):
            self._block(attr)
        value = object.__getattribute__(self, attr)
        if value:
            return value


class Contract(BaseContract):
    symbol: str = ""
    name: str = ""
    category: str = ""
    currency: Currency = Currency.TWD
    delivery_month: str = ""
    delivery_date: str = ""
    strike_price: typing.Union[StrictInt, float] = 0
    option_right: OptionRight = OptionRight.No
    underlying_kind: str = ""
    underlying_code: str = ""
    unit: typing.Union[StrictInt, float] = 0
    multiplier: int = 0
    limit_up: float = 0.0
    limit_down: float = 0.0
    reference: float = 0.0
    update_date: str = ""
    margin_trading_balance: int = 0
    short_selling_balance: int = 0
    day_trade: DayTrade = DayTrade.No


class ComboBase(Contract):
    action: Action


class ComboContract(BaseModel):
    legs: typing.List[ComboBase]


class Index(Contract):
    security_type: SecurityType = SecurityType.Index


class Stock(Contract):
    security_type: SecurityType = SecurityType.Stock
    limit_up: float = 0.0
    limit_down: float = 0.0
    reference: float = 0.0
    margin_trading_balance: int = 0
    short_selling_balance: int = 0
    update_date: str = ""


class Future(Contract):
    security_type: SecurityType = SecurityType.Future
    exchange: Exchange = Exchange.TAIFEX
    limit_up: float = 0.0
    limit_down: float = 0.0
    reference: float = 0.0
    update_date: str = ""


class Option(Contract):
    security_type: SecurityType = SecurityType.Option
    exchange: Exchange = Exchange.TAIFEX
    limit_up: float = 0.0
    limit_down: float = 0.0
    reference: float = 0.0
    update_date: str = ""


ProductTypeDict = dict(
    IndexContracts="exchange",
    StockContracts="exchange",
    FutureContracts="category",
    OptionContracts="category",
)

StreamProductTypeDict = dict(
    StreamIndexContracts="exchange",
    StreamStockContracts="exchange",
    StreamFutureContracts="category",
    StreamOptionContracts="category",
)

_CONTRACTTYPE = {
    SecurityType.Index: Index,
    SecurityType.Stock: Stock,
    SecurityType.Future: Future,
    SecurityType.Option: Option,
}


class BaseIterContracts:
    def __iter__(self):
        for key in self.__slots__:
            if not key.startswith("_"):
                yield getattr(self, key)

    def __bool__(self):
        return True if list(self.keys()) else False

    def keys(self):
        return (key for key in self.__slots__ if not key.startswith("_"))

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __eq__(self, other: Contract) -> bool:
        if isinstance(other, BaseModel):
            return self.__dict__ == other.__dict__
        else:
            return self.__dict__ == other


class ProductContracts(BaseIterContracts):
    def __init__(self, contracts):
        type_key = ProductTypeDict[self.__class__.__name__]
        key_list = list(sorted(set([con[type_key] for con in contracts])))
        self._code2contract = {}
        self._fetched = False
        self.__slots__ = key_list + ["_code2contract", "_fetched"]
        if contracts:
            for key in key_list:
                contract = [con for con in contracts if con[type_key] == key]
                mulcontract = MultiContract(key, contract)
                setattr(self, key, mulcontract)
                self._code2contract.update(getattr(self, key)._code2contract)
        else:
            self.__slots__ = ["_code2contract", "_fetched"]

    def post_init(self, contracts: BaseIterContracts):
        self.__slots__ = contracts.__slots__
        for s in contracts.__slots__:
            setattr(self, s, getattr(contracts, s))

    def __repr__(self):
        self._block()
        return "({})".format(", ".join(self.__slots__[:-2]))

    def __getitem__(self, key):
        if not key.startswith("_"):
            self._block()
        return getattr(self, key, self._code2contract.get(key, None))

    def get(self, key, default=None):
        return getattr(self, key, self._code2contract.get(key, default))

    def _block(self):
        if not self._fetched:
            for _ in range(100):
                time.sleep(0.3)
                if self._fetched:
                    break

    def __getattr__(self, attr):
        if not attr.startswith("_"):
            self._block()
        if object.__getattribute__(self, attr):
            return object.__getattribute__(self, attr)

    def __getattribute__(self, item):
        return super(ProductContracts, self).__getattribute__(item)


class StreamProductContracts(ProductContracts):
    def __init__(self, contracts):
        type_key = StreamProductTypeDict[self.__class__.__name__]
        key_list = list(sorted(set([con[type_key] for con in contracts])))
        self._code2contract = {}
        self._fetched = False
        self._page_list = []
        self._max_page = 0
        self.__slots__ = key_list + [
            "_code2contract",
            "_fetched",
            "_page_list",
            "_max_page",
        ]
        if contracts:
            for key in key_list:
                contract = [con for con in contracts if con[type_key] == key]
                mulcontract = StreamMultiContract(key, contract)
                setattr(self, key, mulcontract)
                self._code2contract.update(getattr(self, key)._code2contract)
        else:
            self.__slots__ = [
                "_code2contract",
                "_fetched",
                "_page_list",
                "_max_page",
            ]

    def __repr__(self):
        self._block()
        return "({})".format(", ".join(self.__slots__[:-4]))

    def append(self, value):
        slots = list(self.__slots__[:-4])
        key_list = value.__slots__[:-4]
        for key in key_list:
            if key in slots:
                getattr(self, key).append(getattr(value, key))
            else:
                mulcontract = getattr(value, key)
                setattr(self, key, mulcontract)
                self._code2contract.update(getattr(self, key)._code2contract)

        slots.extend([key for key in key_list if key not in slots])
        self.__slots__ = sorted(slots) + [
            "_code2contract",
            "_fetched",
            "_page_list",
            "_max_page",
        ]
        self._code2contract.update(value._code2contract)

    def set_status_fetched(self):
        self._fetched = True


class IndexContracts(ProductContracts):
    pass


class StockContracts(ProductContracts):
    pass


class FutureContracts(ProductContracts):
    pass


class OptionContracts(ProductContracts):
    pass


class StreamIndexContracts(StreamProductContracts):
    pass


class StreamStockContracts(StreamProductContracts):
    pass


class StreamFutureContracts(StreamProductContracts):
    pass


class StreamOptionContracts(StreamProductContracts):
    pass


class MultiContract(BaseIterContracts):
    def __init__(self, name, contracts):
        self._name = name
        self._code2contract = {}
        self.__slots__ = []
        for cont in contracts:
            self.__slots__.append(cont["symbol"])
            setattr(self, cont["symbol"], Contract(**cont).astype())
            self._code2contract.update({cont["code"]: getattr(self, cont["symbol"])})
        self.__slots__ += ["_name", "_code2contract"]

    def __getitem__(self, key):
        return getattr(self, key, self._code2contract.get(key, None))

    def get(self, key, default=None):
        return getattr(self, key, self._code2contract.get(key, default))

    def __repr__(self):
        return "{}({})".format(self._name, (", ").join(self.__slots__[:-2]))


class StreamMultiContract(MultiContract):
    def append(self, value):
        slots = self.__slots__[:-2]
        key_list = value.__slots__[:-2]
        for key in key_list:
            mulcontract = getattr(value, key)
            setattr(self, key, mulcontract)

        slots.extend(key_list)
        self.__slots__ = slots + ["_name", "_code2contract"]
        self._code2contract.update(value._code2contract)


SecurityType2ProductContratcs = {
    SecurityType.Index: StreamIndexContracts,
    SecurityType.Stock: StreamStockContracts,
    SecurityType.Future: StreamFutureContracts,
    SecurityType.Option: StreamOptionContracts,
}


def get_product_contracts(security_type: SecurityType) -> ProductContracts:
    return SecurityType2ProductContratcs.get(security_type, ProductContracts)


class Contracts(BaseModel, BaseIterContracts):
    Indexs: StreamIndexContracts
    Stocks: StreamStockContracts
    Futures: StreamFutureContracts
    Options: StreamOptionContracts
    status: FetchStatus = FetchStatus.Unfetch

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **kwargs):
        super().__init__(
            **dict(
                Indexs=StreamIndexContracts(kwargs.get("Indexs", {})),
                Stocks=StreamStockContracts(kwargs.get("Stocks", {})),
                Futures=StreamFutureContracts(kwargs.get("Futures", {})),
                Options=StreamOptionContracts(kwargs.get("Options", {})),
            )
        )

    def set_contracts(self, security_type: SecurityType, contracts: ProductContracts):
        origin_contracts = getattr(self, "{}s".format(security_type.name))
        origin_contracts.post_init(contracts)

    def _set_fetched(self):
        self.Futures._fetched = True
        self.Options._fetched = True
        self.Stocks._fetched = True
        self.Indexs._fetched = True
        self.status = FetchStatus.Fetched

    def __iter__(self):
        return self._iter(to_dict=False, exclude={"status"})