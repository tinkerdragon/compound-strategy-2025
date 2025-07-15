import streamlit as st
from signals import MarketAnalyzer

st.title("Market Analyzer")

analyzer = MarketAnalyzer()

ticker = st.text_input("Enter Ticker Symbol (e.g., AAPL):", "AAPL")
mfi_period = st.slider("MFI Period:", 1, 50, 14)
mfi_slope_window = st.slider("MFI Slope Window:", 1, 10, 3)


if st.button("🚀"):
    try:
        analyzer.fetch_data(ticker)
        analyzer.calculate_mfi(period=mfi_period, slope_window=mfi_slope_window)
        analyzer.calculate_ma()
        analyzer.calculate_obv()
        analyzer.drop()
        analyzer.generate_flags()
        st.dataframe(analyzer.show_data())
        st.plotly_chart(analyzer.plot())
    except AttributeError as e:
        st.error(f'No data found for {ticker}. Please check stock list.')