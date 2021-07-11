import tkinter as tk
import typing

from interface.styling import *
from connectors.binance_spot import BinanceSpotClient
from connectors.binance_margin import BinanceMarginClient
from strategies import TechnicalStrategy, BreakoutStrategy, MacdEmaStrategy


class StrategyEditor(tk.Frame):
    def __init__(self, root, spot: BinanceSpotClient, margin: BinanceMarginClient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = root

        # connectors, so as to have a list of symbols in our option menu
        self._exchanges = {
            "Spot": spot,
            "Margin": margin
        }

        self._all_contracts = []
        self._all_timeframes = ["1m", "5m", "15m", "30m", "1h", "4h"]

        for exchange, client in self._exchanges.items():
            for symbol, contract in client.contracts.items():
                self._all_contracts.append(symbol + "_" + exchange.capitalize())

        self._commands_frame = tk.Frame(self, bg=BG_COLOR)
        self._commands_frame.pack(side=tk.TOP)

        self._table_frame = tk.Frame(self, bg=BG_COLOR)
        self._table_frame.pack(side=tk.TOP)

        self._add_button = tk.Button(self._commands_frame, text="Add strategy", font=GLOBAL_FONT,
                                     command=self._add_strategy_row, bg=BG_COLOR_2, fg=FG_COLOR)
        self._add_button.pack(side=tk.TOP)

        self.body_widgets = dict()
        self._additional_parameters = dict()  # for updation using popup window
        self._extra_input = dict()

        self._base_params = [
            {"code_name": "strategy_type", "widget": tk.OptionMenu, "data_type": str,
             "values": ["Technical", "Breakout", "MACD_EMA"], "width": 10},
            {"code_name": "contract", "widget": tk.OptionMenu, "data_type": str,
             "values": self._all_contracts, "width": 15},
            {"code_name": "timeframe", "widget": tk.OptionMenu, "data_type": str,
             "values": self._all_timeframes, "width": 7},

            {"code_name": "balance_percentage", "widget": tk.Entry, "data_type": float, "width": 7},
            {"code_name": "take_profit", "widget": tk.Entry, "data_type": float, "width": 7},
            {"code_name": "stop_loss", "widget": tk.Entry, "data_type": float, "width": 7},

            {"code_name": "parameters", "widget": tk.Button, "data_type": float, "text": "Parameters", "bg": BG_COLOR_2,
             "command": self._show_popup},
            {"code_name": "activation", "widget": tk.Button, "data_type": float, "text": "OFF", "bg": "darkred",
             "command": self._switch_strategy},
            {"code_name": "delete", "widget": tk.Button, "data_type": float, "text": "X", "bg": "darkred",
             "command": self._delete_row}

        ]

        self._extra_params = {
            "Technical": [
                {"code_name": "rsi_length", "name": "RSI Periods", "widget": tk.Entry, "data_type": int},
                {"code_name": "ema_fast", "name": "MACD Fast Length", "widget": tk.Entry, "data_type": int},
                {"code_name": "ema_slow", "name": "MACD Slow Length", "widget": tk.Entry, "data_type": int},
                {"code_name": "ema_signal", "name": "MACD Signal Length", "widget": tk.Entry, "data_type": int},
            ],
            "Breakout": [
                {"code_name": "min_volume", "name": "Minimum Volume", "widget": tk.Entry, "data_type": float}
            ],
            "MACD_EMA": [
                {"code_name": "macd_ema_fast", "name": "MACD Fast Length", "widget": tk.Entry, "data_type": int},
                {"code_name": "macd_ema_slow", "name": "MACD Slow Length", "widget": tk.Entry, "data_type": int},
                {"code_name": "macd_ema_signal", "name": "MACD Signal Length", "widget": tk.Entry, "data_type": int},
                {"code_name": "ema_period", "name": "EMA Period", "widget": tk.Entry, "data_type": int},
            ]

        }
        ##### CREATING TABLE #####

        self._headers = ["Strategy", "Contract", "Timeframe", "Balance", "TP%", "SL%"]
        for idx, h in enumerate(self._headers):
            header = tk.Label(self._table_frame, text=h, bg=BG_COLOR, fg=FG_COLOR, font=BOLD_FONT)
            header.grid(row=0, column=idx)

        for h in self._base_params:
            self.body_widgets[h['code_name']] = dict()
            if h['widget'] == tk.OptionMenu:  # strategy_type, contract, timeframe
                self.body_widgets[h['code_name'] + '_var'] = dict()

        self._body_index = 1

    def _add_strategy_row(self):
        b_index = self._body_index

        for col, base_param in enumerate(self._base_params):
            code_name = base_param['code_name']

            if base_param['widget'] == tk.OptionMenu:
                self.body_widgets[code_name + "_var"][b_index] = tk.StringVar()
                self.body_widgets[code_name + "_var"][b_index].set(base_param['values'][0])  # setting to default value
                self.body_widgets[code_name][b_index] = tk.OptionMenu(self._table_frame,
                                                                      self.body_widgets[code_name + "_var"][b_index],
                                                                      *base_param['values'])
                self.body_widgets[code_name][b_index].config(width=base_param['width'])
            elif base_param['widget'] == tk.Entry:
                self.body_widgets[code_name][b_index] = tk.Entry(self._table_frame, justify=tk.CENTER)

            elif base_param['widget'] == tk.Button:
                self.body_widgets[code_name][b_index] = tk.Button(self._table_frame, text=base_param['text'],
                                                                  bg=base_param['bg'], fg=FG_COLOR,
                                                                  command=lambda frozen_command=base_param[
                                                                      'command']: frozen_command(b_index))

            else:
                continue

            self.body_widgets[code_name][b_index].grid(row=b_index, column=col)

        # every time you create a new row, create a new key in the additional parameters dict for this new row
        self._additional_parameters[b_index] = dict()
        # the b_index key contains another dictionary and this other dictionary is going to contain keys that are
        # the parameter code names.
        for strat, params in self._extra_params.items():
            for param in params:
                self._additional_parameters[b_index][param['code_name']] = None

        self._body_index += 1

    def _delete_row(self, b_index: int):
        for element in self._base_params:
            self.body_widgets[element['code_name']][b_index].grid_forget()

            # also delete from dictionary
            del self.body_widgets[element['code_name']][b_index]

            # but after creating this, if we try to click on parameters or "OFF" button, they also delete the row!
            # There's a problem...

            # the problem is with the lambda function. When we're in a loop, when we set lambda to a value,
            # it changes the value of previously created lambda functions as well which were created dynamically

            # so technically, every button has, as its command, the command given to the button last created (which
            # happens to be 'delete')

            # to overcome this, we will create a variable to store the lambda function.
            # see whatever I've done with the 'frozencommand' on lambda function

    def _show_popup(self, b_index: int):
        # getting coordinates of clicked widget to spawn popup near click
        x = self.body_widgets["parameters"][b_index].winfo_rootx()
        y = self.body_widgets["parameters"][b_index].winfo_rooty()

        self._popup_window = tk.Toplevel(self)
        self._popup_window.wm_title("Parameters")
        self._popup_window.config(bg=BG_COLOR)
        self._popup_window.attributes("-topmost", "true")
        self._popup_window.grab_set()  # so we can click on only the popup window until it is closed

        self._popup_window.geometry(f"+{x - 80}+{y + 30}")

        strat_selected = self.body_widgets['strategy_type_var'][b_index].get()

        row_nb = 0
        for param in self._extra_params[strat_selected]:
            code_name = param['code_name']

            temp_label = tk.Label(self._popup_window, bg=BG_COLOR, fg=FG_COLOR, text=param['name'], font=BOLD_FONT)
            temp_label.grid(row=row_nb, column=0)

            if param['widget'] == tk.Entry:
                self._extra_input[code_name] = tk.Entry(self._popup_window, bg=BG_COLOR_2, justify=tk.CENTER,
                                                        fg=FG_COLOR,
                                                        insertbackground=FG_COLOR)
                if self._additional_parameters[b_index][code_name] is not None:
                    self._extra_input[code_name].insert(tk.END, str(self._additional_parameters[b_index][code_name]))
            else:
                continue
            self._extra_input[code_name].grid(row=row_nb, column=1)

            row_nb += 1

        # Validation Button
        validation_button = tk.Button(self._popup_window, text="Validate", bg=BG_COLOR_2, fg=FG_COLOR,
                                      command=lambda: self._validate_parameters(b_index))
        validation_button.grid(row=row_nb, column=0, columnspan=2)

    def _validate_parameters(self, b_index: int):
        strat_selected = self.body_widgets['strategy_type_var'][b_index].get()
        for param in self._extra_params[strat_selected]:
            code_name = param['code_name']
            if self._extra_input[code_name].get() == "":
                self._additional_parameters[b_index][code_name] = None
            else:
                self._additional_parameters[b_index][code_name] = param['data_type'](self._extra_input[code_name].get())

        self._popup_window.destroy()

    def _switch_strategy(self, b_index: int):
        # one to activate/ deactivate strategy
        # one for checking that we didn't forget to add any parameters among the mandatory ones
        for param in ["balance_percentage", "take_profit", "stop_loss"]:
            if self.body_widgets[param][b_index].get() == "":
                self.root.logging_frame.add_log(f"Missing {param} parameter")
                return

        # to see if the specific params of the strat are chosen by user
        strat_selected = self.body_widgets['strategy_type_var'][b_index].get()
        for param in self._extra_params[strat_selected]:
            if self._additional_parameters[b_index][param['code_name']] is None:
                self.root.logging_frame.add_log(f"Missing {param['code_name']} parameter")
                return

        # once we know all params are here, we can pass them and store them in variables
        symbol = self.body_widgets['contract_var'][b_index].get().split("_")[0]
        exchange = self.body_widgets['contract_var'][b_index].get().split("_")[1]
        timeframe = self.body_widgets['timeframe_var'][b_index].get()

        contract = self._exchanges[exchange].contracts[symbol]

        balance_percentage = float(self.body_widgets['balance_percentage'][b_index].get())
        take_profit = float(self.body_widgets['take_profit'][b_index].get())
        stop_loss = float(self.body_widgets['stop_loss'][b_index].get())

        # if button is currently off, it means we clicked it to activate the strat
        if self.body_widgets['activation'][b_index].cget("text") == "OFF":

            if strat_selected == "Technical":
                new_strategy = TechnicalStrategy(self._exchanges[exchange], contract, exchange, timeframe,
                                                 balance_percentage, take_profit, stop_loss,
                                                 self._additional_parameters[b_index])

            elif strat_selected == "Breakout":
                new_strategy = BreakoutStrategy(self._exchanges[exchange], contract, exchange, timeframe,
                                                balance_percentage, take_profit, stop_loss,
                                                self._additional_parameters[b_index])

            elif strat_selected == "MACD_EMA":
                new_strategy = MacdEmaStrategy(self._exchanges[exchange], contract, exchange, timeframe,
                                               balance_percentage, take_profit, stop_loss,
                                               self._additional_parameters[b_index])
            else:
                return

            new_strategy.candles = self._exchanges[exchange].get_historical_candles(contract, timeframe)

            if len(new_strategy.candles) == 0:
                self.root.logging_frame.add_log(f"No historical data retrieved for {contract.symbol}")
                return

            self._exchanges[exchange].strategies[b_index] = new_strategy

            # deactivate the buttons to avoid user changing the values while it is running
            for param in self._base_params:
                code_name = param['code_name']
                if code_name != "activation" and "_var" not in code_name:
                    self.body_widgets[code_name][b_index].config(state=tk.DISABLED)

            self.body_widgets['activation'][b_index].config(bg="darkgreen", text="ON")
            self.root.logging_frame.add_log(f"{strat_selected} strategy on {symbol} / {timeframe} started")

        else:
            del self._exchanges[exchange].strategies[b_index]

            for param in self._base_params:
                code_name = param['code_name']
                if code_name != "activation" and "_var" not in code_name:
                    self.body_widgets[code_name][b_index].config(state=tk.NORMAL)

            self.body_widgets['activation'][b_index].config(bg="darkred", text="OFF")
            self.root.logging_frame.add_log(f"{strat_selected} strategy on {symbol} / {timeframe} stopped")
