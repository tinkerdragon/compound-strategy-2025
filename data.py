import pandas as pd
from datetime import datetime
import os
import requests

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
        }

        self.PROVIDERS = ['polygon', 'twelvedata', 'fmp', 'alpha_vantage', 'eodhd', 'marketstack']
        self.HOURLY_PROVIDERS = ['polygon', 'twelvedata', 'fmp', 'alpha_vantage']

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
            print(f"Trying provider: {provider}")
            fetch_func = getattr(self, f'fetch_from_{provider}', None)
            if fetch_func:
                df = fetch_func(symbol, start_date, end_date)
                if not df.empty:
                    print(f"Data fetched successfully from {provider}")
                    return df
                else:
                    print(f"No data from {provider}, trying next...")
                    continue
            else:
                print(f"Function fetch_from_{provider} not found.")
                continue
        
        raise ValueError("All providers failed to fetch data.")

    def fetch_hourly_data(self, symbol: str, start_date: str, end_date: str = None) -> pd.DataFrame:
        """
        Fetches hourly historical stock data using multiple APIs with fallback.
        Args:
            symbol: Stock ticker (e.g., 'AAPL')
            start_date: Start date 'YYYY-MM-DD'
            end_date: End date 'YYYY-MM-DD' (default: today)
        Returns:
            pd.DataFrame with columns: datetime, open, high, low, close, volume
        """
        if end_date is None:
            end_date = datetime.today().strftime('%Y-%m-%d')
        
        for provider in self.HOURLY_PROVIDERS:
            print(f"Trying provider: {provider} for hourly data")
            fetch_func = getattr(self, f'fetch_from_{provider}_hourly', None)
            if fetch_func:
                df = fetch_func(symbol, start_date, end_date)
                if not df.empty:
                    print(f"Hourly data fetched successfully from {provider}")
                    return df
                else:
                    print(f"No hourly data from {provider}, trying next...")
                    continue
            else:
                print(f"Function fetch_from_{provider}_hourly not found.")
                continue
        
        raise ValueError("All providers failed to fetch hourly data.")

    def fetch_from_polygon(self, symbol, start_date, end_date):
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_date}/{end_date}?apiKey={self.API_KEYS['polygon']}"
        resp = requests.get(url)
        resp.raise_for_status()
        results = resp.json().get('results', [])
        df = pd.DataFrame(results)
        df = df[['t', 'o', 'h', 'l', 'c', 'v']]
        df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        df['date'] = pd.to_datetime(df['date'], unit='ms').dt.strftime('%Y-%m-%d')
        return df

    def fetch_from_polygon_hourly(self, symbol, start_date, end_date):
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/hour/{start_date}/{end_date}?apiKey={self.API_KEYS['polygon']}"
        resp = requests.get(url)
        resp.raise_for_status()
        results = resp.json().get('results', [])
        df = pd.DataFrame(results)
        df = df[['t', 'o', 'h', 'l', 'c', 'v']]
        df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
        return df

    def fetch_from_twelvedata(self, symbol, start_date, end_date):
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1day&start_date={start_date}&end_date={end_date}&apikey={self.API_KEYS['twelvedata']}"
        resp = requests.get(url)
        resp.raise_for_status()
        values = resp.json().get('values', [])
        df = pd.DataFrame(values)
        df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
        df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        return df

    def fetch_from_twelvedata_hourly(self, symbol, start_date, end_date):
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1h&start_date={start_date}&end_date={end_date}&apikey={self.API_KEYS['twelvedata']}"
        resp = requests.get(url)
        resp.raise_for_status()
        values = resp.json().get('values', [])
        df = pd.DataFrame(values)
        df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
        return df

    def fetch_from_fmp(self, symbol, start_date, end_date):
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?from={start_date}&to={end_date}&apikey={self.API_KEYS['fmp']}"
        resp = requests.get(url)
        resp.raise_for_status()
        historical = resp.json().get('historical', [])
        df = pd.DataFrame(historical)
        df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
        return df

    def fetch_from_fmp_hourly(self, symbol, start_date, end_date):
        url = f"https://financialmodelingprep.com/api/v3/historical-chart/1hour/{symbol}?from={start_date}&to={end_date}&apikey={self.API_KEYS['fmp']}"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(data)
        df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
        df.rename(columns={'date': 'datetime'}, inplace=True)
        return df

    def fetch_from_alpha_vantage(self, symbol, start_date, end_date):
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={self.API_KEYS['alpha_vantage']}&outputsize=full"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json().get('Time Series (Daily)', {})
        df = pd.DataFrame.from_dict(data, orient='index')
        df.reset_index(inplace=True)
        df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        return df

    def fetch_from_alpha_vantage_hourly(self, symbol, start_date, end_date):
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=60min&outputsize=full&apikey={self.API_KEYS['alpha_vantage']}"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json().get('Time Series (60min)', {})
        df = pd.DataFrame.from_dict(data, orient='index')
        df.reset_index(inplace=True)
        df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        df['date'] = df['datetime'].str[:10]
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        df.drop('date', axis=1, inplace=True)
        return df

    def fetch_from_eodhd(self, symbol, start_date, end_date):
        url = f"https://eodhd.com/api/eod/{symbol}.US?from={start_date}&to={end_date}&api_token={self.API_KEYS['eodhd']}&fmt=json"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(data)
        df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
        return df

    def fetch_from_marketstack(self, symbol, start_date, end_date):
        url = f"http://api.marketstack.com/v1/eod?access_key={self.API_KEYS['marketstack']}&symbols={symbol}&date_from={start_date}&date_to={end_date}"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json().get('data', [])
        df = pd.DataFrame(data)
        df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
        df['date'] = df['date'].str[:10]
        return df