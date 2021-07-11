import datetime
import time
import tkinter as tk
import pandas as pd
import logging
import keygen
from pprint import pprint
# from connectors.bitmex_api import get_contracts
from connectors.binance_margin import BinanceMarginClient
from connectors.binance_spot import BinanceSpotClient
from connectors.balance_websocket import BalanceWebsocket
from interface.root_component import Root

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s :: %(message)s')
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.INFO)
file_handler = logging.FileHandler('info.log')
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)
logger.addHandler(stream_handler)
logger.addHandler(file_handler)

if __name__ == '__main__':
    publicKey, secretKey = keygen.getKeys()

    spot = BinanceSpotClient(public_key=publicKey, secret_key=secretKey, testnet=False)
    margin = BinanceMarginClient(public_key=publicKey, secret_key=secretKey, testnet=False)
    balance_websocket = BalanceWebsocket(public_key=publicKey, secret_key=secretKey, spot=spot, margin=margin, testnet=False)
    time.sleep(1.5)  # necessary to not get error while subscribing due to external thread
    spot.make_snapshot()

    root = Root(spot=spot, margin=margin)

    root.mainloop()
