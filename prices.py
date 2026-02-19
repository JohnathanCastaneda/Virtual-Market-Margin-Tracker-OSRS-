import requests

MAPPING_URL = "https://prices.runescape.wiki/api/v1/osrs/mapping"
PRICING_URL = "https://prices.runescape.wiki/api/v1/osrs/latest"

class PriceManager:
    def __init__(self):
        self.items = {}
        self.prices = {}

        self.load_items()
        self.load_prices()

    def load_items(self):
        data = requests.get(MAPPING_URL).json()

        for item in data:
            self.items[item["name"].lower()] = item["id"]

    def load_prices(self):
        self.prices = requests.get(PRICING_URL).json()["data"]

    def is_tradable(self, name):
        return name.lower() in self.items

    def get_price(self, name, price_type="low"):
        name = name.lower()

        if name not in self.items:
            return None

        item_id = self.items[name]
        price_data = self.prices.get(str(item_id))
        
        if not price_data:
            return None

        return price_data.get(price_type)