import os
import requests
import pandas as pd
from datetime import datetime

class DataManager:
    def __init__(self):
        self.data = 0
        self.API_KEYS = {
            'alpha_vantage': os.getenv('ALPHA_VANTAGE_KEY', 'K72Y4TZQHEH5FSJC'),
            'fmp': os.getenv('FMP_KEY', 'XXvJv893Xcda44gojz5fRjENuFoyt2XZ'),
            'marketstack': os.getenv('MARKETSTACK_KEY', '2a44b657a95108570aadee0fc61476ec'),
            'eodhd': os.getenv('EODHD_KEY', ' 68ad4c715bb122.05778507'),
            'twelvedata': os.getenv('TWELVEDATA_KEY', '4b8603d1d3f743458b2adfa2b7e6050f'),
            'polygon': os.getenv('POLYGON_KEY', 'tG46_YlaJWzQJ5CaxgG_pGNdsp7ueXsc'),
            'finnhub': os.getenv('FINNHUB_KEY', 'd1ost19r01qi9vk19dh0d1ost19r01qi9vk19dhg'),
            'alpaca_key': os.getenv('ALPACA_KEY', 'CK92VDKIX38FUIC2V3WO'),  # Alpaca needs key
            'alpaca_secret': os.getenv('ALPACA_SECRET', 'CcMRGQyZlZg90wsXYdccdX5wNhf0b8g9l0RjUq5b'),  # Alpaca needs secret
        }

        self.PROVIDERS = ['alpaca','finnhub','polygon', 'twelvedata','fmp','alpha_vantage','eodhd', 'marketstack']

    def fetch_daily_data(self, symbol: str, start_date: str, end_date: str = None) -> pd.DataFrame:
        """
        Fetches daily historical stock data using multiple APIs with fallback.
        Args:
            symbol: Stock ticker (e.g., 'AAPL')
            start_date: Start date 'YYYY-MM-DD'
            end_date: End date 'YYYY-MM-DD' (default: today)
        Returns:
            pd.DataFrame with columns: date, open, high, low, close, volume
        """
        if end_date is None:
            end_date = datetime.today().strftime('%Y-%m-%d')
        
        for provider in self.PROVIDERS:
            try:
                df = globals()[f'fetch_from_{provider}'](symbol, start_date, end_date)
                if not df.empty:
                    print(f"Data fetched successfully from {provider}")
                    return df
            except Exception as e:
                print(f"Failed to fetch from {provider}: {e}")
                continue
        
        raise ValueError("All providers failed to fetch data.")

    def fetch_from_alpaca(self, symbol, start_date, end_date):
        # Alpaca uses APCA-API-KEY-ID and APCA-API-SECRET-KEY headers
        headers = {
            'APCA-API-KEY-ID': self.API_KEYS['alpaca_key'],
            'APCA-API-SECRET-KEY': self.API_KEYS['alpaca_secret']
        }
        url = f"https://data.alpaca.markets/v2/stocks/{symbol}/bars?start={start_date}&end={end_date}&timeframe=1Day"
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        bars = resp.json().get('bars', [])
        df = pd.DataFrame(bars)
        df = df[['t', 'o', 'h', 'l', 'c', 'v']]
        df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        self.data = df
        return df

    def fetch_from_finnhub(self, symbol, start_date, end_date):
        start_unix = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp())
        end_unix = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp())
        url = f"https://finnhub.io/api/v1/stock/candle?symbol={symbol}&resolution=D&from={start_unix}&to={end_unix}&token={self.API_KEYS['finnhub']}"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame({
            'date': pd.to_datetime(data['t'], unit='s').strftime('%Y-%m-%d'),
            'open': data['o'],
            'high': data['h'],
            'low': data['l'],
            'close': data['c'],
            'volume': data['v']
        })
        self.data = df
        return df

    def fetch_from_polygon(self, symbol, start_date, end_date):
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_date}/{end_date}?apiKey={self.API_KEYS['polygon']}"
        resp = requests.get(url)
        resp.raise_for_status()
        results = resp.json().get('results', [])
        df = pd.DataFrame(results)
        df = df[['t', 'o', 'h', 'l', 'c', 'v']]
        df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        df['date'] = pd.to_datetime(df['date'], unit='ms').dt.strftime('%Y-%m-%d')
        self.data = df
        return df

    def fetch_from_twelvedata(self, symbol, start_date, end_date):
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1day&start_date={start_date}&end_date={end_date}&apikey={self.API_KEYS['twelvedata']}"
        resp = requests.get(url)
        resp.raise_for_status()
        values = resp.json().get('values', [])
        df = pd.DataFrame(values)
        df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
        df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        self.data = df
        return df

    def fetch_from_fmp(self, symbol, start_date, end_date):
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?from={start_date}&to={end_date}&apikey={self.API_KEYS['fmp']}"
        resp = requests.get(url)
        resp.raise_for_status()
        historical = resp.json().get('historical', [])
        df = pd.DataFrame(historical)
        df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
        self.data = df
        return df

    def fetch_from_alpha_vantage(self, symbol, start_date, end_date):
        # Alpha Vantage doesn't support date range directly; fetch full and filter
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={self.API_KEYS['alpha_vantage']}&outputsize=full"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json().get('Time Series (Daily)', {})
        df = pd.DataFrame.from_dict(data, orient='index')
        df.reset_index(inplace=True)
        df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        self.data = df
        return df

    def fetch_from_eodhd(self, symbol, start_date, end_date):
        url = f"https://eodhd.com/api/eod/{symbol}.US?from={start_date}&to={end_date}&api_token={self.API_KEYS['eodhd']}&fmt=json"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(data)
        df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
        self.data = df
        return df

    def fetch_from_marketstack(self, symbol, start_date, end_date):
        url = f"http://api.marketstack.com/v1/eod?access_key={self.API_KEYS['marketstack']}&symbols={symbol}&date_from={start_date}&date_to={end_date}"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json().get('data', [])
        df = pd.DataFrame(data)
        df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
        df['date'] = df['date'].str[:10]  # Strip time
        self.data = df
        return df