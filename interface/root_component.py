import logging
import tkinter as tk
import logging

from connectors.binance_spot import BinanceSpotClient
from connectors.binance_margin import BinanceMarginClient
import time
from interface.styling import *
from interface.logging_component import Logging
from interface.watchlist_component import WatchList
from interface.trades_component import TradesWatch
from interface.strategy_component import StrategyEditor

logger = logging.getLogger()

class Root(tk.Tk):
    def __init__(self, spot: BinanceSpotClient, margin: BinanceMarginClient):  # margin: BinanceMarginClient,
        super().__init__()

        self.spot = spot
        self.margin = margin

        self.title("Ishaan's Trading Bot")

        self.configure(bg=BG_COLOR)

        self._left_frame = tk.Frame(self, bg=BG_COLOR)
        self._left_frame.pack(side=tk.LEFT)

        self._right_frame = tk.Frame(self, bg=BG_COLOR)
        self._right_frame.pack(side=tk.LEFT)

        self._watchlist_frame = WatchList(spot.contracts, margin.contracts, self._left_frame, bg=BG_COLOR)
        self._watchlist_frame.pack(side=tk.TOP)

        self.logging_frame = Logging(self._left_frame, bg=BG_COLOR)
        self.logging_frame.pack(side=tk.TOP)

        self._strategy_frame = StrategyEditor(self, self.spot, self.margin, self._right_frame, bg=BG_COLOR)
        self._strategy_frame.pack(side=tk.TOP)

        self._trades_frame = TradesWatch(self._right_frame, bg = BG_COLOR)
        self._trades_frame.pack(side=tk.TOP)

        self._update_ui()

    def _update_ui(self):

        # Logs
        for log in self.margin.logs:
            if not log['displayed']:
                self.logging_frame.add_log(log['log'])
                log['displayed'] = True

        for log in self.spot.logs:
            if not log['displayed']:
                self.logging_frame.add_log(log['log'])
                log['displayed'] = True

        # Trade Component and Trade Logs

        for client in [self.spot, self.margin]:
            try:
                for b_index, strategy in client.strategies.items():
                    for log in strategy.logs:
                        if not log['displayed']:
                            self.logging_frame.add_log(log['log'])
                            log['displayed'] = True

                    for trade in strategy.trades:
                        if trade.time not in self._trades_frame.body_widgets['time']:
                            self._trades_frame.add_trade(trade)

                        precision = trade.contract.base_asset_decimals

                        pnl_str = "{0:.{prec}f}".format(trade.pnl, prec=precision)
                        self._trades_frame.body_widgets['pnl_var'][trade.time].set(pnl_str)
                        self._trades_frame.body_widgets['status_var'][trade.time].set(trade.status.capitalize())

            except RuntimeError as e:
                logger.error("Error while looping thorough the strategies dictionary: %s", e)





        # Watchlist prices

        try:
            for key, value in self._watchlist_frame.body_widgets['Symbol'].items():
                symbol = self._watchlist_frame.body_widgets['Symbol'][key].cget("text")
                exchange = self._watchlist_frame.body_widgets['Exchange'][key].cget("text")

                if exchange == "Spot":
                    if symbol not in self.spot.contracts:
                        continue

                    # if symbol not in self.spot.prices:
                    self.spot.get_bid_ask(self.spot.contracts[symbol])
                        # continue

                    precision = self.spot.contracts[symbol].base_asset_decimals
                    prices = self.spot.prices[symbol]

                elif exchange == "Margin":
                    if symbol not in self.margin.contracts:
                        continue

                    # if symbol not in self.margin.prices:
                    self.margin.get_bid_ask(self.margin.contracts[symbol])
                        # continue

                    precision = self.margin.contracts[symbol].base_asset_decimals
                    prices = self.margin.prices[symbol]

                else:
                    continue

                if prices['bid'] is not None:
                    price_str = "{0: .{prec}f}".format(prices['bid'], prec=precision)
                    self._watchlist_frame.body_widgets['Bid_var'][key].set(price_str)

                if prices['ask'] is not None:
                    price_str = "{0: .{prec}f}".format(prices['ask'], prec=precision)
                    self._watchlist_frame.body_widgets['Ask_var'][key].set(price_str)
        except RuntimeError as e:
            logger.error("Error while looping thorough the watchlist dictionary: %s", e)
        self.after(1500, self._update_ui)
