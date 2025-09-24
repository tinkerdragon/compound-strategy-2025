# US Stock Technical Analysis Dashboard 📈

A Streamlit-based web application for analyzing technical indicators of U.S. stocks, including S&P 500 components or user-specified tickers. The dashboard fetches hourly stock data, calculates indicators like MFI (Money Flow Index), OBV (On-Balance Volume), and moving averages, detects candlestick patterns, and visualizes results with interactive charts. 🚀

## ✨ Features
- **S&P 500 Analysis**: Analyze all ~500 S&P 500 stocks or input custom tickers. 📊
- **Technical Indicators**:
  - Money Flow Index (MFI) with oversold/overbought signals and slope analysis. 📉
  - On-Balance Volume (OBV) for trend confirmation. 📈
  - 20-hour and 50-hour Moving Averages (MA) for support/resistance. 📅
- **Candlestick Patterns**: Detects Hammer, Bullish Engulfing, Morning Star, Shooting Star, Bearish Engulfing, and Evening Star. 🕯️
- **Interactive Charts**: Plotly-powered candlestick charts with auto-scaling Y-axis and multi-panel views for buy/sell signals, MFI, and volume. 📊
- **Volume Surge Detection**: Flags stocks with significant volume increases. ⚡
- **Flexible Parameters**: Customize MFI periods, slope thresholds, volume multipliers, and more via Streamlit sliders. 🎚️
- **Robust Data Fetching**: Uses multiple APIs (Polygon, TwelveData, FMP, Alpha Vantage) with fallback for reliability. 🌐
- **User-Friendly Interface**: Streamlit UI with progress bars, error handling, and interactive instructions. 😊

## 🛠️ Prerequisites
- Python 3.8 or higher 🐍
- A virtual environment (recommended) 🖥️
- API keys for at least one of the following data providers:
  - [Polygon](https://polygon.io/) 🔑
  - [TwelveData](https://twelvedata.com/) 🔑
  - [Financial Modeling Prep (FMP)](https://financialmodelingprep.com/) 🔑
  - [Alpha Vantage](https://www.alphavantage.co/) 🔑
  - [EODHD](https://eodhd.com/) 🔑
  - [Marketstack](https://marketstack.com/) 🔑
- A `.env` file with API keys (see [Setup](#setup) below).

## 🔧 Setup
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/us-stock-analysis.git
   cd us-stock-analysis
