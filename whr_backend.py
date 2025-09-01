import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data import DataManager

class MarketAnalyzer:
    def __init__(self):
        self.data = []

    def fetch_data(self, ticker, start_date, end_date):
        manager = DataManager()
        self.data = manager.fetch_hourly_data(ticker, start_date, end_date)
    
    def show_data(self):
        """Display the first few rows of the stored data sequence."""
        return self.data

    def calculate_mfi(self, period=14, slope_window=3):
        df = self.data.copy()
        
        df['Typical_Price'] = (df['high'] + df['low'] + df['close']) / 3
        df['Raw_Money_Flow'] = df['Typical_Price'] * df['volume']
        
        df['Price_Change'] = df['Typical_Price'].diff()
        df['Positive_Flow'] = np.where(df['Price_Change'] > 0, df['Raw_Money_Flow'], 0)
        df['Negative_Flow'] = np.where(df['Price_Change'] < 0, df['Raw_Money_Flow'], 0)
        
        positive_sum = df['Positive_Flow'].rolling(window=period).sum()
        negative_sum = df['Negative_Flow'].rolling(window=period).sum()
        
        df['Money_Flow_Ratio'] = positive_sum / (negative_sum + 1e-10)
        df['INDC_MFI'] = 100 - (100 / (1 + df['Money_Flow_Ratio']))

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
                    'Positive_Flow', 'Negative_Flow', 'Money_Flow_Ratio'], axis=1).dropna()
        
        self.data = df
        return 'MFI calculation completed.'
    
    def calculate_obv(self):
        df = self.data.copy()
        
        df['Price_Change'] = df['close'].diff()
        df['Direction'] = np.where(df['Price_Change'] > 0, 1, np.where(df['Price_Change'] < 0, -1, 0))
        
        df['INDC_OBV'] = (df['volume'] * df['Direction']).cumsum()
        df = df.drop(['Price_Change', 'Direction'], axis=1).dropna()
        
        self.data = df
        return 'OBV calculation completed.'
    
    def calculate_ma(self):
        df = self.data.copy()
        df['INDC_20HR_MA'] = df['close'].rolling(window=20).mean()
        df['INDC_50HR_MA'] = df['close'].rolling(window=50).mean()
        self.data = df
        return '20-hour MA calculated.'
    
    def calculate_candle_patterns(self, volume_multiplier=2.0):
        df = self.data.copy()
        
        df['body'] = abs(df['close'] - df['open'])
        df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
        df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['Hammer'] = (df['lower_wick'] >= 2 * df['body']) & (df['upper_wick'] <= 0.5 * df['body'])
        
        df['Bullish_Engulfing'] = (df['close'].shift(1) < df['open'].shift(1)) & \
                                  (df['close'] > df['open']) & \
                                  (df['open'] < df['close'].shift(1)) & \
                                  (df['close'] > df['open'].shift(1))
        
        df['Morning_Star'] = (df['close'].shift(2) < df['open'].shift(2)) & \
                             (abs(df['close'].shift(1) - df['open'].shift(1)) < 0.3 * (df['high'].shift(1) - df['low'].shift(1))) & \
                             (df['open'].shift(1) < df['close'].shift(2)) & \
                             (df['close'] > df['open']) & \
                             (df['close'] > (df['open'].shift(2) + df['close'].shift(2)) / 2)
        
        df['prev_avg_vol'] = df['volume'].shift(1).rolling(3).mean()
        df['Volume_Surge'] = df['volume'] > volume_multiplier * df['prev_avg_vol']
        
        df = df.drop(['body', 'lower_wick', 'upper_wick', 'prev_avg_vol'], axis=1)
        
        self.data = df.dropna()
        return 'Candle patterns calculated.'
    
    def drop(self):
        self.data = self.data.dropna()
        return 'Indicators calculated and data updated.'
    
    def generate_flags(self, dip_window=5, slope_threshold=1.0):
        df = self.data.copy()
        df['均线支持'] = np.where(
            (df['close'] >= df['INDC_20HR_MA'] * 0.97) & (df['close'] <= df['INDC_20HR_MA'] * 1.03) &
            (df['INDC_20HR_MA'] > df['INDC_50HR_MA']),
            True, False
        )

        df['MFI超卖反弹'] = np.where(
            (df['INDC_MFI'].rolling(window=dip_window).min() < 30) & 
            (df['INDC_MFI_SLOPE'] > slope_threshold),
            True, False
        )

        df['OBV量价背离'] = np.where(
            (df['close'] < df['close'].shift(1)) & 
            (df['INDC_OBV'] >= df['INDC_OBV'].shift(1)),
            True, False
        )

        self.data = df.dropna()

    def create_figure(self, df):
        bool_cols = ['均线支持', 'MFI超卖反弹', 'OBV量价背离', 'Hammer', 'Morning_Star', 'Bullish_Engulfing', 'Volume_Surge']
        if not all(col in df.columns for col in bool_cols):
            raise ValueError(f"Missing columns: {set(bool_cols) - set(df.columns)}")
        data = df[bool_cols].astype(int).T
        
        # Create subplots with adjusted heights and spacing
        fig = make_subplots(
            rows=4, cols=1,
            shared_xaxes=True,
            row_heights=[0.3, 0.2, 0.2, 0.3],  # Adjusted for better proportion
            vertical_spacing=0.03,  # Increased spacing
            subplot_titles=("Closing Price", "MFI", "Volume", "Signal Heatmap")
        )
        
        # Plot closing price as a line
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['close'],
                mode='lines',
                name='Close Price',
                line=dict(color='blue')
            ),
            row=1, col=1
        )
        
        # Plot 20HR MA
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['INDC_20HR_MA'],
                mode='lines',
                name='20HR MA',
                line=dict(color='orange')
            ),
            row=1, col=1
        )
        
        # Plot 50HR MA
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['INDC_50HR_MA'],
                mode='lines',
                name='50HR MA',
                line=dict(color='green')
            ),
            row=1, col=1
        )
        
        # Plot MFI
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['INDC_MFI'],
                mode='lines',
                name='MFI',
                line=dict(color='purple')
            ),
            row=2, col=1
        )
        
        # Add overbought/oversold lines
        fig.add_hline(y=80, line_dash="dot", line_color="red", row=2, col=1)
        fig.add_hline(y=20, line_dash="dot", line_color="green", row=2, col=1)
        
        # Plot Volume
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['volume'],
                name='Volume',
                marker_color='blue'
            ),
            row=3, col=1
        )
        
        # Plot heatmap
        fig.add_trace(
            go.Heatmap(
                z=data.values,
                x=df.index,
                y=data.index,
                colorscale='YlGnBu',
                showscale=True,
                colorbar=dict(title='Signal'),
            ),
            row=4, col=1
        )
        
        # Update layout for better appearance
        fig.update_layout(
            height=1000,  # Increased height for better visibility
            title_text="Closing Price, MFI, Volume, and Signal Heatmap",
            xaxis4_title="Date",
            yaxis_title="Price",
            yaxis2_title="MFI",
            yaxis3_title="Volume",
            yaxis4_title="Signals",
            yaxis=dict(autorange=True),
            yaxis2=dict(autorange=True),
            yaxis3=dict(autorange=True),
            yaxis4=dict(autorange=True),
            xaxis_rangeslider_visible=False,
            hovermode="x unified",
            dragmode="zoom",
            plot_bgcolor="white",
            margin=dict(l=50, r=50, t=100, b=50),
            showlegend=True,
        )
        
        return fig