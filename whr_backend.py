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
                             (abs(df['close'].shift(1) - df['open'].shift(1)) < 0.3 * (
                                         df['high'].shift(1) - df['low'].shift(1))) & \
                             (df['open'].shift(1) < df['close'].shift(2)) & \
                             (df['close'] > df['open']) & \
                             (df['close'] > (df['open'].shift(2) + df['close'].shift(2)) / 2)

        df['Shooting_Star'] = (df['upper_wick'] >= 2 * df['body']) & (df['lower_wick'] <= 0.5 * df['body'])

        df['Bearish_Engulfing'] = (df['close'].shift(1) > df['open'].shift(1)) & \
                                  (df['close'] < df['open']) & \
                                  (df['open'] > df['close'].shift(1)) & \
                                  (df['close'] < df['open'].shift(1))

        df['Evening_Star'] = (df['close'].shift(2) > df['open'].shift(2)) & \
                             (abs(df['close'].shift(1) - df['open'].shift(1)) < 0.3 * (
                                         df['high'].shift(1) - df['low'].shift(1))) & \
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

    def generate_flags(self, signal_window=5, slope_threshold=1.0, lookback_window=3, price_change_lookback=3,
                       price_change_threshold=5.0, selected_signals=None, signal_mode="Buy Signals"):
        df = self.data.copy()
        selected_signals = selected_signals or []

        # Define all possible signals
        if signal_mode == "Buy Signals":
            signal_definitions = {
                '均线支持': lambda df: np.where(
                    (df['close'] >= df['INDC_20HR_MA'] * 0.97) & (df['close'] <= df['INDC_20HR_MA'] * 1.03) &
                    (df['INDC_20HR_MA'] > df['INDC_50HR_MA']),
                    True, False
                ),
                'MFI超卖反弹': lambda df: np.where(
                    (df['INDC_MFI'].rolling(window=signal_window).min() < 30) &
                    (df['INDC_MFI_SLOPE'] >= slope_threshold),
                    True, False
                ),
                'Hammer': lambda df: df['Hammer'],
                'Morning_Star': lambda df: df['Morning_Star'],
                'Bullish_Engulfing': lambda df: df['Bullish_Engulfing'],
                'Volume_Surge': lambda df: df['Volume_Surge'],
                '价格上涨': lambda df: np.where(
                    ((df['close'] / df['close'].shift(price_change_lookback) - 1) * 100 > price_change_threshold),
                    True, False
                )
            }
        else:  # Sell Signals
            signal_definitions = {
                'MFI超买回落': lambda df: np.where(
                    (df['INDC_MFI'].rolling(window=signal_window).max() > 70) &
                    (df['INDC_MFI_SLOPE'] < -slope_threshold),
                    True, False
                ),
                'OBV熊背离': lambda df: np.where(
                    (df['close'] > df['close'].shift(1)) &
                    (df['INDC_OBV'] < df['INDC_OBV'].shift(1)),
                    True, False
                ),
                'Shooting_Star': lambda df: df['Shooting_Star'],
                'Evening_Star': lambda df: df['Evening_Star'],
                'Bearish_Engulfing': lambda df: df['Bearish_Engulfing'],
                'Volume_Surge': lambda df: df['Volume_Surge'],
                'MFI顶背离': lambda df: np.where(
                    (df['close'] > df['close'].shift(1)) &
                    (df['INDC_MFI'] < df['INDC_MFI'].shift(1)) &
                    (df['INDC_MFI'] > 70),
                    True, False
                )
            }

        # Calculate only the selected signals
        for signal in selected_signals:
            if signal in signal_definitions:
                df[signal] = signal_definitions[signal](df)

        self.data = df.dropna()

    def create_figures(self, df, selected_signals=None, signal_mode="Buy Signals"):
        selected_signals = selected_signals or []
        buy_cols = ['均线支持', 'MFI超卖反弹', 'Hammer', 'Morning_Star', 'Bullish_Engulfing', 'Volume_Surge', '价格上涨']
        sell_cols = ['MFI超买回落', 'OBV熊背离', 'Shooting_Star', 'Evening_Star', 'Bearish_Engulfing', 'Volume_Surge', 'MFI顶背离']
        
        # Filter signals based on mode and user selection
        if signal_mode == "Buy Signals":
            active_cols = [col for col in selected_signals if col in buy_cols and col in df.columns]
        else:
            active_cols = [col for col in selected_signals if col in sell_cols and col in df.columns]

        if not active_cols:
            raise ValueError(f"No valid signals selected for {signal_mode}")

        # Use numeric index for the x-axis in all plots
        x_idx = np.arange(len(df))
        try:
            time_str = pd.to_datetime(df.index).strftime('%Y-%m-%d %H:%M')
        except Exception:
            time_str = df.index.astype(str)
        customdata_ts = np.column_stack([time_str])

        # Create candlestick figure
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

        # Add annotations for bullish or bearish patterns based on mode
        if signal_mode == "Buy Signals":
            bullish_mask = df[active_cols].any(axis=1)
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
                    ay=-30
                )
        else:
            bearish_mask = df[active_cols].any(axis=1)
            bearish_indices = np.where(bearish_mask)[0]
            for i in bearish_indices:
                fig_candle.add_annotation(
                    x=x_idx[i],
                    y=df.iloc[i]['high'],
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1.5,
                    arrowwidth=2,
                    arrowcolor="blue",
                    ax=0,
                    ay=30
                )

        fig_candle.update_layout(
            height=600,
            width=2000,
            title_text=f"Candlestick Chart with MAs ({signal_mode}, Auto-scaling Y-axis)",
            xaxis_title="Index",
            yaxis_title="Price",
            xaxis=dict(
                rangeslider=dict(
                    visible=True,
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
        fig_candle.update_xaxes(rangeslider_yaxis_rangemode='match')

        # Create multiplot subplots
        fig_multi = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            row_heights=[0.3, 0.3, 0.4],
            vertical_spacing=0.03,
            subplot_titles=(f"{signal_mode} Heatmap", "MFI", "Volume")
        )

        # Plot signal heatmap
        signal_data = df[active_cols].astype(int).T
        fig_multi.add_trace(
            go.Heatmap(
                z=signal_data.values,
                x=x_idx,
                y=signal_data.index,
                colorscale='YlGnBu' if signal_mode == "Buy Signals" else 'YlOrRd',
                showscale=True,
                colorbar=dict(title=signal_mode),
            ),
            row=1, col=1
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
            row=2, col=1
        )

        # Overbought/oversold lines
        fig_multi.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
        fig_multi.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)

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
            row=3, col=1
        )

        fig_multi.update_layout(
            height=1200,
            width=2000,
            title_text=f"{signal_mode}, MFI, Volume",
            xaxis3_title="Index",
            yaxis_title=signal_mode,
            yaxis2_title="MFI",
            yaxis3_title="Volume",
            yaxis=dict(autorange=True),
            yaxis2=dict(autorange=True),
            yaxis3=dict(autorange=True),
            xaxis_rangeslider_visible=False,
            hovermode="x unified",
            dragmode="zoom",
            plot_bgcolor="white",
            margin=dict(l=50, r=50, t=100, b=50),
            showlegend=True,
        )

        return fig_candle, fig_multi