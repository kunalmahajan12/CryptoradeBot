import threading
import time
import websocket
from connectors.binance_spot import BinanceSpotClient
from connectors.binance_margin import BinanceMarginClient
import json
from pprint import pprint
import typing
import requests
import logging
from models import *

logger = logging.getLogger()


class BalanceWebsocket:
    def __init__(self, public_key, secret_key, spot: BinanceSpotClient, margin: BinanceMarginClient, testnet: bool):
        if testnet:
            self._base_url = "https://testnet.binance.vision/api"
            self._wss_url = "wss://stream.binancefuture.com/ws"
        else:
            self._base_url = "https://api.binance.com"
            self._wss_url = "wss://stream.binance.com:9443/ws"

        self.spot = spot
        self.margin = margin

        self._public_key = public_key
        self._secret_key = secret_key
        self._headers = {'X-MBX-APIKEY': self._public_key}

        self.spot_listen_key = None
        self.margin_listen_key = None
        self._renew_listen_keys()

        ##### WEBSOCKETS #####
        self._spot_ws = None
        self._margin_ws = None

        spot_thread = threading.Thread(target=self._start_spot_ws)
        spot_thread.start()

        margin_thread = threading.Thread(target=self._start_margin_ws)
        margin_thread.start()

    def _make_request(self, method: str, endpoint: str, data):
        response = None
        if method == 'POST':
            try:
                response = requests.post(self._base_url + endpoint, params=data, headers=self._headers)
            except Exception as e:
                logger.error("Connection error while making %s request to %s: %s", method, endpoint, e)
                return None

        if method == 'DELETE':
            try:
                response = requests.delete(self._base_url + endpoint, params=data, headers=self._headers)
            except Exception as e:
                logger.error("Connection error while making %s request to %s: %s", method, endpoint, e)
                return None
        if response.status_code == 200:
            return response.json()
        else:
            logger.error("Error while making %s request to %s:%s (error code %s)", method, endpoint, response.json(),
                         response.status_code)
            return None

    def _renew_listen_keys(self):
        if self.spot_listen_key is None:
            self.spot_listen_key = self._make_request('POST', "/api/v3/userDataStream", dict())['listenKey']
            self.margin_listen_key = self._make_request('POST', "/sapi/v1/userDataStream", dict())['listenKey']

            # delete existing keys
            self._make_request("DELETE", "/api/v3/userDataStream", {'listenKey': self.spot_listen_key})  # spot
            self._make_request("DELETE", "/sapi/v1/userDataStream", {'listenKey': self.margin_listen_key})  # margin

            # get new keys
            spot_key = self._make_request('POST', "/api/v3/userDataStream", dict())['listenKey']
            margin_key = self._make_request('POST', "/sapi/v1/userDataStream", dict())['listenKey']
            self.spot_listen_key = spot_key
            self.margin_listen_key = margin_key

        else:
            # delete existing keys
            self._make_request("DELETE", "/api/v3/userDataStream", {'listenKey': self.spot_listen_key})  # spot
            self._make_request("DELETE", "/sapi/v1/userDataStream", {'listenKey': self.margin_listen_key})  # margin

            # get new keys
            spot_key = self._make_request('POST', "/api/v3/userDataStream", dict())['listenKey']
            margin_key = self._make_request('POST', "/sapi/v1/userDataStream", dict())['listenKey']
            self.spot_listen_key = spot_key
            self.margin_listen_key = margin_key

        t = threading.Timer(45 * 60, self._renew_listen_keys)
        t.start()

    def _start_spot_ws(self):
        self._spot_ws = websocket.WebSocketApp(self._wss_url + "/" + self.spot_listen_key,
                                               on_open=self._on_spot_open,
                                               on_close=self._on_spot_close,
                                               on_error=self._on_spot_error,
                                               on_message=self._on_spot_message)
        while True:
            try:
                self._spot_ws.run_forever()
            except Exception as e:
                logger.error("Spot Balance Websocket error in run_forever() method: %s", e)
            time.sleep(2)

    def _on_spot_open(self, ws):
        logger.info("Spot Balance Websocket connection opened")

    def _on_spot_close(self, ws):
        logger.warning("Spot Balance Websocket connection closed")

    def _on_spot_error(self, ws, msg: str):
        logger.error("Spot Balance Websocket connection error: %s", msg)

    def _on_spot_message(self, ws, msg: str):
        data = dict()
        data = json.loads(msg)

        # there are two types of payloads, balanceUpdate and outboundAccountPosition
        if 'e' in data:
            if data['e'] == 'outboundAccountPosition':
                pprint(data)
                for i in data['B']:
                    asset = i['a']
                    free = float(i['f'])
                    locked = float(i['l'])
                    if asset in self.spot.Balances:
                        self.spot.Balances[asset].free = free
                        self.spot.Balances[asset].locked = locked
                    else:
                        self.spot.Balances[asset] = SpotBalance({"asset": asset, "free": free, "locked": locked})

            elif data['e'] == "balanceUpdate":
                # not really needed
                return

    # MARGIN WEBSOCKET
    def _start_margin_ws(self):
        self._margin_ws = websocket.WebSocketApp(self._wss_url + "/" + self.margin_listen_key,
                                                 on_open=self._on_margin_open,
                                                 on_close=self._on_margin_close,
                                                 on_error=self._on_margin_error,
                                                 on_message=self._on_margin_message)
        while True:
            try:
                self._margin_ws.run_forever()
            except Exception as e:
                logger.error("Margin Balance Websocket error in run_forever() method: %s", e)
            time.sleep(2)

    def _on_margin_open(self, ws):
        logger.info("Margin Balance Websocket connection opened")

    def _on_margin_close(self, ws):
        logger.warning("Margin Balance Websocket connection closed")

    def _on_margin_error(self, ws, msg: str):
        logger.error("Margin Balance Websocket connection error: %s", msg)

    def _on_margin_message(self, ws, msg: str):
        data = dict()
        data = json.loads(msg)

        # there are two types of payloads, balanceUpdate and outboundAccountPosition
        if 'e' in data:
            if data['e'] == 'outboundAccountPosition':
                pprint(data)
                for i in data['B']:
                    asset = i['a']
                    free = float(i['f'])
                    locked = float(i['l'])
                    if asset in self.margin.Balances:
                        self.spot.Balances[asset].free = free
                        self.spot.Balances[asset].locked = locked
                    else:
                        self.margin.Balances[asset] = MarginBalance({"asset": asset, "free": free, "locked": locked})

            elif data['e'] == "balanceUpdate":
                # not really needed
                return
