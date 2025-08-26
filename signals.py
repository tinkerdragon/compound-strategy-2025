import pandas as pd
import os
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data import DataManager

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

    def fetch_data(self, ticker, start_date, end_date):
        manager = DataManager()
        self.data = manager.fetch_daily_data(ticker, start_date, end_date)
    
    def show_data(self):
        """Display the first few rows of the stored data sequence."""
        return self.data

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
    
    def drop(self):
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

    def plot(self):
        bool_cols = ['均线支持', 'MFI超卖反弹', 'OBV量价背离']
        data = self.data[bool_cols].astype(int).T
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            row_heights=[0.6, 0.4],
            vertical_spacing=0.1,
            subplot_titles=("Close", "Signal Heatmap")
        )
        fig.add_trace(
            go.Scatter(
                x=self.data.index,
                y=self.data['<CLOSE>'],
                mode='lines',
                name='Close',
                line=dict(color='white')
            ),
            row=1, col=1
        )
        fig.add_trace(
            go.Heatmap(
                z=data.values,
                x=self.data.index,
                y=data.index,
                colorscale='YlGnBu',
                showscale=True,
                colorbar=dict(title='Signal'),
            ),
            row=2, col=1
        )
        fig.update_layout(
            height=600,
            title_text=f"Close Prices and Signal Heatmap",
            xaxis2_title="Index",
            yaxis_title="Close",
            yaxis2_title="Signals"
        )

        fig.update_layout(
            plot_bgcolor="rgba(14, 17, 23, 1)",
        )

        return fig