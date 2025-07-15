import pandas as pd
import os
import numpy as np

'''
四大触发条件:
1.均线支撑:
价格回调至20小时均线附近(±3%)确认
20小时均线仍高于50小时均线(短线趋势未破)
*(参数:小时级K线, 对应30/60分钟周期)*
2.MFI超卖反弹:
MFI(14) 跌破30后快速回升 → 资金回流信号
要求:MFI回升斜率 > 45°(快速脱离超卖区)
3.OBV量价背离终结:
价格创新低, 但OBV未创新低(下跌动能衰竭)
OBV出现单根2%以上阳量柱(主力吸筹信号)
4.K线+成交量准确入场:
反转K线组合:早晨之星/锤子线/阳包阴(最强买卖点)
成交量放大:当前成交量 > 前3小时均量 200%
'''

class MarketAnalyzer:
    def __init__(self):
        self.data = []

    def fetch_data(self, ticker='AAPL'):
        """
        Search all subdirectories for a file named '{ticker}.csv' and print its path if found.
        """
        target_filename = f"{ticker}.csv"
        found = False
        for root, dirs, files in os.walk(os.getcwd()):
            if target_filename in files:
                self.data = pd.read_csv(os.path.join(root, target_filename))
                print(f"Found and loaded: {os.path.join(root, target_filename)}")
                found = True
        if not found:
            print(f"{target_filename} not found in any subdirectory.")
    
    def show_data(self):
        """Display the first few rows of the stored data sequence."""
        return self.data.head()

    def calculate_mfi(self, period=14, slope_window=3):
        df = self.data.copy()
        
        df['Typical_Price'] = (df['<HIGH>'] + df['<LOW>'] + df['<CLOSE>']) / 3
        
        df['Raw_Money_Flow'] = df['Typical_Price'] * df['<VOL>']
        
        df['Price_Change'] = df['Typical_Price'].diff()
        df['Positive_Flow'] = np.where(df['Price_Change'] > 0, df['Raw_Money_Flow'], 0)
        df['Negative_Flow'] = np.where(df['Price_Change'] < 0, df['Raw_Money_Flow'], 0)
        
        positive_sum = df['Positive_Flow'].rolling(window=period).sum()
        negative_sum = df['Negative_Flow'].rolling(window=period).sum()
        
        df['Money_Flow_Ratio'] = positive_sum / (negative_sum + 1e-10)
        
        df['INDC_MFI'] = 100 - (100 / (1 + df['Money_Flow_Ratio']))

        # Calculate the slope of MFI using linear regression over a rolling window
        def calc_slope(series):
            y = series.values
            x = np.arange(len(y))
            if len(y) < slope_window or np.any(np.isnan(y)):
                return np.nan
            A = np.vstack([x, np.ones(len(x))]).T
            m, _ = np.linalg.lstsq(A, y, rcond=None)[0]
            return m

        df['INDC_MFI_SLOPE'] = df['INDC_MFI'].rolling(window=slope_window).apply(calc_slope, raw=False)

        df = df.drop(['Typical_Price', 'Raw_Money_Flow', 'Price_Change', 
                    'Positive_Flow', 'Negative_Flow', 'Money_Flow_Ratio'], axis=1).dropna().reset_index(drop=True)
        
        self.data = df

        return 'MFI calculation completed.'
    
    def calculate_obv(self):
        df = self.data.copy()
        
        df['Price_Change'] = df['<CLOSE>'].diff()
        df['Direction'] = np.where(df['Price_Change'] > 0, 1, np.where(df['Price_Change'] < 0, -1, 0))
        
        df['INDC_OBV'] = (df['<VOL>'] * df['Direction']).cumsum()
        df = df.drop(['Price_Change', 'Direction'], axis=1).dropna().reset_index(drop=True)
        
        self.data = df
        
        return 'OBV calculation completed.'
    
    def calculate_ma(self):
        """
        Calculate the 20-hour moving average of the closing prices.
        """
        df = self.data.copy()
        df['INDC_20HR_MA'] = df['<CLOSE>'].rolling(window=20).mean()
        df['INDC_50HR_MA'] = df['<CLOSE>'].rolling(window=50).mean()
        self.data = df
        return '20-hour MA calculated.'
    
    def calculate_indicators(self):
        """
        Calculate MFI and OBV indicators and update the data.
        """
        self.calculate_mfi()
        self.calculate_obv()
        self.calculate_ma()
        self.data = self.data.dropna().reset_index(drop=True)
        return 'Indicators calculated and data updated.'
    
    def generate_flags(self):
        df = self.data.copy()
        df['均线支持'] = np.where(
            (df['<CLOSE>'] >= df['INDC_20HR_MA'] * 0.97) & (df['<CLOSE>'] <= df['INDC_20HR_MA'] * 1.03) &
            (df['INDC_20HR_MA'] > df['INDC_50HR_MA']),
            True, False
        )

        df['MFI超卖反弹'] = np.where(
            (df['INDC_MFI'] < 30) & (df['INDC_MFI'].shift(1) >= 30) & 
            (df['INDC_MFI_SLOPE'] > 1),
            True, False
        )

        df['OBV量价背离'] = np.where(
            (df['<CLOSE>'] < df['<CLOSE>'].shift(1)) & 
            (df['INDC_OBV'] >= df['INDC_OBV'].shift(1)),
            True, False
        )

        self.data = df.dropna().reset_index(drop=True)
