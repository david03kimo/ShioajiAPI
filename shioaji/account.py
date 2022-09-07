from enum import Enum

from shioaji.base import BaseModel

__all__ = ("Account StockAccount FutureAccount").split()


class AccountType(str, Enum):
    Stock = "S"
    Future = "F"
    H = "H"  # TODO declear


class BaseAccount(BaseModel):
    account_type: AccountType
    person_id: str
    broker_id: str
    account_id: str
    signed: bool = False

    def astype(self):
        return _ACCTTYPE.get(self.account_type, self.__class__)(**self.dict())


class Account(BaseAccount):
    username: str = ""


class StockAccount(Account):
    account_type: AccountType = AccountType.Stock


class FutureAccount(Account):
    account_type: AccountType = AccountType.Future


_ACCTTYPE = {"S": StockAccount, "F": FutureAccount}
