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

# Add info about auto-scaling feature
st.info("📊 提示: K线图支持自动Y轴缩放 - 使用鼠标框选或拖动底部滑块时，Y轴会自动调整以适配可见数据范围")

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
    price_change_lookback = st.slider("价格变化看回窗口:", 1, 10, 3)
    price_change_threshold = st.slider("价格变化阈值 (%):", 0.0, 20.0, 5.0, 0.5)

if st.button("🚀 开始分析"):
    try:
        with st.spinner('正在获取数据并计算指标...'):
            # Fetch and process data
            analyzer.fetch_data(ticker, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            analyzer.calculate_mfi(period=mfi_period, slope_window=mfi_slope_window)
            analyzer.calculate_ma()
            analyzer.calculate_obv()
            analyzer.calculate_candle_patterns(volume_multiplier=volume_multiplier)
            analyzer.generate_flags(signal_window=signal_window, slope_threshold=slope_threshold, lookback_window=lookback_window, price_change_lookback=price_change_lookback, price_change_threshold=price_change_threshold)
        
        # Display data
        st.success(f'✅ 成功加载 {ticker} 数据')
        
        # Display interactive instructions
        with st.expander("📖 图表交互说明"):
            st.markdown("""
            - **缩放**: 鼠标框选区域或使用滑块调整显示范围
            - **自动缩放**: Y轴会自动调整以适配当前显示的数据范围
            - **平移**: 按住鼠标左键拖动图表
            - **重置**: 双击图表恢复初始视图
            - **悬停**: 鼠标悬停查看详细数值
            """)
        
        # Display plots
        fig_candle, fig_multi = analyzer.create_figures(analyzer.data)
        
        # Candlestick chart with auto-scaling
        st.plotly_chart(fig_candle, use_container_width=False, config={'displayModeBar': True})
        
        # Multi-panel chart
        st.plotly_chart(fig_multi, use_container_width=False, config={'displayModeBar': True})
        
    except Exception as e:
        st.error(f"❌ 错误: {e}")
        st.info("请检查输入的股票代码和日期范围是否正确")