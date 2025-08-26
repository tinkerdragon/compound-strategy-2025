import streamlit as st
from signals import MarketAnalyzer

st.title("美股技术指标分析")

analyzer = MarketAnalyzer()

ticker = st.text_input("输入美股代码 (e.g. AAPL):", "AAPL")
mfi_period = st.slider("MFI 周期:", 1, 50, 14)
mfi_slope_window = st.slider("MFI 梯度计算周期:", 1, 10, 3)


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
    except Exception as e:
        st.error(f'No data found for {ticker}. Please check stock list.')
