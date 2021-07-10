import logging
import time
import typing
import pandas as pd
from threading import Timer
from models import *
# we needed to import clients to facilitate the coding process by telling which 'client' it is
# but this would lead to circular importing
# to avoid this

if typing.TYPE_CHECKING:
    from connectors.binance_spot import BinanceSpotClient
    from connectors.binance_margin import BinanceMarginClient

logger = logging.getLogger()
TF_EQUIV = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
}


class Strategy:
    def __init__(self, client: typing.Union["BinanceSpotClient", "BinanceMarginClient"], contract: Contract, exchange: str, timeframe: str, balance_pct: float, take_profit: float,
                 stop_loss: float, strat_name):

        self.client = client
        self.contract = contract
        self.exchange = exchange
        self.tf = timeframe
        self.balance_pct = balance_pct
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.tf_equiv = TF_EQUIV[timeframe] * 1000
        self.strat_name = strat_name

        self.ongoing_position = False

        self.candles: typing.List[Candle] = []
        self.trades: typing.List[Trade] = []
        self.logs = []

    def _add_log(self, msg: str):
        logger.info("%s", msg)
        self.logs.append({"log": msg, "displayed": False})

    def parse_trades(self, price: float, size: float, timestamp: int):
        # 1. update the same current candle
        # 2. new candle
        # 3. new candle + missing candles

        timestamp_diff = int(time.time() * 1000) - timestamp
        if timestamp_diff >= 2000:
            logger.warning("%s %s: %s milliseconds of difference bw the current time and trade time",
                           self.exchange, self.contract.symbol, timestamp_diff)
        last_candle = self.candles[-1]

        # SAME CANDLE
        if timestamp < last_candle.timestamp + self.tf_equiv:
            # update close price
            last_candle.close = price
            last_candle.volume += size

            if price > last_candle.high:
                last_candle.high = price
            elif price < last_candle.low:
                last_candle.low = price

            return "same_candle"

        # MISSING CANDLES
        elif timestamp >= last_candle.timestamp + 2 * self.tf_equiv:
            missing_candles = int((timestamp - last_candle.timestamp) / self.tf_equiv) - 1
            for missing in range(missing_candles):
                new_ts = last_candle.timestamp + self.tf_equiv
                candle_info = {
                    'ts': new_ts,
                    'open': last_candle.open,
                    'high': last_candle.high,
                    'low': last_candle.low,
                    'close': last_candle.close,
                    'volume': 0
                }

                new_candle = Candle(candle_info, self.tf, "parse_trade")
                self.candles.append(new_candle)
                last_candle = new_candle

            new_ts = last_candle.timestamp + self.tf_equiv
            candle_info = {
                'ts': new_ts,
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': size
            }

            new_candle = Candle(candle_info, self.tf, "parse_trade")
            self.candles.append(new_candle)

            logger.info("Added missing %s candles for %s %s (%s %s)", missing_candles, self.contract.symbol, self.tf,
                        timestamp, last_candle.timestamp)
            return "new_candle"

        # NEW CANDLE
        elif timestamp >= last_candle.timestamp + self.tf_equiv:
            new_ts = last_candle.timestamp + self.tf_equiv
            candle_info = {
                'ts': new_ts,
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': size
            }

            new_candle = Candle(candle_info, self.tf, "parse_trade")
            self.candles.append(new_candle)

            logger.info("Added new candle for %s %s", self.contract.symbol, self.tf)
            return "new_candle"

    def _check_order_status(self, order_id):
        order_status = self.client.get_order_status(self.contract, order_id)
        if order_status is not None:
            logger.info("%s order status: %s", self.exchange, order_status.status)

            if order_status.status == "filled":
                for trade in self.trades:
                    if trade.entry_id == order_id:
                        trade.entry_price = order_status.avg_price
                        break
                return

        t = Timer(2.0, lambda: self._check_order_status(order_id))
        t.start()

    def _open_position(self, signal_result: int):
        # market order
        trade_size = self.client.get_trade_size(self.contract, self.candles[-1].close, self.balance_pct)
        # number of units to buy

        if trade_size is None:
            return

        # we can log that signal has been triggered, but we can't let two threads interfere
        # since logger is on parent thread and this runs on websocket thread
        # Therefore we'll have list of logs, and use _update_ui of client

        order_side = "buy" if signal_result == 1 else "sell"
        position_side = "long" if signal_result == 1 else "short"

        self._add_log(f"{position_side.capitalize()} signal on {self.contract.symbol} {self.tf}")

        order_status = self.client.place_order(self.contract, "MARKET", trade_size, order_side)
        avg_fill_price = None

        if order_status is not None:
            self._add_log(f"{order_side.capitalize()} order placed on {self.exchange} | Status: {order_status.status}")

            self.ongoing_position = True

            if order_status.status == "filled":
                avg_fill_price = order_status.avg_price
            else:
                t = Timer(2.0, lambda: self._check_order_status(order_status.order_id))
                t.start()

            new_trade = Trade({"time": int(time.time()*1000), "entry_price": avg_fill_price,
                               "contract": self.contract, "strategy": self.strat_name, "side": position_side,
                               "status": "open", "pnl": 0, "quantity": trade_size, "entry_id": order_status.order_id})
            self.trades.append(new_trade)
        #make sure spot doesn't short

class TechnicalStrategy(Strategy):
    def __init__(self, client, contract: Contract, exchange: str, timeframe: str, balance_pct: float, take_profit: float,
                 stop_loss: float, other_params: typing.Dict):
        super().__init__(client, contract, exchange, timeframe, balance_pct, take_profit, stop_loss, "Technical")

        self._ema_fast = other_params['ema_fast']
        self._ema_slow = other_params['ema_slow']
        self._ema_signal = other_params['ema_signal']

        self._rsi_length = other_params['rsi_length']
        # at this point i went to strategy component to add an 'rsi_length' in other_params
        # (go to self._extra_params)

    def _rsi(self):
        close_list = []
        for candle in self.candles:
            close_list.append(candle.close)

        closes = pd.Series(close_list)

        delta = closes.diff().dropna()  # dropna to drop the first entry Nan (only one value then)
        up, down = delta.copy(), delta.copy()
        up[up < 0] = 0
        down[down > 0] = 0

        avg_gain = up.ewm(com=(self._rsi_length - 1), min_periods=self._rsi_length).mean()
        avg_loss = down.abs().ewm(com=(self._rsi_length - 1), min_periods=self._rsi_length).mean()

        res = avg_gain / avg_loss
        rsi = 100 - 100 / (1 + res)
        rsi = rsi.round(2)

        return rsi.iloc[-2]

    def _macd(self) -> typing.Tuple[float, float]:
        # provide list of close prices
        close_list = []
        for candle in self.candles:
            close_list.append(candle.close)

        closes = pd.Series(close_list)
        ema_fast = closes.ewm(span=self._ema_fast).mean()
        ema_slow = closes.ewm(span=self._ema_slow).mean()
        macd_line = ema_fast - ema_slow

        macd_signal = macd_line.ewm(span=self._ema_signal).mean()

        return macd_line.iloc[-2], macd_signal.iloc[-2]
        # -2 because we want macd of finished candles, not ones which are still in formation

    def _check_signal(self):
        macd_line, macd_signal = self._macd()
        rsi = self._rsi()

        if rsi < 30 and macd_line > macd_signal:
            return 1
        elif rsi > 70 and macd_line < macd_signal:
            return -1
        else:
            return 0

    def check_trade(self, tick_type: str):
        if tick_type == "new_candle" and not self.ongoing_position:  # take trade only if no open positions yet
            signal_result = self._check_signal()

            if signal_result in [-1, 1]:
                self._open_position(signal_result)


class BreakoutStrategy(Strategy):
    def __init__(self, client, contract: Contract, exchange: str, timeframe: str, balance_pct: float, take_profit: float,
                 stop_loss: float, other_params: typing.Dict):
        super().__init__(client, contract, exchange, timeframe, balance_pct, take_profit, stop_loss, "Breakout")

        self._ema_fast = other_params['min_volume']

    def _check_signal(self) -> int:
        # if self.candles[-1].close > self.candles[-2].high and self.candles[-1].volume > self._min_volume:
        #     return 1
        #
        # elif self.candles[-1].close < self.candles[-2].low and self.candles[-1].volume > self._min_volume:
        #     return -1
        #
        # else
        #     return 0

        # inside bar pattern

        if self.candles[-2].high < self.candles[-3].high and self.candles[-2].low > self.candles[-3].low:
            if self.candles[-1].close > self.candles[-3].high:
                # upside breakout
                return 1
            elif self.candles[-1].close < self.candles[-3].low:
                # downside pattern
                return -1
            else:
                return 0

    def check_trade(self, tick_type: str):
        if not self.ongoing_position:
            signal_result = self._check_signal()

            if signal_result in [-1, 1]:
                self._open_position(signal_result)
