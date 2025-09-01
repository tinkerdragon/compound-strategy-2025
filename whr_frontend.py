import streamlit as st
from whr_backend import MarketAnalyzer
from data import DataManager
from datetime import datetime

st.title("美股技术指标分析")

analyzer = MarketAnalyzer()

# Create columns for parameter inputs
col1, col2 = st.columns(2)

with col1:
    ticker = st.text_input("输入美股代码 (e.g. AAPL):", "AAPL")
    start_date = st.date_input("开始日期:", value=None, min_value=None, max_value=None)
    use_today = st.checkbox("使用今天日期", value=False)
    if use_today:
        end_date = datetime.today().date()
        st.write(f"结束日期: {end_date.strftime('%Y-%m-%d')} (今日)")
    else:
        end_date = st.date_input("结束日期:", value=None, min_value=None, max_value=None)

with col2:
    mfi_period = st.slider("MFI 周期:", 1, 50, 14)
    mfi_slope_window = st.slider("MFI 梯度计算周期:", 1, 10, 3)
    dip_window = st.slider("MFI 反弹检测窗口长度:", 1, 50, 5)
    slope_threshold = st.slider("MFI 反弹梯度:", 0.0, 5.0, 1.0, 0.1)

if st.button("🚀"):
    try:
        # Fetch and process data
        analyzer.fetch_data(ticker, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        analyzer.calculate_mfi(period=mfi_period, slope_window=mfi_slope_window)
        analyzer.calculate_ma()
        analyzer.calculate_obv()
        analyzer.calculate_candle_patterns()
        analyzer.generate_flags(dip_window=dip_window, slope_threshold=slope_threshold)
        
        # Display data
        st.dataframe(analyzer.show_data())
        
        # Display plot
        fig = analyzer.create_figure(analyzer.data)
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error: {e}")