import datetime
import hashlib
import hmac
import logging
import time
from datetime import datetime
import pandas as pd
from urllib.parse import urlencode
import websocket
import \
    threading  # because socket runs forever, if it were to be used on main thread, it would block the rest of the program forever. Therefore we have to run it on a different thread
import json
import requests
from pprint import pprint
import typing
from models import *
from strategies import TechnicalStrategy, BreakoutStrategy, MacdEmaStrategy

from connectors.binance_spot import BinanceSpotClient

logger = logging.getLogger()


class BinanceMarginClient:
    def __init__(self, spot: BinanceSpotClient, public_key: str, secret_key: str, testnet: bool):  # constructor
        self.spot_client = spot
        if testnet:
            self._base_url = "https://testnet.binance.vision/api"
            self._wss_url = "wss://stream.binancefuture.com/ws"
        else:
            self._base_url = "https://api.binance.com"
            self._wss_url = "wss://stream.binance.com:9443/ws"

        self._public_key = public_key
        self._secret_key = secret_key

        self._headers = {'X-MBX-APIKEY': self._public_key}

        self.Balances: typing.Dict[str, MarginBalance] = dict()
        self._make_snapshot()  # gets a snapshot of user balances

        self.contracts: typing.Dict[str, Contract] = self.get_contracts()  # gets exchange information about symbols and their trading
        self.prices = dict()

        self.strategies: typing.Dict[int, typing.Union[TechnicalStrategy, BreakoutStrategy, MacdEmaStrategy]] = dict()

        self.logs = []

        ##### WEBSOCKET #####
        self._ws_id = 1
        self.ws: websocket.WebSocketApp
        self.reconnect = True

        t = threading.Thread(target=self._start_ws)
        t.start()

        logger.info("Binance Margin Client was successfully initialized")

    def _add_log(self, msg: str):
        # logger.info("%s", msg)
        self.logs.append({
            "log": msg,
            "displayed": False
        })

    def _generate_signature(self, data: typing.Dict) -> str:
        return hmac.new(self._secret_key.encode(), urlencode(data).encode(), hashlib.sha256).hexdigest()

    def _make_request(self, method: str, endpoint: str, data: typing.Dict):
        if method == 'GET':
            try:
                response = requests.get(self._base_url + endpoint, params=data, headers=self._headers)
            except Exception as e:
                logger.error("Connection error while making %s request to %s: %s", method, endpoint, e)
                return None

        elif method == 'POST':
            try:
                response = requests.post(self._base_url + endpoint, params=data, headers=self._headers)
            except Exception as e:
                logger.error("Connection error while making %s request to %s: %s", method, endpoint, e)
                return None

        elif method == 'DELETE':
            try:
                response = requests.delete(self._base_url + endpoint, params=data, headers=self._headers)
            except Exception as e:
                logger.error("Connection error while making %s request to %s: %s", method, endpoint, e)
                return None

        else:
            raise ValueError()

        if response.status_code == 200:
            return response.json()
        else:
            logger.error("Error while making %s request to %s:%s (error code %s)", method, endpoint, response.json(),
                         response.status_code)
            return None

    def get_time(self):
        data = dict()
        response = self._make_request("GET", "/api/v3/time", data)
        print(response)
        print(int(time.time()) * 1000)

    def _make_snapshot(self):
        # makes a snapshot of user balances by making transfers to help balance_websocket work

        # spot to margin
        data = dict()
        data['asset'] = "USDT"
        data['amount'] = 0.5
        data['type'] = 1
        data['timestamp'] = int(time.time() * 1000)
        data['signature'] = self._generate_signature(data)
        x = self._make_request("POST", "/sapi/v1/margin/transfer", data=data)

        # back to spot
        data2 = dict()
        data2['asset'] = "USDT"
        data2['amount'] = 0.5
        data2['type'] = 2
        data2['timestamp'] = int(time.time() * 1000)
        data2['signature'] = self._generate_signature(data2)
        self._make_request("POST", "/sapi/v1/margin/transfer", data=data2)


    def get_contracts(self) -> typing.Dict[str, Contract]:
        # gets exchange information about symbols and their trading
        logger.info("Running get_contracts")
        data = {
            'symbols': "[\"BTCUSDT\",\"ETHUSDT\",\"ADAUSDT\",\"DOGEUSDT\",\"LTCUSDT\",\"BNBUSDT\"]"
        }
        exchange_info = self._make_request("GET", "/api/v3/exchangeInfo", data)

        contracts = {}
        if exchange_info is not None:
            for contract_data in exchange_info['symbols']:
                if "MARGIN" in contract_data['permissions']:
                    contracts[contract_data['symbol']] = Contract(contract_data, "Margin")

        return contracts

    def get_bid_ask(self, contract: Contract) -> typing.Dict[str, float]:
        # bid and ask price of given contract

        bid_and_ask = self._make_request("GET", "/api/v3/ticker/bookTicker", {'symbol': contract.symbol})

        if bid_and_ask is not None:
            if contract.symbol not in self.prices:  # if not in dictionary already, make
                self.prices[contract.symbol] = {
                    "bid": float(bid_and_ask['bidPrice']),
                    "ask": float(bid_and_ask['askPrice'])
                }
            else:  # if already there, update
                self.prices[contract.symbol]["bid"] = float(bid_and_ask['bidPrice'])
                self.prices[contract.symbol]["ask"] = float(bid_and_ask['askPrice'])
            return self.prices[contract.symbol]

    def get_historical_candles(self, contract: Contract, interval: str) -> typing.List[Candle]:
        # Kline/Candlestick Data, Kline/candlestick bars for a symbol.
        # Klines are uniquely identified by their open time.
        # also saves the data in a dataframe with same name as symbol

        logger.info("Running get_historical_candles")
        data = dict()
        data['symbol'] = contract.symbol
        data['interval'] = interval
        data['limit'] = 1000

        response = self._make_request("GET", "/api/v3/klines", data)

        candles = []
        if response is not None:
            for c in response:
                candles.append(Candle(c,interval,"Margin"))

        df = []
        for i in candles:
            dt = datetime.utcfromtimestamp(i.timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
            x = [dt, i.open, i.high, i.low, i.close, i.volume]
            df.append(x)

            # saving this
            path = 'E:\Ishaan\'s Bot\saved candles\\'
            pd.DataFrame(df, columns=['time', 'open', 'high', 'low', 'close', 'volume']).to_csv(
                path + contract.symbol + ".csv", index=False)

        return candles

    #  still have to make place order and cancel order and order status

    ########### WEBSOCKET ############

    def _start_ws(self):
        self.ws = websocket.WebSocketApp(self._wss_url,
                                         on_open=self._on_open,
                                         on_error=self._on_error,
                                         on_message=self._on_message)
        while True:
            try:
                if self.reconnect:
                    self.ws.run_forever()
                else:
                    break
            except Exception as e:
                logger.error("Binance error in run_forever() method: %s", e)
            time.sleep(2)

    def _on_open(self, ws):
        logger.info("Binance Margin Websocket connection opened")

        lst = list(self.contracts.values())
        self.subscribe_channel(lst, "bookTicker")
        self.subscribe_channel(lst, "aggTrade")  # somesome message about this aggTrade at vid 41, 7:28

    def _on_close(self, ws):
        logger.warning("Binance Margin Websocket connection closed")

    def _on_error(self, ws, msg: str):
        logger.error("Binance Margin Websocket connection error: %s", msg)

    def _on_message(self, ws, msg: str):
        data = dict()
        data = json.loads(msg)

        """
        {
          "u":400900217,     // order book updateId
          "s":"BNBUSDT",     // symbol
          "b":"25.35190000", // best bid price
          "B":"31.21000000", // best bid qty
          "a":"25.36520000", // best ask price
          "A":"40.66000000"  // best ask qty
        }
        """
        if 'result' in data:
            return

        if "e" not in data and "s" in data:
            symbol = data['s']
            if symbol not in self.prices:  # if not in dictionary already, make
                self.prices[symbol] = {
                    "bid": float(data['b']),
                    "ask": float(data['a'])
                }
            else:  # if already there, update
                self.prices[symbol]["bid"] = float(data['b'])
                self.prices[symbol]["ask"] = float(data['a'])

            # PnL Calculation
            try:
                for b_index, strat in self.strategies.items():
                    if strat.contract.symbol == symbol:
                        for trade in strat.trades:
                            if trade.status == "open" and trade.entry_price is not None:
                                if trade.side == "long":
                                    trade.pnl = (self.prices[symbol]['bid'] - trade.entry_price) * trade.quantity
                                if trade.side == "short":
                                    trade.pnl = (trade.entry_price - self.prices[symbol]['ask']) * trade.quantity
            except RuntimeError as e:
                logger.error(("Error while looping through margin strategies: %s", e))

        elif data['e'] == "aggTrade":
            symbol = data['s']

            for key, strat in self.strategies.items():
                if strat.contract.symbol == symbol:
                    res = strat.parse_trades(float(data['p']), float(data['q']), data['T'])  # price, quantity, time
                    strat.check_trade(res)
        # if symbol == 'BTCUSDT':
        #     self._add_log(
        #         symbol + " " + str(self.prices[symbol]['bid']) + "/" + str(self.prices[symbol]['ask']))

    def subscribe_channel(self, contracts: typing.List[Contract], channel: str):
        # we can subscribe to the "!bookTicker" channel to subscribe to allll the symbols in bookTicker
        data = dict()  # https://binance-docs.github.io/apidocs/futures/en/#live-subscribing-unsubscribing-to-streams
        data['method'] = "SUBSCRIBE"
        data['params'] = []

        for contract in contracts:
            data['params'].append(contract.symbol.lower() + "@" + channel)
        data['id'] = self._ws_id
        self._ws_id += 1

        try:
            self.ws.send(json.dumps(data))
            logger.info("Successfully subscribed")
        except Exception as e:
            logger.error("Binance Margin Websocket error while subscribing to %s %s updates: %s", len(contracts), channel,
                         e)



    ##### FROM STRATEGY MODULE #####


    def get_trade_size(self, contract: Contract, price: float, usdt_input: float):
        balance = self.spot_client.Balances
        if balance is not None:
            if 'USDT' in balance:
                balance = balance['USDT'].free
                if balance < usdt_input:
                    return None
            else:
                return None
        else:
            return None

        trade_size = usdt_input / price  #USDT amount to invest
        trade_size = round((round(trade_size / contract.tick_size) * contract.tick_size), 8)
        logger.info("MARGIN- signal for %s: current USDT balance = %s, trade size = %s", contract.symbol, balance, trade_size)

        return trade_size


    def _transfer_funds(self, amount: float, direction: int):
        """
        :param amount: amount of USDT
        :param direction: 1 for spot -> margin, 2 for margin -> spot
        :return: transactionId or None
        """

        data = dict()
        data['asset'] = "USDT"
        data['amount'] = amount
        data['type'] = direction
        data['timestamp'] = int(time.time() * 1000)
        data['signature'] = self._generate_signature(data)

        transfer_status = self._make_request("POST", "/sapi/v1/margin/transfer", data=data)

        if transfer_status is not None:
            logger.info(f"Transferred {amount} USDT from {'spot' if direction==1 else 'margin'} to {'margin' if direction==1 else 'spot'}")
            return transfer_status['tranId']
        else:
            return None

    def _borrow_funds(self, asset: str, amount: float):

        data = dict()
        data['asset'] = asset
        data['amount'] = amount
        data['timestamp'] = int(time.time() * 1000)
        data['signature'] = self._generate_signature(data)

        borrow_status = self._make_request("POST", "/sapi/v1/margin/loan", data)

        if borrow_status is not None:
            logger.info(f"Borrowed {amount} {asset} on Binance Margin")
            return borrow_status['tranId']
        else:
            return None

    def _repay_funds(self, asset: str, amount: float):
        data = dict()
        data['asset'] = asset
        amount = min(amount, self.Balances[asset].free)

        data['amount'] = amount
        data['timestamp'] = int(time.time() * 1000)
        data['signature'] = self._generate_signature(data)

        repay_status = self._make_request("POST", "/sapi/v1/margin/repay", data)
        if repay_status is not None:
            logger.info(f"Repayed {amount} {asset} on Binance Margin")
            return repay_status['tranId']
        else:
            return None

    def _margin_balance(self):
        data = dict()
        data['timestamp'] = int(time.time() * 1000)
        data['signature'] = self._generate_signature(data)

        response = self._make_request("GET", "/sapi/v1/margin/account", data)

        pprint(response)

########### ORDERS ###########

    def place_order(self, contract: Contract, order_type: str, quantity: float, side: str,  usdt_total: float, entry_or_exit: str, price=None, tif=None) -> OrderStatus:

        data = dict()
        ask = self.get_bid_ask(contract)['bid']
        print(f"{contract.symbol}, quantity = {quantity}, at total cost: {ask * quantity}")

        data['symbol'] = contract.symbol
        data['side'] = side.upper()  # BUY / SELL
        data['quantity'] = quantity
        data['type'] = order_type.upper()

        if tif is not None:
            data['timeInForce'] = tif

        order_status = None
        if entry_or_exit == "ENTRY":
            order_status = self._entry_order(data=data, usdt_total=usdt_total)
        elif entry_or_exit == "EXIT":
            order_status = self._exit_order(data=data, usdt_total=usdt_total)

        if order_status is not None:
            order_status = OrderStatus(order_status)
        else:
            print("TRADE FAILED!")
        return order_status

    def _entry_order(self, data: typing.Dict, usdt_total):
        side = data['side']
        if side == "BUY":
            self._transfer_funds(usdt_total+3, 1)
            data['timestamp'] = int(time.time() * 1000)
            data['signature'] = self._generate_signature(data)
            order_status = self._make_request("POST", "/sapi/v1/margin/order", data)
            if order_status is None:
                self._transfer_funds(usdt_total+3, 2)
            return order_status

        elif side == "SELL":
            transfer_status = self._transfer_funds(usdt_total+3, 1)
            if transfer_status is None:
                return None

            borrow_status = self._borrow_funds(asset=data['symbol'][:-4], amount=data['quantity'])
            if borrow_status is None:
                return None

            data['timestamp'] = int(time.time() * 1000)
            data['signature'] = self._generate_signature(data)
            order_status = self._make_request("POST", "/sapi/v1/margin/order", data)

            if order_status is None:
                repay_status = self._repay_funds(asset=data['symbol'][:-4], amount=data['quantity'])
                if repay_status is None:
                    print("REPAY FAILED! PLEASE DO MANUALLY")
                self._transfer_funds(usdt_total+3, 2)
            return order_status

        else:
            return None


    def _exit_order(self, data: typing.Dict, usdt_total):
        side = data['side']
        if side == "SELL":
            asset = data['symbol'][:-4]
            qty = min(data['quantity'], self.Balances[asset].free)
            qty = int(qty * pow(10, self.contracts[data['symbol']].base_asset_decimals)) / pow(10, self.contracts[data['symbol']].base_asset_decimals)

            data1 = {'symbol': data['symbol'], 'side': data['side'],
                     'quantity': qty, 'type': data['type'],
                     'timestamp': int(time.time() * 1000)}
            data1['signature'] = self._generate_signature(data1)
            order_status = self._make_request("POST", "/sapi/v1/margin/order", data1)
            if order_status is None:
                return None
            self._transfer_funds(int(usdt_total), 2)
            return order_status

        if side == "BUY":
            data['timestamp'] = int(time.time() * 1000)
            data['signature'] = self._generate_signature(data)
            order_status = self._make_request("POST", "/sapi/v1/margin/order", data)
            if order_status is None:
                return None

            repay_status = self._repay_funds(asset=data['symbol'][:-4], amount=data['quantity'])
            if repay_status is None:
                print("REPAY FAILED! PLEASE DO MANUALLY")
                return order_status

            transfer_status = self._transfer_funds(int(usdt_total), 2)
            if transfer_status is None:
                print("TRANSFER FROM MARGIN TO SPOT FAILED! PLEASE DO MANUALLY")

            return order_status

        else:
            return None

    def cancel_order(self, contract: Contract, order_id: int) -> OrderStatus:
        data = dict()
        data['orderId'] = order_id
        data['symbol'] = contract.symbol
        data['timestamp'] = int(time.time() * 1000)
        data['signature'] = self._generate_signature(data)

        order_status = self._make_request("DELETE", "/api/v3/order", data)

        if order_status is not None:
            order_status = OrderStatus(order_status)

        return order_status


    def get_order_status(self, contract: Contract, order_id: int) -> OrderStatus:
        data = dict()
        data['timestamp'] = int(time.time() * 1000)
        data['symbol'] = contract.symbol
        data['orderId'] = order_id
        data['signature'] = self._generate_signature(data)

        order_status = self._make_request("GET", "/api/v3/order", data)

        print("")
        print(order_status)
        print("")

        if order_status is not None:
            order_status = OrderStatus(order_status)

        return order_status