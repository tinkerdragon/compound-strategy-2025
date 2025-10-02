# whr_backend.py
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

        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        self.data[numeric_cols] = self.data[numeric_cols].apply(pd.to_numeric, errors='coerce')
        self.data = self.data.dropna(subset=numeric_cols)
        
        self.data['datetime'] = pd.to_datetime(self.data['datetime'])
        self.data.set_index('datetime', inplace=True)
        # Filter for hours between 13:00 and 19:00
        self.data = self.data[self.data.index.hour.isin(range(13, 20))]
        # Remove non-trading days (days with no trading activity, i.e., total volume == 0)
        self.data['date'] = self.data.index.date
        daily_volume = self.data.groupby('date')['volume'].sum()
        trading_days = daily_volume[daily_volume > 0].index
        self.data = self.data[self.data['date'].isin(trading_days)]
        self.data = self.data.drop(columns=['date'])
    
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
        
        df['Shooting_Star'] = (df['upper_wick'] >= 2 * df['body']) & (df['lower_wick'] <= 0.5 * df['body'])
        
        df['Bearish_Engulfing'] = (df['close'].shift(1) > df['open'].shift(1)) & \
                                  (df['close'] < df['open']) & \
                                  (df['open'] > df['close'].shift(1)) & \
                                  (df['close'] < df['open'].shift(1))
        
        df['Evening_Star'] = (df['close'].shift(2) > df['open'].shift(2)) & \
                             (abs(df['close'].shift(1) - df['open'].shift(1)) < 0.3 * (df['high'].shift(1) - df['low'].shift(1))) & \
                             (df['open'].shift(1) > df['close'].shift(2)) & \
                             (df['close'] < df['open']) & \
                             (df['close'] < (df['open'].shift(2) + df['close'].shift(2)) / 2)
        
        df['prev_avg_vol'] = df['volume'].shift(1).rolling(3).mean()
        df['Volume_Surge'] = df['volume'] > volume_multiplier * df['prev_avg_vol']
        
        df = df.drop(['body', 'lower_wick', 'upper_wick', 'prev_avg_vol'], axis=1)
        
        self.data = df.dropna()
        return 'Candle patterns calculated.'
    
    def drop(self):
        self.data = self.data.dropna()
        return 'Indicators calculated and data updated.'
    
    def generate_flags(self, signal_window=5, slope_threshold=1.0, lookback_window=3, price_change_lookback=3, price_change_threshold=5.0):
        df = self.data.copy()
        df['均线支持'] = np.where(
            (df['close'] >= df['INDC_20HR_MA'] * 0.97) & (df['close'] <= df['INDC_20HR_MA'] * 1.03) &
            (df['INDC_20HR_MA'] > df['INDC_50HR_MA']),
            True, False
        )

        df['MFI超卖反弹'] = np.where(
            (df['INDC_MFI'].rolling(window=signal_window).min() < 30) & 
            (df['INDC_MFI_SLOPE'] >= slope_threshold),
            True, False
        )

        df['MFI超买回落'] = np.where(
            (df['INDC_MFI'].rolling(window=signal_window).max() > 70) & 
            (df['INDC_MFI_SLOPE'] < -slope_threshold),
            True, False
        )

        df['MFI顶背离'] = np.where(
            (df['close'] > df['close'].shift(1)) & 
            (df['INDC_MFI'] < df['INDC_MFI'].shift(1)) &
            (df['INDC_MFI'] > 70),
            True, False
        )

        df['OBV熊背离'] = np.where(
            (df['close'] > df['close'].shift(1)) & 
            (df['INDC_OBV'] < df['INDC_OBV'].shift(1)),
            True, False
        )

        df['价格上涨'] = np.where(
            ((df['close'] / df['close'].shift(price_change_lookback) - 1) * 100 > price_change_threshold),
            True, False
        )

        df['成交量增加'] = df['volume'] > df['volume'].shift(1)

        self.data = df.dropna()

    def create_figures(self, df):
        # Columns needed for the heatmaps
        buy_cols = ['均线支持', 'MFI超卖反弹', 'Hammer', 'Morning_Star', 'Bullish_Engulfing', 'Volume_Surge', '价格上涨']
        sell_cols = ['MFI超买回落', 'OBV熊背离', 'Shooting_Star', 'Evening_Star', 'Bearish_Engulfing', 'Volume_Surge', 'MFI顶背离']
        if not all(col in df.columns for col in buy_cols + sell_cols):
            missing = set(buy_cols + sell_cols) - set(df.columns)
            raise ValueError(f"Missing columns: {missing}")
        
        # Use numeric index for the x-axis in all plots
        x_idx = np.arange(len(df))
        # Keep readable time in hover (if index is datetime-like)
        try:
            time_str = pd.to_datetime(df.index).strftime('%Y-%m-%d %H:%M')
        except Exception:
            # Fallback in case index is not datetime-like
            time_str = df.index.astype(str)
        # For candlestick hovertemplate we can use customdata as 2D array
        customdata_ts = np.column_stack([time_str])

        buy_data = df[buy_cols].astype(int).T
        sell_data = df[sell_cols].astype(int).T

        # Create candlestick figure with auto-ranging y-axis on zoom
        fig_candle = go.Figure(data=[go.Candlestick(
            x=x_idx,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Candlestick',
            customdata=customdata_ts,
        )])

        # Add 20HR MA
        fig_candle.add_trace(
            go.Scatter(
                x=x_idx,
                y=df['INDC_20HR_MA'],
                mode='lines',
                name='20HR MA',
                line=dict(color='orange'),
                customdata=time_str,
                hovertemplate="Index: %{x}<br>Time: %{customdata}<br>20HR MA: %{y:.4f}<extra></extra>"
            )
        )

        # Add 50HR MA
        fig_candle.add_trace(
            go.Scatter(
                x=x_idx,
                y=df['INDC_50HR_MA'],
                mode='lines',
                name='50HR MA',
                line=dict(color='green'),
                customdata=time_str,
                hovertemplate="Index: %{x}<br>Time: %{customdata}<br>50HR MA: %{y:.4f}<extra></extra>"
            )
        )

        # Add red upward arrows for bullish candle patterns
        bullish_mask = df['Hammer'] | df['Morning_Star'] | df['Bullish_Engulfing']
        bullish_indices = np.where(bullish_mask)[0]
        for i in bullish_indices:
            fig_candle.add_annotation(
                x=x_idx[i],
                y=df.iloc[i]['low'],
                showarrow=True,
                arrowhead=2,
                arrowsize=1.5,
                arrowwidth=2,
                arrowcolor="red",
                ax=0,
                ay=-30  # Offset below the low
            )

        # Update layout with auto-ranging y-axis
        fig_candle.update_layout(
            height=600,
            width=2000,
            title_text="Candlestick Chart with MAs (Auto-scaling Y-axis)",
            xaxis_title="Index",
            yaxis_title="Price",
            xaxis=dict(
                rangeslider=dict(
                    visible=True,
                    # This is the key setting for auto-ranging y-axis
                    yaxis=dict(rangemode='match')
                ),
                type='linear'
            ),
            yaxis=dict(
                autorange=True,
                fixedrange=False,
                type='linear'
            ),
            hovermode="x unified",
            dragmode="zoom",
            plot_bgcolor="white",
            margin=dict(l=50, r=50, t=100, b=50),
            showlegend=True,
        )
        
        # Enable auto-ranging on zoom for the main plot area as well
        fig_candle.update_xaxes(rangeslider_yaxis_rangemode='match')

        # Create multiplot subplots
        fig_multi = make_subplots(
            rows=4, cols=1,
            shared_xaxes=True,
            row_heights=[0.25, 0.25, 0.25, 0.25],
            vertical_spacing=0.03,
            subplot_titles=("Buy Signal Heatmap", "Sell Signal Heatmap", "MFI", "Volume")
        )

        # Plot buy heatmap
        fig_multi.add_trace(
            go.Heatmap(
                z=buy_data.values,
                x=x_idx,
                y=buy_data.index,
                colorscale='YlGnBu',
                showscale=True,
                colorbar=dict(title='Buy Signal'),
            ),
            row=1, col=1
        )

        # Plot sell heatmap
        fig_multi.add_trace(
            go.Heatmap(
                z=sell_data.values,
                x=x_idx,
                y=sell_data.index,
                colorscale='YlOrRd',
                showscale=True,
                colorbar=dict(title='Sell Signal'),
            ),
            row=2, col=1
        )

        # Plot MFI
        fig_multi.add_trace(
            go.Scatter(
                x=x_idx,
                y=df['INDC_MFI'],
                mode='lines',
                name='MFI',
                line=dict(color='purple'),
                customdata=time_str,
                hovertemplate="Index: %{x}<br>Time: %{customdata}<br>MFI: %{y:.2f}<extra></extra>"
            ),
            row=3, col=1
        )

        # Overbought/oversold lines
        fig_multi.add_hline(y=70, line_dash="dot", line_color="red", row=3, col=1)
        fig_multi.add_hline(y=30, line_dash="dot", line_color="green", row=3, col=1)

        # Plot Volume
        fig_multi.add_trace(
            go.Bar(
                x=x_idx,
                y=df['volume'],
                name='Volume',
                marker_color='blue',
                customdata=time_str,
                hovertemplate="Index: %{x}<br>Time: %{customdata}<br>Volume: %{y}<extra></extra>"
            ),
            row=4, col=1
        )

        # Update layout for better appearance
        fig_multi.update_layout(
            height=1400,
            width=2000,
            title_text="Buy and Sell Signal Heatmaps, MFI, Volume",
            xaxis4_title="Index",
            yaxis_title="Buy Signals",
            yaxis2_title="Sell Signals",
            yaxis3_title="MFI",
            yaxis4_title="Volume",
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

        return fig_candle, fig_multi
