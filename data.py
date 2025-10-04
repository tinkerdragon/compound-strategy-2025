import pandas as pd
from datetime import datetime
import os
import requests
import time

class DataManager:
    def __init__(self):
        self.data = 0
        self.API_KEYS = {
            'alpha_vantage': os.getenv('ALPHA_VANTAGE_KEY', 'K72Y4TZQHEH5FSJC'),
            'fmp': os.getenv('FMP_KEY', 'XXvJv893Xcda44gojz5fRjENuFoyt2XZ'),
            'marketstack': os.getenv('MARKETSTACK_KEY', '2a44b657a95108570aadee0fc61476ec'),
            'eodhd': os.getenv('EODHD_KEY', '68ad4c715bb122.05778507'),
            'twelvedata': os.getenv('TWELVEDATA_KEY', '4b8603d1d3f743458b2adfa2b7e6050f'),
            'polygon': os.getenv('POLYGON_KEY', 'tG46_YlaJWzQJ5CaxgG_pGNdsp7ueXsc'),
            'stockdata': os.getenv('STOCKDATA_KEY', 'pYQgJkfVul9xyH0fRhnyogZ3uxZ8v6v075YlkjmW'),
            'finnhub': os.getenv('FINNHUB_KEY', 'd1ost19r01qi9vk19dh0d1ost19r01qi9vk19dhg'),
            'tiingo': os.getenv('TIINGO_KEY', '683357598426d16b75051dbfc3dda57d029ce3bd'),
        }

        self.HOURLY_PROVIDERS = ['yahoo', 'polygon', 'twelvedata', 'fmp', 'alpha_vantage', 'tiingo', 'marketstack', 'stockdata']

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
            try:
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
            except Exception as e:
                print(f"Error with {provider}: {e}")
                continue
        
        print(f"All providers failed to fetch hourly data for {symbol}")
        return pd.DataFrame()

    def fetch_from_polygon_hourly(self, symbol, start_date, end_date):
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/hour/{start_date}/{end_date}?apiKey={self.API_KEYS['polygon']}&limit=50000"
        resp = requests.get(url)
        resp.raise_for_status()
        results = resp.json().get('results', [])
        df = pd.DataFrame(results)
        if df.empty:
            return df
        df = df[['t', 'o', 'h', 'l', 'c', 'v']]
        df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
        return df

    def fetch_from_twelvedata_hourly(self, symbol, start_date, end_date):
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1h&start_date={start_date}&end_date={end_date}&apikey={self.API_KEYS['twelvedata']}"
        resp = requests.get(url)
        resp.raise_for_status()
        values = resp.json().get('values', [])
        df = pd.DataFrame(values)
        if df.empty:
            return df
        df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
        return df

    def fetch_from_fmp_hourly(self, symbol, start_date, end_date):
        url = f"https://financialmodelingprep.com/api/v3/historical-chart/1hour/{symbol}?from={start_date}&to={end_date}&apikey={self.API_KEYS['fmp']}"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(data)
        if df.empty:
            return df
        df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
        df.rename(columns={'date': 'datetime'}, inplace=True)
        return df

    def fetch_from_alpha_vantage_hourly(self, symbol, start_date, end_date):
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=60min&outputsize=full&apikey={self.API_KEYS['alpha_vantage']}"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json().get('Time Series (60min)', {})
        df = pd.DataFrame.from_dict(data, orient='index')
        if df.empty:
            return df
        df.reset_index(inplace=True)
        df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        df['date'] = df['datetime'].str[:10]
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        df.drop('date', axis=1, inplace=True)
        return df

    def fetch_from_marketstack_hourly(self, symbol, start_date, end_date):
        url = f"https://api.marketstack.com/v1/intraday?access_key={self.API_KEYS['marketstack']}&symbols={symbol}&interval=1hour&date_from={start_date}&date_to={end_date}&limit=50000"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json().get('data', [])
        df = pd.DataFrame(data)
        if df.empty:
            return df
        df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
        df['datetime'] = pd.to_datetime(df['date'])
        df.drop('date', axis=1, inplace=True)
        return df

    def fetch_from_stockdata_hourly(self, symbol, start_date, end_date):
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        start_unix = int(start_dt.timestamp())
        end_unix = int(end_dt.timestamp()) + 86399  # End of day
        url = f"https://api.stockdata.org/v1/data/intraday?symbols={symbol}&resolution=1h&from={start_unix}&to={end_unix}&api_token={self.API_KEYS['stockdata']}"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json().get('data', [])
        df = pd.DataFrame(data)
        if df.empty:
            return df
        # Expand the 'data' column dictionary into separate columns
        df_data = pd.json_normalize(df['data'])
        df = pd.concat([df[['date', 'ticker']], df_data], axis=1)
        df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
        df['datetime'] = pd.to_datetime(df['date'])
        df.drop('date', axis=1, inplace=True)
        return df

    def fetch_from_finnhub_hourly(self, symbol, start_date, end_date):
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        start_unix = int(start_dt.timestamp())
        end_unix = int(end_dt.timestamp()) + 86399
        url = f"https://finnhub.io/api/v1/stock/candle?symbol={symbol}&resolution=60&from={start_unix}&to={end_unix}&token={self.API_KEYS['finnhub']}"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        if data.get('s') != 'ok':
            return pd.DataFrame()
        df = pd.DataFrame({
            'datetime': pd.to_datetime(data['t'], unit='s'),
            'open': data['o'],
            'high': data['h'],
            'low': data['l'],
            'close': data['c'],
            'volume': data['v']
        })
        return df

    def fetch_from_tiingo_hourly(self, symbol, start_date, end_date):
        url = f"https://api.tiingo.com/iex/{symbol}/prices?startDate={start_date}&endDate={end_date}&resampleFreq=1hour&token={self.API_KEYS['tiingo']}"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(data)
        if df.empty:
            return df
        df = df[['date', 'open', 'high', 'low', 'close']]
        df['volume'] = df.get('volume', 0)  # Tiingo may not provide volume
        df['datetime'] = pd.to_datetime(df['date'])
        df.drop('date', axis=1, inplace=True)
        return df

    def fetch_from_barchart_hourly(self, symbol, start_date, end_date):
        start_fmt = start_date.replace('-', '')
        end_fmt = end_date.replace('-', '')
        url = f"https://marketdata.websol.barchart.com/getHistory.json?apikey={self.API_KEYS['barchart']}&symbol={symbol}&type=minutes&startDate={start_fmt}&endDate={end_fmt}&interval=60"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json().get('results', [])
        df = pd.DataFrame(data)
        if df.empty:
            return df
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        df['datetime'] = pd.to_datetime(df['timestamp'])
        df.drop('timestamp', axis=1, inplace=True)
        return df

    def fetch_from_yahoo_hourly(self, symbol, start_date, end_date):
        try:
            import yfinance as yf
            df = yf.download(symbol, start=start_date, end=end_date, interval='1h', prepost=True)
            if df.empty:
                return df
            df.reset_index(inplace=True)
            df = df[['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']]
            df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            df = df[df['volume'] != 0].reset_index(drop=True)
            return df
        except ImportError:
            print("yfinance library not installed.")
            return pd.DataFrame()