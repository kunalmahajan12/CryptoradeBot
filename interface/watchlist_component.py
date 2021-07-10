import tkinter as tk
from interface.styling import *
import typing
from models import *
import time


class WatchList(tk.Frame):
    def __init__(self, spot_contracts: typing.Dict[str, Contract], margin_contracts: typing.Dict[str, Contract],
                 *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.spot_symbols = list(spot_contracts.keys())
        self.margin_symbols = list(margin_contracts.keys())

        self._commands_frame = tk.Frame(self, bg=BG_COLOR)
        self._commands_frame.pack(side=tk.TOP)

        self._table_frame = tk.Frame(self, bg=BG_COLOR)
        self._table_frame.pack(side=tk.TOP)

        # SPOT
        self._spot_label = tk.Label(self._commands_frame, text="Spot", bg=BG_COLOR, fg=FG_COLOR, font=BOLD_FONT)
        self._spot_label.grid(row=0, column=0)

        self._spot_entry = tk.Entry(self._commands_frame, fg=FG_COLOR, justify=tk.CENTER, insertbackground=FG_COLOR,
                                    bg=BG_COLOR_2)
        self._spot_entry.bind("<Return>", self._add_spot_symbol)
        self._spot_entry.grid(row=1, column=0)

        # MARGIN
        self._margin_label = tk.Label(self._commands_frame, text="Margin", bg=BG_COLOR, fg=FG_COLOR, font=BOLD_FONT)
        self._margin_label.grid(row=0, column=1)

        self._margin_entry = tk.Entry(self._commands_frame, fg=FG_COLOR, justify=tk.CENTER, insertbackground=FG_COLOR,
                                       bg=BG_COLOR_2)
        self._margin_entry.bind("<Return>", self._add_margin_symbol)
        self._margin_entry.grid(row=1, column=1)

        self.body_widgets = dict()

        ##### CREATING TABLE #####

        self._headers = ["Symbol", "Exchange", "Bid", "Ask", "Remove"]
        for idx, h in enumerate(self._headers):
            header = tk.Label(self._table_frame, text=h.capitalize() if h!= "Remove" else "", bg=BG_COLOR, fg=FG_COLOR, font=BOLD_FONT)
            header.grid(row=0, column=idx)

        for h in self._headers:
            self.body_widgets[h] = dict()
            if h in ["Bid", "Ask"]:
                self.body_widgets[h + "_var"] = dict()

        self._body_index = 1

    def _remove_symbol(self, b_index: int):

        for h in self._headers:
            self.body_widgets[h][b_index].grid_forget()
            del self.body_widgets[h][b_index]

    def _add_spot_symbol(self, event):  # event contains info about the widget that was triggered
        symbol = event.widget.get().upper()
        if symbol in self.spot_symbols:
            self._add_symbol(symbol, "Spot")
            event.widget.delete(0, tk.END)

    def _add_margin_symbol(self, event):  # event contains info about the widget that was triggered
        symbol = event.widget.get().upper()
        if symbol in self.margin_symbols:
            self._add_symbol(symbol, "Margin")
            event.widget.delete(0, tk.END)

    def _add_symbol(self, symbol: str, exchange: str):
        # watch carefully, heavy design work here :3

        b_index = self._body_index

        self.body_widgets['Symbol'][b_index] = tk.Label(self._table_frame, text=symbol, bg=BG_COLOR, fg=FG_COLOR_2,
                                                        font=GLOBAL_FONT)
        self.body_widgets['Symbol'][b_index].grid(row=b_index, column=0)

        self.body_widgets['Exchange'][b_index] = tk.Label(self._table_frame, text=exchange, bg=BG_COLOR, fg=FG_COLOR_2,
                                                          font=GLOBAL_FONT)
        self.body_widgets['Exchange'][b_index].grid(row=b_index, column=1)

        # value to textvariable must be a tkinter StringVar object
        # when we want to update bidvar or askvar, we can just use the body_widgets dictionary to reach it and update
        self.body_widgets['Bid_var'][b_index] = tk.StringVar()
        self.body_widgets['Ask_var'][b_index] = tk.StringVar()
        self.body_widgets['Bid'][b_index] = tk.Label(self._table_frame,
                                                     textvariable=self.body_widgets['Bid_var'][b_index], bg=BG_COLOR,
                                                     fg=FG_COLOR_2, font=GLOBAL_FONT)
        self.body_widgets['Bid'][b_index].grid(row=b_index, column=2)

        self.body_widgets['Ask'][b_index] = tk.Label(self._table_frame,
                                                     textvariable=self.body_widgets['Ask_var'][b_index], bg=BG_COLOR,
                                                     fg=FG_COLOR_2, font=GLOBAL_FONT)
        self.body_widgets['Ask'][b_index].grid(row=b_index, column=3)

        self.body_widgets['Remove'][b_index] = tk.Button(self._table_frame,
                                                     text ="X", bg="darkred",
                                                     fg=FG_COLOR, font=GLOBAL_FONT, command=lambda: self._remove_symbol(b_index)) # lambda because even though it is a callback function (and giving parenthesis will lead to it being executed as soon as it is encountered (and
        self.body_widgets['Remove'][b_index].grid(row=b_index, column=4)

        self._body_index += 1
