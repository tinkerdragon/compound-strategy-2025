import yfinance as yf
import pandas as pd

class MarketAnalyzer:
    def __init__(self):
        self.data = []

    def fetch_data(self, ticker, period="50h", interval="1h"):
        """
        Fetch hourly market data using yfinance and store it as an attribute.
        
        Args:
            ticker (str): Ticker symbol (e.g., 'SPY' for S&P 500 ETF).
            period (str): Period of data to fetch (default: '50h').
            interval (str): Data interval (default: '1h' for hourly).
        """
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval)
            self.data = [
                {
                    'high': row['High'],
                    'low': row['Low'],
                    'close': row['Close'],
                    'volume': row['Volume']
                } for _, row in df.iterrows()
            ]
        except Exception as e:
            print(f"Error fetching data: {e}")
            self.data = []

    def compute_obv(self):
        """Compute On-Balance Volume (OBV) for the stored data sequence."""
        if not self.data:
            return [0]
        obv = [0]
        for i in range(1, len(self.data)):
            if self.data[i]['close'] > self.data[i-1]['close']:
                obv.append(obv[-1] + self.data[i]['volume'])
            elif self.data[i]['close'] < self.data[i-1]['close']:
                obv.append(obv[-1] - self.data[i]['volume'])
            else:
                obv.append(obv[-1])
        return obv

    def compute_mfi(self, period=14):
        """Compute Money Flow Index (MFI) for each period where possible."""
        if not self.data:
            return [None] * period
        mfi = [None] * (period - 1)
        for i in range(period - 1, len(self.data)):
            window = self.data[i - period + 1: i + 1]
            typical = [(d['high'] + d['low'] + d['close']) / 3 for d in window]
            money_flow = [typical[j] * window[j]['volume'] for j in range(period)]
            positive_mf = sum(money_flow[j] for j in range(1, period) if typical[j] > typical[j-1])
            negative_mf = sum(money_flow[j] for j in range(1, period) if typical[j] < typical[j-1])
            if negative_mf == 0:
                mfi_val = 100
            else:
                mfi_ratio = positive_mf / negative_mf
                mfi_val = 100 - 100 / (1 + mfi_ratio)
            mfi.append(mfi_val)
        return mfi

    def analyze(self):
        """
        Analyze the market state based on the stored data and return three boolean flags.
        
        Returns:
            tuple: (flag1, flag2, flag3) indicating if each condition is met.
        """
        # Require at least 50 periods for all indicators to be fully computable
        if len(self.data) < 50:
            return (False, False, False)

        # Extract close prices
        close_prices = [d['close'] for d in self.data]

        # Compute 20-hour and 50-hour moving averages
        ma20 = sum(close_prices[-20:]) / 20
        ma50 = sum(close_prices[-50:]) / 50

        # Flag 1: Price within ±3% of 20-hour MA and 20-hour MA > 50-hour MA
        price_retrace = abs(self.data[-1]['close'] - ma20) / ma20 <= 0.03
        ma_condition = ma20 > ma50
        flag1 = price_retrace and ma_condition

        # Flag 2: MFI drops below 30 and rebounds sharply
        mfi = self.compute_mfi(14)
        recent_mfi = mfi[-5:]
        min_mfi = min(m for m in recent_mfi if m is not None)
        # Check if MFI was below 30 recently, is now above 30, and increased by >10 points
        flag2 = any(m < 30 for m in recent_mfi if m is not None) and mfi[-1] > 30 and (mfi[-1] - min_mfi) > 10

        # Flag 3: Price at new low, OBV not at new low, with a high-volume up day
        obv = self.compute_obv()
        min_close = min(close_prices[-20:])
        is_new_low = self.data[-1]['close'] == min_close
        min_obv = min(obv[-20:])
        obv_not_new_low = obv[-1] > min_obv

        # Check for a positive volume bar > 2% above average volume
        avg_volume = sum([d['volume'] for d in self.data[-20:]]) / 20
        has_positive_volume = any(
            self.data[-k]['close'] > self.data[-k-1]['close'] and self.data[-k]['volume'] > 1.02 * avg_volume
            for k in range(1, 6)
        )
        flag3 = is_new_low and obv_not_new_low and has_positive_volume

        return (flag1, flag2, flag3)
