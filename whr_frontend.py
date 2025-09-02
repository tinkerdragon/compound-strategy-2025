import streamlit as st
from whr_backend import MarketAnalyzer
from data import DataManager
from datetime import datetime

st.title("美股技术指标分析")

analyzer = MarketAnalyzer()

st.markdown("""
    <style>
    .block-container {
        padding-left: 15rem !important;
        padding-right: 15rem !important;
        max-width: 100% !important;
    }
    </style>
""", unsafe_allow_html=True)

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
    volume_multiplier = st.slider("成交量激增倍数:", 1.0, 5.0, 2.0, 0.1)

with col2:
    mfi_period = st.slider("MFI 周期:", 1, 50, 14, help="计算MFI的周期长度")
    mfi_slope_window = st.slider("MFI 梯度计算周期:", 1, 10, 3, help="用于计算MFI回弹梯度的窗口长度")
    signal_window = st.slider("MFI 信号检测窗口长度:", 1, 50, 5, help="用于检测MFI摸底回弹的窗口长度")
    slope_threshold = st.slider("MFI 反弹梯度:", 0.0, 5.0, 1.0, 0.1, help="判断MFI反弹的梯度阈值")
    lookback_window = st.slider("MA破位看回窗口:", 1, 10, 3)
    

if st.button("🚀"):
    try:
        # Fetch and process data
        analyzer.fetch_data(ticker, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        analyzer.calculate_mfi(period=mfi_period, slope_window=mfi_slope_window)
        analyzer.calculate_ma()
        analyzer.calculate_obv()
        analyzer.calculate_candle_patterns(volume_multiplier=volume_multiplier)
        analyzer.generate_flags(signal_window=signal_window, slope_threshold=slope_threshold, lookback_window=lookback_window)
        
        # Display data
        st.success('Data successfully loaded.')
        
        # Display plot
        fig_candle, fig_multi = analyzer.create_figures(analyzer.data)
        st.plotly_chart(fig_candle, use_container_width=False)
        st.plotly_chart(fig_multi, use_container_width=False)
        
    except Exception as e:
        st.error(f"Error: {e}")