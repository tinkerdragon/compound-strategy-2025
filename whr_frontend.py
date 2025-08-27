import streamlit as st
from whr_backend import MarketAnalyzer
from data import DataManager

st.title("美股技术指标分析")

analyzer = MarketAnalyzer()

ticker = st.text_input("输入美股代码 (e.g. AAPL):", "AAPL")
start_date = st.date_input("开始日期:", value=None, min_value=None, max_value=None)
end_date = st.date_input("结束日期:", value=None, min_value=None, max_value=None)
mfi_period = st.slider("MFI 周期:", 1, 50, 14)
mfi_slope_window = st.slider("MFI 梯度计算周期:", 1, 10, 3)


if st.button("🚀"):
    try:
        analyzer.fetch_data(ticker, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        analyzer.calculate_mfi(period=mfi_period, slope_window=mfi_slope_window)
        analyzer.calculate_ma()
        analyzer.calculate_obv()
        analyzer.drop()
        analyzer.generate_flags()
        st.dataframe(analyzer.show_data())
        st.plotly_chart(analyzer.plot())
    except Exception as e:
        st.error(e)
        st.error(f'No data found for {ticker}. Please check stock list.')
