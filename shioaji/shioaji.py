import datetime as dt
import typing
from pathlib import Path
from importlib import reload
from sentry_sdk import configure_scope

from shioaji import config
from shioaji.account import Account, FutureAccount, StockAccount
from shioaji.backend import _http
from shioaji.backend.solace import SolaceAPI
from shioaji.backend.solace.utils import (
    get_contracts_filename,
    load_contracts_file,
    mockca,
    new_contracts,
    read_config,
)
from shioaji.backend.solace.tick import TickSTKv1, TickFOPv1
from shioaji.backend.solace.bidask import BidAskSTKv1, BidAskFOPv1
from shioaji.backend.solace.quote import QuoteSTKv1
from shioaji.constant import (
    Action,
    Exchange,
    OrderState,
    SecurityType,
    Status,
    Unit,
    ScannerType,
    TicksQueryType,
)
from shioaji.contracts import (
    BaseContract,
    ComboContract,
    Contract,
    Contracts,
    FetchStatus,
    Future,
    Index,
    Option,
    Stock,
)
from shioaji.position import (
    FuturePosition,
    Position,
    ProfitLoss,
    Settlement,
    AccountBalance,
    ProfitLossDetail,
    StockPosition,
)
from shioaji.data import (
    DailyQuotes,
    ShortStockSource,
    Snapshot,
    Ticks,
    Kbars,
    CreditEnquire,
    ChangePercentRank,
)
from shioaji.reserve import (
    EarmarkStocksDetailResponse,
    ReserveEarmarkingResponse,
    ReserveStockResponse,
    ReserveStocksDetailResponse,
    ReserveStocksSummaryResponse,
)
from shioaji.order import (
    ComboOrder,
    Order,
    StrictInt,
    Trade,
    ComboTrade,
    conint,
)
from shioaji.orderprops import OrderProps
from shioaji.utils import log, set_error_tracking
from shioaji.error import AccountNotSignError


class Shioaji:
    """shioaji api

    Functions:
        login
        activate_ca
        list_accounts
        set_default_account
        get_account_margin
        get_account_openposition
        get_account_settle_profitloss
        get_stock_account_funds
        get_stock_account_unreal_profitloss
        get_stock_account_real_profitloss
        place_order
        update_order
        update_status
        list_trades

    Objects:
        Quote
        Contracts
        Order
    """

    def __init__(
        self,
        backend: str = "http",
        simulation: bool = False,
        proxies: typing.Dict[str, str] = {},
        currency: str = "NTD",
    ):
        """initialize Shioaji to start trading

        Args:
            backend (str): {http, socket}
                use http or socket as backend currently only support http, async socket backend coming soon.
            simulation (bool):
                - False: to trading on real market (just use your Sinopac account to start trading)
                - True: become simulation account(need to contract as to open simulation account)
            proxies (dict): specific the proxies of your https
                ex: {'https': 'your-proxy-url'}
            currency (str): {NTX, USX, NTD, USD, HKD, EUR, JPY, GBP}
                set the default currency for display
        """
        self._http = _http(False, proxies)
        read_config()
        reload(config)

        self.quote: SolaceAPI = None
        self._api = self._http
        self.stock_account = None
        self.futopt_account = None
        self.OrderProps = OrderProps
        self.Contracts = getattr(self._http, "Contracts", None)
        self.Order = Order
        self.ComboOrder = ComboOrder
        self._currency = currency
        self._tft = False
        self.simulation = simulation
        self.proxies = proxies

        # TODO: change it to False if paper trade go production
        self._simu_to_stag = simulation
        self._setup_solace()

    @property
    def tft(self) -> bool:
        return self._tft

    @tft.setter
    def tft(self, tft: bool):
        self._solace.tft = self._tft = tft

    def _create_solace(self, server: str = "prod"):
        """create solace api object
        Args:
            server (str): {prod, stag}
        """
        prefix = "SJCLIENT_SOL_"
        suffix = ""
        if server == "stag":
            suffix = "_STAG"

        sol_conf = {
            arg: getattr(config, "{}{}{}".format(prefix, arg.upper(), suffix), "")
            for arg in SolaceAPI.__init__.__code__.co_varnames
            if arg != "self"
        }
        sol_conf["simulation"] = self.simulation
        sol_conf["proxies"] = self.proxies
        solace = SolaceAPI(**sol_conf)
        return solace

    def _setup_solace(self):
        if self._simu_to_stag:
            self._solace = self._create_solace("stag")
            # solace_implicit: connect to release server
            self._solace_implicit = self._create_solace()
        else:
            self._solace = self._create_solace()
            self._solace_implicit = None

        if self.simulation:
            self._solace.activated_ca = mockca()

        self.quote = self._solace

    def _trace_log(self, trade: Trade):
        if not self.simulation:
            return
        if dt.datetime.utcnow().weekday() >= 5:
            return
        elif dt.datetime.utcnow().hour < 6:
            return
        elif dt.datetime.utcnow().hour >= 10:
            return

        if not self._simu_to_stag:
            if not trade.order.account.signed:
                if not self._solace_implicit:
                    self._solace_implicit = self._create_solace("stag")
                    simulation_token = self._solace.session._token
                    _ = self._solace_implicit.simulation_login(
                        simulation_token,
                        person_id=self._solace._person_id,
                        subscribe_trade=False,
                    )
                self._solace_implicit.trace_log(trade)
        else:
            self._solace.trace_log(trade)

    def fetch_contracts(
        self,
        contract_download: bool = False,
        contracts_timeout: int = 0,
        contracts_cb: typing.Callable[[], None] = None,
    ):
        self.Contracts = self._solace.Contracts = new_contracts()
        contract_file = get_contracts_filename()
        todayfile_exist = False
        if contract_file.exists():
            today8am = dt.datetime.now().replace(hour=8, minute=0, second=0).timestamp()
            filetime = contract_file.stat().st_mtime
            todayfile_exist = True if today8am <= filetime else False
        if contract_download or not todayfile_exist:
            self._solace.fetch_all_contract(contracts_timeout, contracts_cb)
        else:
            if self.Contracts.status == FetchStatus.Unfetch:
                self.Contracts.status = FetchStatus.Fetching
                self.Contracts = self._solace.Contracts = load_contracts_file()
                self.Contracts.status = FetchStatus.Fetched
                if contracts_cb:
                    for securitytype in SecurityType:
                        contracts_cb(securitytype)
            else:
                pass

    def login(
        self,
        person_id: str,
        passwd: str,
        hashed: bool = False,
        fetch_contract: bool = True,
        contracts_timeout: int = 0,
        contracts_cb: typing.Callable[[], None] = None,
        subscribe_trade: bool = True,
    ) -> None:
        """login to trading server

        Args:
            person_id (str): Same as your eleader, ileader login id(usually your person ID)
            passwd  (str): the password of your eleader login password(not ca password)

        """
        with configure_scope() as scope:
            scope.user = dict(id=person_id)

        if self._simu_to_stag:
            # solace_implicit: will connect to release server
            _ = self._solace_implicit.login(person_id, passwd, hashed, subscribe_trade)
            simulation_token = self._solace_implicit.session._token
            self._solace_implicit.logout()

            accounts, contract_download = self._solace.simulation_login(
                simulation_token,
                person_id,
                subscribe_trade,
            )
            web_token = ""
        else:
            accounts, contract_download, web_token = self._solace.login(
                person_id, passwd, hashed, subscribe_trade
            )

        if accounts:
            with configure_scope() as scope:
                scope.user = dict(id=person_id, username=accounts[0].username)
        error_tracking = self._solace.error_tracking(person_id)
        set_error_tracking(self.simulation, error_tracking)
        if fetch_contract:
            self.fetch_contracts(contract_download, contracts_timeout, contracts_cb)
        self.stock_account = self._solace.default_stock_account
        self.futopt_account = self._solace.default_futopt_account
        if not self.simulation:
            try:
                # self._http.login(person_id, passwd)
                self._http.token_login(person_id, web_token, self._solace._public_ip)
                if self.futopt_account and self.futopt_account.signed:
                    self.AccountMargin = self._http.get_account_margin(
                        self._currency, "1", self.futopt_account
                    )
                    self.AccountOpenPosition = self._http.get_account_openposition(
                        "0", "0", self.futopt_account
                    )
                    self.AccountSettleProfitLoss = (
                        self._http.get_account_settle_profitloss(
                            "0",
                            "Y",
                            (dt.date.today() + dt.timedelta(days=10)).strftime(
                                "%Y%m%d"
                            ),
                            dt.date.today().strftime("%Y%m%d"),
                            self._currency,
                            self.futopt_account,
                        )
                    )
            except Exception as e:
                log.error(e)

        return accounts

    def logout(self):
        """logout shioaji api"""
        res = self._solace.logout()
        return res

    def subscribe_trade(self, account: Account) -> bool:
        res = self._solace.subscribe_trade(account, True)
        return res

    def unsubscribe_trade(self, account: Account) -> bool:
        res = self._solace.subscribe_trade(account, False)
        return res

    def activate_ca(self, ca_path: str, ca_passwd: str, person_id: str, store: int = 0):
        """activate your ca for trading

        Args:
            ca_path (str):
                the path of your ca, support both absloutely and relatively path, use same ca with eleader
            ca_passwd (str): password of your ca
            person_id (str): the ca belong which person ID
        """
        res = self._solace.activate_ca(ca_path, ca_passwd, person_id, store)
        return res

    def list_accounts(self):
        """list all account you have"""
        return self._solace.list_accounts()

    def set_default_account(self, account):
        """set default account for trade when place order not specific

        Args:
            account (:obj:Account):
                choice the account from listing account and set as default
        """
        if isinstance(account, StockAccount):
            self._solace.default_stock_account = account
            self.stock_account = account
        elif isinstance(account, FutureAccount):
            self._solace.default_futopt_account = account
            self.futopt_account = account

    def get_account_margin(self, currency="NTD", margin_type="1", account={}):
        """query margin

        Args:
            currency (str):{NTX, USX, NTD, USD, HKD, EUR, JPY, GBP}
                the margin calculate in which currency
                - NTX: 約當台幣
                - USX: 約當美金
                - NTD: 新台幣
                - USD: 美元
                - HKD: 港幣
                - EUR: 歐元
                - JPY: 日幣
                - GBP: 英鎊
            margin_type (str): {'1', '2'}
                query margin type
                - 1 : 即時
                - 2 : 風險
        """
        account = account if account else self.futopt_account
        return self._api.get_account_margin(currency, margin_type, account)

    def get_account_openposition(self, product_type="0", query_type="0", account={}):
        """query open position

        Args:
            product_type (str): {0, 1, 2, 3}
                filter product type of open position
                - 0: all
                - 1: future
                - 2: option
                - 3: usd base
            query_type (str): {0, 1}
                query return with detail or summary
                - 0: detail
                - 1: summary
        """
        account = account if account else self.futopt_account
        return self._api.get_account_openposition(product_type, query_type, account)

    def get_account_settle_profitloss(
        self,
        product_type="0",
        summary="Y",
        start_date="",
        end_date="",
        currency="",
        account={},
    ):
        """query settlement profit loss

        Args:
            product_type (str): {0, 1, 2}
                filter product type of open position
                - 0: all
                - 1: future
                - 2: option
            summary (str): {Y, N}
                query return with detail or summary
                - Y: summary
                - N: detail
            start_date (str): the start date of query range format with %Y%m%d
                ex: 20180101
            end_date (str): the end date of query range format with %Y%m%d
                ex: 20180201
            currency (str): {NTD, USD, HKD, EUR, CAD, BAS}
                the profit loss calculate in which currency
                - NTD: 新台幣
                - USD: 美元
                - HKD: 港幣
                - EUR: 歐元
                - CAD: 加幣
                - BAS: 基幣
        """
        account = account if account else self.futopt_account
        start_date = (
            start_date
            if start_date
            else (dt.date.today() + dt.timedelta(days=10)).strftime("%Y%m%d")
        )
        end_date = end_date if end_date else dt.date.today().strftime("%Y%m%d")
        currency = currency if currency else self._currency
        return self._api.get_account_settle_profitloss(
            product_type, summary, start_date, end_date, currency, account
        )

    def get_stock_account_funds(self, include_tax=" ", account: StockAccount = None):
        """query stock account funds

        Args:
            include_tax (str): {' ', '1'}
                - ' ': tax included
                - '1': tax excluded
        """
        account = account if account else self.stock_account
        return self._api.get_stock_account_funds(include_tax, account)

    def get_stock_account_unreal_profitloss(
        self, stock_type="A", currency="A", filter_rule=" ", account=None
    ):
        """query stock account unreal profitloss

        Args:
            stock_type (str): {A, 0, 1, 2, R}
                - 'A': 全部
                - '0': 現-上市櫃
                - '1': 資
                - '2': 券
                - 'R': 興櫃
            currency (str): {A, NTD, CNY}
                - A: 全部
                - NTD: 新台幣
                - CNY: 人民幣
            filter_rule (str): {' ', 1, 2, 3}
                - ' ': default, no filter
                - '1': filter delisting stock
                - '2': tax excluded
                - '3': filter delisting stock and tax excluded
        """
        account = account if account else self.stock_account
        return self._api.get_stock_account_unreal_profitloss(
            stock_type, currency, filter_rule, account
        )

    def get_stock_account_real_profitloss(
        self,
        stock_type="A",
        start_date="",
        end_date="",
        currency="A",
        filter_rule=" ",
        account=None,
    ):
        """query stock account real profitloss

        Args:
            stock_type (str): {A, 0, 1, 2, R}
                - 'A': 全部
                - '0': 現-上市櫃
                - '1': 資
                - '2': 券
                - 'R': 興櫃
            start_date (str):
                the start date of query range format with %Y%m%d
                ex: 20180201
            end_date (str):
                the end date of query range format with %Y%m%d
                ex: 20180201
            currency (str): {A, NTD, CNY}
                - A: 全部
                - NTD: 新台幣
                - CNY: 人民幣
            filter_rule (str): {' ', 1}
                - ' ': default, no filter
                - '1': filter cost is 0
        """
        account = account if account else self.stock_account
        start_date = (
            start_date
            if start_date
            else (dt.date.today() + dt.timedelta(days=10)).strftime("%Y%m%d")
        )
        end_date = end_date if end_date else dt.date.today().strftime("%Y%m%d")
        return self._api.get_stock_account_real_profitloss(
            stock_type, start_date, end_date, currency, filter_rule, account
        )

    def place_order(
        self,
        contract: Contract,
        order: Order,
        timeout: int = 5000,
        cb: typing.Callable[[Trade], None] = None,
    ) -> Trade:
        """placing order

        Args:
            contract (:obj:Shioaji.Contract):
            order (:obj:Shioaji.Order):
                pass Shioaji.Order object to place order
        """
        if not order.account:
            if isinstance(contract, Future) or isinstance(contract, Option):
                order.account = self.futopt_account
            elif isinstance(contract, Stock):
                order.account = self.stock_account
            else:
                log.error("Please provide the account place to.")
                return None

        trade = self._solace.place_order(contract, order, timeout, cb)

        if self.simulation:
            self._trace_log(trade)

        return trade

    def update_order(
        self,
        trade: Trade,
        price: typing.Union[StrictInt, float] = None,
        qty: int = None,
        timeout: int = 5000,
        cb: typing.Callable[[Trade], None] = None,
    ) -> Trade:
        """update the order price or qty

        Args:
            trade (:obj:Trade):
                pass place_order return Trade object to update order
            price (float): the price you want to replace
            qty (int): the qty you want to subtract
        """
        trade = self._solace.update_order(trade, price, qty, timeout, cb)
        return trade

    def cancel_order(
        self,
        trade: Trade,
        timeout: int = 5000,
        cb: typing.Callable[[Trade], None] = None,
    ) -> Trade:
        """cancel order

        Args:
            trade (:obj:Trade):
                pass place_order return Trade object to cancel order
        """
        trade = self._solace.cancel_order(trade, timeout, cb)
        return trade

    def place_comboorder(
        self,
        combo_contract: ComboContract,
        order: ComboOrder,
        timeout: int = 5000,
        cb: typing.Callable[[ComboTrade], None] = None,
    ):
        """placing combo order

        Args:
            combocontract (:obj:List of legs):
            order (:obj:Shioaji.Order):
                pass Shioaji.Order object to place combo order
        """
        if not len(combo_contract.legs) == 2:
            log.error("Just allow order with two contracts.")
        if not order.account:
            if not self.futopt_account:
                log.error("Please provide the future account.")
            else:
                order.account = self.futopt_account
                trade = self._solace.place_comboorder(
                    combo_contract, order, timeout, cb
                )
                return trade

    def cancel_comboorder(
        self,
        combotrade: ComboTrade,
        timeout: int = 5000,
        cb: typing.Callable[[ComboTrade], None] = None,
    ) -> Trade:
        """cancel combo order

        Args:
            trade (:obj:Trade):
                pass place_order return Trade object to cancel order
        """
        trade = self._solace.cancel_comboorder(combotrade, timeout, cb)
        return trade

    def update_status(
        self,
        account: Account = None,
        trade: Trade = None,
        timeout: int = 5000,
        cb: typing.Callable[[typing.List[Trade]], None] = None,
    ):
        """update status of all trades you have"""
        if trade:
            self._solace.update_status(
                trade.order.account,
                seqno=trade.order.seqno,
                timeout=timeout,
                cb=cb,
            )
        elif account and account.signed:
            self._solace.update_status(account, timeout=timeout, cb=cb)
        else:
            if self.stock_account and self.stock_account.signed:
                self._solace.update_status(self.stock_account, timeout=timeout, cb=cb)
            if self.futopt_account and self.futopt_account.signed:
                self._solace.update_status(self.futopt_account, timeout=timeout, cb=cb)

    def stock_reserve_summary(
        self,
        account: Account,
        timeout: int = 5000,
        cb: typing.Callable[[ReserveStocksSummaryResponse], None] = None,
    ) -> ReserveStocksSummaryResponse:
        if account.signed:
            resp = self._solace.stock_reserve_summary(account, timeout, cb)
            return resp
        else:
            raise AccountNotSignError(account)

    def stock_reserve_detail(
        self,
        account: Account,
        timeout: int = 5000,
        cb: typing.Callable[[ReserveStocksDetailResponse], None] = None,
    ) -> ReserveStocksDetailResponse:
        if account.signed:
            resp = self._solace.stock_reserve_detail(account, timeout, cb)
            return resp
        else:
            raise AccountNotSignError(account)

    def reserve_stock(
        self,
        account: Account,
        contract: Contract,
        share: int,
        timeout: int = 5000,
        cb: typing.Callable[[ReserveStockResponse], None] = None,
    ) -> ReserveStockResponse:
        if account.signed:
            resp = self._solace.reserve_stock(account, contract, share, timeout, cb)
            return resp
        else:
            raise AccountNotSignError(account)

    def earmarking_detail(
        self,
        account: Account,
        timeout: int = 5000,
        cb: typing.Callable[[EarmarkStocksDetailResponse], None] = None,
    ) -> EarmarkStocksDetailResponse:
        if account.signed:
            resp = self._solace.earmarking_detail(account, timeout, cb)
            return resp
        else:
            raise AccountNotSignError(account)

    def reserve_earmarking(
        self,
        account: Account,
        contract: Contract,
        share: int,
        price: float,
        timeout: int = 5000,
        cb: typing.Callable[[ReserveEarmarkingResponse], None] = None,
    ) -> ReserveEarmarkingResponse:
        if account.signed:
            resp = self._solace.reserve_earmarking(
                account, contract, share, price, timeout, cb
            )
            return resp
        else:
            raise AccountNotSignError(account)

    def update_combostatus(
        self,
        account: Account = None,
        timeout: int = 5000,
        cb: typing.Callable[[typing.List[ComboTrade]], None] = None,
    ):
        if account and account.signed:
            if account.account_type == "F":
                self._solace.update_combostatus(account, timeout=timeout, cb=cb)
            else:
                log.error("Please provide the future account.")
        else:
            if self.futopt_account and self.futopt_account.signed:
                self._solace.update_combostatus(
                    self.futopt_account, timeout=timeout, cb=cb
                )
            else:
                log.error("Please provide the future account.")

    def list_positions(
        self,
        account: Account = None,
        unit: Unit = Unit.Common,
        timeout: int = 5000,
        cb: typing.Callable[
            [typing.List[typing.Union[StockPosition, FuturePosition]]], None
        ] = None,
    ) -> typing.List[typing.Union[StockPosition, FuturePosition]]:
        """query account of unrealized gain or loss
        Args:
            account (:obj:Account):
                choice the account from listing account (Default: stock account)
        """
        if account and account.signed:
            position = self._solace.list_positions(
                account, unit=unit, timeout=timeout, cb=cb
            )
        else:
            if self.stock_account and self.stock_account.signed:
                position = self._solace.list_positions(
                    self.stock_account, unit=unit, timeout=timeout, cb=cb
                )
        return position

    def list_profit_loss(
        self,
        account: Account = None,
        begin_date: str = "",
        end_date: str = "",
        timeout: int = 5000,
        cb: typing.Callable[[typing.List[ProfitLoss]], None] = None,
    ) -> typing.List[ProfitLoss]:
        """query account of profit loss

        Args:
            account (:obj:Account):
                choice the account from listing account (Default: stock account)
            begin_date (str): the start date of query profit loss (Default: today)
            end_date (str): the end date of query profit loss (Default: today)
        """
        if account and account.signed:
            return self._solace.list_profit_loss(
                account, begin_date, end_date, timeout=timeout, cb=cb
            )
        else:
            if self.stock_account and self.stock_account.signed:
                return self._solace.list_profit_loss(
                    self.stock_account,
                    begin_date,
                    end_date,
                    timeout=timeout,
                    cb=cb,
                )

    def list_profit_loss_detail(
        self,
        account: Account = None,
        detail_id: int = 0,
        timeout: int = 5000,
        cb: typing.Callable[[typing.List[ProfitLossDetail]], None] = None,
    ):
        """query account of profit loss detail

        Args:
            account (:obj:Account):
                choice the account from listing account (Default: stock account)
            detail_id (int): the id is from ProfitLoss object, ProfitLoss is from list_profit_loss
        """
        if account and account.signed:
            return self._solace.list_profit_loss_detail(
                account, detail_id, timeout=timeout, cb=cb
            )
        else:
            if self.stock_account and self.stock_account.signed:
                return self._solace.list_profit_loss_detail(
                    self.stock_account, detail_id, timeout=timeout, cb=cb
                )

    def list_settlements(
        self,
        account: Account = None,
        timeout: int = 5000,
        cb: typing.Callable[[typing.List[Settlement]], None] = None,
    ) -> typing.List[Settlement]:
        """query stock account of settlements"""
        if self.stock_account and self.stock_account.signed:
            return self._solace.list_settlements(
                self.stock_account, timeout=timeout, cb=cb
            )

    def list_trades(self) -> typing.List[Trade]:
        """list all trades"""
        return self._solace.trades

    def list_combotrades(self) -> typing.List[ComboTrade]:
        """list all combotrades"""
        return self._solace.combotrades

    def ticks(
        self,
        contract: BaseContract,
        date: str = dt.date.today().strftime("%Y-%m-%d"),
        query_type: TicksQueryType = TicksQueryType.AllDay,
        time_start: typing.Union[str, dt.time] = None,
        time_end: typing.Union[str, dt.time] = None,
        last_cnt: int = 0,
        timeout: int = 30000,
        cb: typing.Callable[[Ticks], None] = None,
    ) -> Ticks:
        """get contract tick volumn

        Arg:
            contract (:obj:Shioaji.BaseContract)
            date (str): "2020-02-02"
        """
        ticks = self._solace.ticks(
            contract,
            date,
            query_type,
            time_start,
            time_end,
            last_cnt,
            timeout,
            cb,
        )
        return ticks

    def kbars(
        self,
        contract: BaseContract,
        start: str = (dt.date.today() - dt.timedelta(days=1)).strftime("%Y-%m-%d"),
        end: str = dt.date.today().strftime("%Y-%m-%d"),
        timeout: int = 30000,
        cb: typing.Callable[[Kbars], None] = None,
    ) -> Kbars:
        """get Kbar

        Arg:
            contract (:obj:Shioaji.BaseContract)
            start (str): "2020-02-02"
            end (str): "2020-06-02"
        """
        kbars = self._solace.kbars(contract, start, end, timeout, cb)
        return kbars

    def daily_quotes(
        self,
        date: dt.date = dt.date.today(),
        exclude: bool = True,
        timeout: int = 5000,
        cb: typing.Callable[[DailyQuotes], None] = None,
    ) -> DailyQuotes:
        """get daily quote

        Args:
            date (:datetime:date):
                date for quote (Default: today)
            exclude (:bool):
                exclude warrant data (Default: True)
        """
        daily_quotes = self._solace.daily_quotes(date, exclude, timeout, cb)
        return daily_quotes

    def snapshots(
        self,
        contracts: typing.List[typing.Union[Option, Future, Stock, Index]],
        timeout: int = 30000,
        cb: typing.Callable[[Snapshot], None] = None,
    ) -> typing.List[Snapshot]:
        """get contract snapshot info

        Arg:
            contract (:obj:List of contract)
        """
        snapshots = self._solace.snapshots(contracts, timeout, cb)
        return snapshots

    def scanners(
        self,
        scanner_type: ScannerType,
        ascending: bool = True,
        date: str = None,
        count: conint(ge=1, le=200) = 100,
        timeout: int = 30000,
        cb: typing.Callable[
            [typing.Union[typing.List[ChangePercentRank]]], None
        ] = None,
    ) -> typing.Union[typing.List[ChangePercentRank]]:
        """get contract snapshot info

        Arg:
            contract (:obj:List of contract)
        """
        scanners = self._solace.scanners(
            scanner_type, ascending, date, count, timeout, cb
        )
        return scanners

    def credit_enquires(
        self,
        contracts: typing.List[Stock],
        timeout: int = 30000,
        cb: typing.Callable[[CreditEnquire], None] = None,
    ) -> typing.List[CreditEnquire]:
        """get contract snapshot info

        Arg:
            contract (:obj:List of contract)
        """
        credit_enquires = self._solace.credit_enquires(contracts, timeout, cb)
        return credit_enquires

    def short_stock_sources(
        self,
        contracts: typing.List[Stock],
        timeout: int = 5000,
        cb: typing.Callable[[ShortStockSource], None] = None,
    ) -> typing.List[ShortStockSource]:
        """get contract snapshot info

        Arg:
            contract (:obj:List of contract)
        """
        short_stock_sources = self._solace.short_stock_sources(contracts, timeout, cb)
        return short_stock_sources

    def account_balance(
        self,
        timeout: int = 5000,
        cb: typing.Callable[[AccountBalance], None] = None,
    ):
        """get stock account balance"""
        return self._solace.account_balance(self.stock_account, timeout=timeout, cb=cb)

    def set_order_callback(
        self, func: typing.Callable[[OrderState, dict], None]
    ) -> None:
        self._solace.set_order_callback(func)

    def set_session_down_callback(self, func: typing.Callable[[], None]) -> None:
        self.quote.set_session_down_callback(func)

    def set_context(self, context: typing.Any):
        self.quote.set_context(context)

    def on_tick_stk_v1(
        self, bind: bool = False
    ) -> typing.Callable[[Exchange, TickSTKv1], None]:
        def wrap_deco(
            func: typing.Callable[[Exchange, TickSTKv1], None]
        ) -> typing.Callable[[Exchange, TickSTKv1], None]:
            self.quote.set_on_tick_stk_v1_callback(func, bind)
            return func

        return wrap_deco

    def on_tick_fop_v1(
        self, bind: bool = False
    ) -> typing.Callable[[Exchange, TickFOPv1], None]:
        def wrap_deco(
            func: typing.Callable[[Exchange, TickFOPv1], None]
        ) -> typing.Callable[[Exchange, TickFOPv1], None]:
            self.quote.set_on_tick_fop_v1_callback(func, bind)
            return func

        return wrap_deco

    def on_bidask_stk_v1(
        self, bind: bool = False
    ) -> typing.Callable[[Exchange, BidAskSTKv1], None]:
        def wrap_deco(
            func: typing.Callable[[Exchange, BidAskSTKv1], None]
        ) -> typing.Callable[[Exchange, BidAskSTKv1], None]:
            self.quote.set_on_bidask_stk_v1_callback(func, bind)
            return func

        return wrap_deco

    def on_bidask_fop_v1(
        self, bind: bool = False
    ) -> typing.Callable[[Exchange, BidAskFOPv1], None]:
        def wrap_deco(
            func: typing.Callable[[Exchange, BidAskFOPv1], None]
        ) -> typing.Callable[[Exchange, BidAskFOPv1], None]:
            self.quote.set_on_bidask_fop_v1_callback(func, bind)
            return func

        return wrap_deco

    def on_quote_stk_v1(
        self, bind: bool = False
    ) -> typing.Callable[[Exchange, QuoteSTKv1], None]:
        def wrap_deco(
            func: typing.Callable[[Exchange, QuoteSTKv1], None]
        ) -> typing.Callable[[Exchange, QuoteSTKv1], None]:
            self.quote.set_on_quote_stk_v1_callback(func, bind)
            return func

        return wrap_deco

    def on_quote(
        self, func: typing.Callable[[str, dict], None]
    ) -> typing.Callable[[str, dict], None]:
        self.quote.set_quote_callback(func)
        return func

    def on_event(
        self, func: typing.Callable[[int, int, str, str], None]
    ) -> typing.Callable[[int, int, str, str], None]:
        self.quote.set_event_callback(func)
        return func

    def on_session_down(
        self, func: typing.Callable[[], None]
    ) -> typing.Callable[[], None]:
        self.quote.set_session_down_callback(func)
        return func

    def __del__(self):
        self._solace.__del__()
