import tkinter as tk
import typing
import datetime
from interface.styling import *
from models import *


class TradesWatch(tk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        ##### CREATING TABLE #####

        self.body_widgets = dict()
        self._headers = ["Time", "Symbol", "Exchange", "Strategy", "Side", "Quantity", "Status", "PnL", "Open Price",
                         "Profit Line", "Loss Line"]
        self._table_frame = tk.Frame(self, bg=BG_COLOR)
        self._table_frame.pack(side=tk.TOP)

        for idx, h in enumerate(self._headers):
            header = tk.Label(self._table_frame, text=h.capitalize(), bg=BG_COLOR, fg=FG_COLOR,
                              font=BOLD_FONT)
            header.grid(row=0, column=idx)

        for h in self._headers:
            self.body_widgets[h] = dict()
            if h in ["Status", "PnL"]:
                self.body_widgets[h + "_var"] = dict()

        self._body_index = 1

    def add_trade(self, trade: Trade):
        b_index = self._body_index
        t_index = trade.time  # time of trade can act as a unique identifier
        dt_str = datetime.datetime.fromtimestamp(trade.time/1000).strftime("%b %d %H:%M")

        self.body_widgets['Time'][t_index] = tk.Label(self._table_frame, text=dt_str, bg=BG_COLOR, fg=FG_COLOR_2,
                                                      font=GLOBAL_FONT)
        self.body_widgets['Time'][t_index].grid(row=b_index, column=0)

        self.body_widgets['Symbol'][t_index] = tk.Label(self._table_frame, text=trade.contract.symbol, bg=BG_COLOR,
                                                        fg=FG_COLOR_2,
                                                        font=GLOBAL_FONT)
        self.body_widgets['Symbol'][t_index].grid(row=b_index, column=1)

        self.body_widgets['Exchange'][t_index] = tk.Label(self._table_frame, text=trade.contract.exchange.capitalize(),
                                                          bg=BG_COLOR,
                                                          fg=FG_COLOR_2,
                                                          font=GLOBAL_FONT)
        self.body_widgets['Exchange'][t_index].grid(row=b_index, column=2)

        self.body_widgets['Strategy'][t_index] = tk.Label(self._table_frame, text=trade.strategy, bg=BG_COLOR,
                                                          fg=FG_COLOR_2,
                                                          font=GLOBAL_FONT)
        self.body_widgets['Strategy'][t_index].grid(row=b_index, column=3)

        self.body_widgets['Side'][t_index] = tk.Label(self._table_frame, text=trade.side.upper(), bg=BG_COLOR,
                                                      fg=FG_COLOR_2,
                                                      font=GLOBAL_FONT)
        self.body_widgets['Side'][t_index].grid(row=b_index, column=4)

        self.body_widgets['Quantity'][t_index] = tk.Label(self._table_frame, text=trade.quantity, bg=BG_COLOR,
                                                          fg=FG_COLOR_2,
                                                          font=GLOBAL_FONT)
        self.body_widgets['Quantity'][t_index].grid(row=b_index, column=5)

        # Status
        self.body_widgets['Status_var'][t_index] = tk.StringVar()
        self.body_widgets['Status'][t_index] = tk.Label(self._table_frame,
                                                        textvariable=self.body_widgets['Status_var'][t_index],
                                                        bg=BG_COLOR, fg=FG_COLOR_2,
                                                        font=GLOBAL_FONT)
        self.body_widgets['Status'][t_index].grid(row=b_index, column=6)

        # PnL
        self.body_widgets['PnL_var'][t_index] = tk.StringVar()
        self.body_widgets['PnL'][t_index] = tk.Label(self._table_frame,
                                                     textvariable=self.body_widgets['PnL_var'][t_index],
                                                     bg=BG_COLOR, fg=FG_COLOR_2,
                                                     font=GLOBAL_FONT)
        self.body_widgets['PnL'][t_index].grid(row=b_index, column=7)

        # Open Price
        self.body_widgets['Open Price'][t_index] = tk.Label(self._table_frame, text=str(trade.entry_price), bg=BG_COLOR,
                                                            fg=FG_COLOR_2,
                                                            font=GLOBAL_FONT)
        self.body_widgets['Open Price'][t_index].grid(row=b_index, column=8)

        # Profit Line
        profit_per = abs(trade.entry_price - trade.profit_line) / trade.entry_price * 100
        self.body_widgets['Profit Line'][t_index] = tk.Label(self._table_frame,
                                                             text=f"{round(trade.profit_line,4)}, {round(profit_per,2)}%", bg=BG_COLOR,
                                                             fg=FG_COLOR_2, font=GLOBAL_FONT)
        self.body_widgets['Profit Line'][t_index].grid(row=b_index, column=9)

        # Loss Line
        loss_per = abs(trade.entry_price - trade.stop_loss_line) / trade.entry_price * 100
        self.body_widgets['Loss Line'][t_index] = tk.Label(self._table_frame,
                                                           text=f"{round(trade.stop_loss_line,4)}, {round(loss_per,2)}%",
                                                           bg=BG_COLOR,
                                                           fg=FG_COLOR_2, font=GLOBAL_FONT)
        self.body_widgets['Loss Line'][t_index].grid(row=b_index, column=10)

        self._body_index += 1
