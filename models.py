class SpotBalance:
    def __init__(self, data):
        self.asset = data['asset']
        self.free = data['free']
        self.locked = data['locked']

class MarginBalance:
    def __init__(self, data):
        self.asset = data['asset']
        self.free = data['free']
        self.locked = data['locked']

class Contract:
    def __init__(self, contract_data):
        self.symbol = contract_data['symbol']
        self.base_asset = contract_data['baseAsset']
        self.quote_asset = contract_data['quoteAsset']
        self.base_asset_decimals = contract_data['baseAssetPrecision']
        # self.quote_asset_decimals = contract_data['quotePrecision']
        self.tick_size = 1.0 / pow(10, self.base_asset_decimals)
        # self.lot_size = 1.0 / pow(10, self.quantity_decimals)

class Balance:
    def __init__(self, data):
        self.initial_margin = float(data['initialMargin'])
        self.maintenance_margin = float(data['maintMargin'])
        self.margin_balance = float(data['marginBalance'])
        self.wallet_balance = float(data['walletBalance'])
        self.unrealized_pnl = float(data['unrealizedProfit'])


class Candle:
    def __init__(self, candle_data, timeframe, exchange):

        if exchange == "Spot" or exchange == "Margin":       #check for spellings
            self.timestamp = candle_data[0]
            self.open = float(candle_data[1])
            self.high = float(candle_data[2])
            self.low = float(candle_data[3])
            self.close = float(candle_data[4])
            self.volume = float(candle_data[5])

        elif exchange == "parse_trade":
            self.timestamp = candle_data['ts']
            self.open = float(candle_data['open'])
            self.high = float(candle_data['high'])
            self.low = float(candle_data['low'])
            self.close = float(candle_data['close'])
            self.volume = float(candle_data['volume'])

# class Contract:
#     def __init__(self, contract_data):
#         self.symbol = contract_data['symbol']
#         self.base_asset = contract_data['baseAsset']
#         self.quote_asset = contract_data['quoteAsset']
#         self.price_decimals = contract_data['pricePrecision']
#         self.quantity_decimals = contract_data['quantityPrecision']
#         self.tick_size = 1.0 / pow(10, self.price_decimals)
#         self.lot_size = 1.0 / pow(10, self.quantity_decimals)


class OrderStatus:
    def __init__(self, order_info):
        self.order_id = order_info['orderId']
        self.status = order_info['status'].lower()
        self.avg_price = float(order_info['price'])


class Trade:
    def __init__(self, trade_info):
        self.time: int = trade_info['time']
        self.contract: Contract = trade_info['contract']
        self.strategy: str = trade_info['strategy']
        self.side: str = trade_info['side']
        self.entry_price: float = trade_info['entry_price']
        self.status: str = trade_info['status']
        self.pnl: float = trade_info['pnl']
        self.quantity = trade_info['quantity']
        self.entry_id = trade_info['entry_id']


