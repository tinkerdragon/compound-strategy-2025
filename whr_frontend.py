# whr_frontend.py
import streamlit as st
from whr_backend import MarketAnalyzer
from data import DataManager
from datetime import datetime
import pandas as pd
import requests
import io

if 'analyzers' not in st.session_state:
    st.session_state.analyzers = None
if 'signaling_tickers' not in st.session_state:
    st.session_state.signaling_tickers = []
if 'attempted_count' not in st.session_state:
    st.session_state.attempted_count = 0
if 'selected_ticker' not in st.session_state:
    st.session_state.selected_ticker = None
if 'show_dropdown' not in st.session_state:
    st.session_state.show_dropdown = True

st.title("美股技术指标分析")

st.markdown("""
    <style>
    .block-container {
        padding-left: 15rem !important;
        padding-right: 15rem !important;
        max-width: 100% !important;
    }
    .ticker-button {
        margin: 5px;
        padding: 8px 16px;
        background-color: #4CAF50;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
    }
    .ticker-button:hover {
        background-color: #45a049;
    }
    .dropdown-button {
        margin: 5px;
        padding: 8px 16px;
        background-color: #008CBA;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
    }
    .dropdown-button:hover {
        background-color: #007399;
    }
    </style>
""", unsafe_allow_html=True)

# Add info about auto-scaling feature
st.info("📊 提示: K线图支持自动Y轴缩放 - 使用鼠标框选或拖动底部滑块时，Y轴会自动调整以适配可见数据范围")

# Function to get S&P 500 tickers
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_sp500_tickers():
    """Fetch S&P 500 tickers from Wikipedia with proper headers"""
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        tables = pd.read_html(io.StringIO(response.text))
        sp500_table = tables[0]
        tickers = sp500_table['Symbol'].tolist()
        # Remove any invalid characters or formatting issues
        tickers = [ticker.replace('.', '-') for ticker in tickers]
        return tickers
    except Exception as e:
        st.error(f"Failed to fetch S&P 500 list: {e}")
        # Fallback to a smaller sample if web scraping fails
        return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK-B', 'JPM', 'UNH']

# Create columns for parameter inputs
col1, col2 = st.columns(2)

with col1:
    use_sp500 = st.checkbox("🔥 分析所有S&P 500股票 (约500只)", help="启用后将自动分析S&P 500指数成分股，耗时较长")
    
    if use_sp500:
        ticker_input = st.text_input("输入额外股票代码 (逗号分隔):", "", help="除了S&P 500外，可添加其他股票")
        extra_tickers = [t.strip().upper() for t in ticker_input.split(',') if t.strip()]
        sp500_tickers = get_sp500_tickers()
        tickers = sp500_tickers + extra_tickers
        st.info(f"📊 将分析 {len(sp500_tickers)} 只S&P 500股票 + {len(extra_tickers)} 只额外股票 = 总计 {len(tickers)} 只股票")
    else:
        ticker_input = st.text_input("输入美股代码列表 (e.g. AAPL,GOOG,MSFT):", "AAPL")
        tickers = [t.strip().upper() for t in ticker_input.split(',') if t.strip()]
    
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

# Warning for large analysis
if use_sp500 and len(tickers) > 50:
    st.warning(f"⚠️ 即将分析 {len(tickers)} 只股票，这可能需要 {len(tickers)*2-5} 分钟时间。请耐心等待...")

# Create a container for real-time error display
error_container = st.container()

if st.button("🚀 开始分析"):
    if not tickers:
        st.error("❌ 请至少输入一个股票代码或启用S&P 500分析")
    else:
        try:
            with st.spinner(f'正在获取数据并计算指标... (0/{len(tickers)}股票)'):
                analyzers = {}
                signaling_tickers = []
                progress_bar = st.progress(0)
                successful_count = 0
                failed_tickers = []
                
                # Clear the error container before starting
                with error_container:
                    st.empty()
                
                for i, t in enumerate(tickers):
                    try:
                        analyzer = MarketAnalyzer()
                        analyzer.fetch_data(t, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
                        
                        # Skip if no data
                        if analyzer.data.empty:
                            failed_tickers.append(t)
                            with error_container:
                                st.error(f"{t}: No data returned")
                            continue
                            
                        analyzer.calculate_mfi(period=mfi_period, slope_window=mfi_slope_window)
                        analyzer.calculate_ma()
                        analyzer.calculate_obv()
                        analyzer.calculate_candle_patterns(volume_multiplier=volume_multiplier)
                        analyzer.generate_flags(signal_window=signal_window, slope_threshold=slope_threshold, 
                                              lookback_window=lookback_window, price_change_lookback=price_change_lookback, 
                                              price_change_threshold=price_change_threshold)
                        analyzers[t] = analyzer
                        successful_count += 1
                        
                        # Check for signals at the latest data point
                        df = analyzer.data
                        if not df.empty:
                            latest = df.iloc[-1]
                            # More flexible signal condition - at least 3 out of 4 conditions
                            signal_conditions = [
                                latest.get('MFI超卖反弹', False),
                                latest.get('均线支持', False), 
                                latest.get('Volume_Surge', False),
                                latest.get('成交量增加', False)
                            ]
                            active_signals = sum(signal_conditions)
                            if active_signals >= 3:  # At least 3 out of 4 conditions
                                signaling_tickers.append(t)
                        
                        st.toast(f" {t} 分析完成 ({i+1}/{len(tickers)})", icon="✅")
                        
                    except Exception as e:
                        failed_tickers.append(t)
                        with error_container:
                            st.error(f"{t}: {str(e)}")
                        st.toast(f" {t} 分析失败: {str(e)[:50]}...", icon="❌")
                    
                    progress_bar.progress((i + 1) / len(tickers))
                
                # Update progress summary
                progress_text = f"完成! 成功: {successful_count}/{len(tickers)} 股票"
                if failed_tickers:
                    progress_text += f" | 失败: {len(failed_tickers)} 股票"
                st.success(progress_text)
                
                if failed_tickers:
                    with st.expander(f"❌ 查看失败的股票 ({len(failed_tickers)} 只)"):
                        st.write(", ".join(failed_tickers[:20]))
                        if len(failed_tickers) > 20:
                            st.write(f"... 还有 {len(failed_tickers)-20} 只股票失败")
            
            st.session_state.analyzers = analyzers
            st.session_state.signaling_tickers = signaling_tickers
            st.session_state.attempted_count = len(tickers)
            st.session_state.show_dropdown = True  # Reset dropdown visibility after analysis
            
        except Exception as e:
            with error_container:
                st.error(f"分析过程中发生错误: {e}")
            st.info("请检查网络连接和日期范围是否正确")

# Display results if data is available
if st.session_state.analyzers is not None and st.session_state.analyzers:
    total_analyzed = len(st.session_state.analyzers)
    st.success(f'✅ 成功分析 {total_analyzed} 只股票数据')
    
    col_metric1, col_metric2 = st.columns(2)
    with col_metric1:
        st.metric("总分析股票数", st.session_state.attempted_count)
    with col_metric2:
        st.metric("信号股票数", len(st.session_state.signaling_tickers))
    
    if st.session_state.signaling_tickers:
        st.success(f"📈 具有强信号的股票 ({len(st.session_state.signaling_tickers)} 只):")
        button_container = st.container()
        with button_container:
            button_cols = st.columns(5)
            for i, ticker in enumerate(st.session_state.signaling_tickers):
                with button_cols[i % 5]:
                    if st.button(ticker, key=f"btn_{ticker}", help=f"View charts for {ticker}"):
                        st.session_state.selected_ticker = ticker
                        st.session_state.show_dropdown = False  # Hide dropdown when button is clicked
            # Add button to show dropdown
            st.button("🔍 Show Ticker Dropdown", key="show_dropdown_btn", help="Show the dropdown menu to select other tickers", on_click=lambda: st.session_state.update(show_dropdown=True))
    
    else:
        st.info("🛑 没有股票满足强信号条件 (至少3/4个买入条件)")
    
    # Display interactive instructions
    with st.expander("📖 图表交互说明"):
        st.markdown("""
        - **缩放**: 鼠标框选区域或使用滑块调整显示范围
        - **自动缩放**: Y轴会自动调整以适配当前显示的数据范围
        - **平移**: 按住鼠标左键拖动图表
        - **重置**: 双击图表恢复初始视图
        - **悬停**: 鼠标悬停查看详细数值
        """)
    
    # Show dropdown only if show_dropdown is True
    if st.session_state.show_dropdown:
        signal_options = st.session_state.signaling_tickers + [t for t in st.session_state.analyzers.keys() if t not in st.session_state.signaling_tickers]
        default_signal = st.session_state.signaling_tickers[0] if st.session_state.signaling_tickers else (signal_options[0] if signal_options else None)
        selected_ticker = st.selectbox(
            "选择股票查看图表:",
            signal_options,
            index=signal_options.index(default_signal) if default_signal in signal_options else 0,
            key="ticker_select"
        )
        if selected_ticker:
            st.session_state.selected_ticker = selected_ticker
            st.session_state.show_dropdown = True  # Keep dropdown visible if used
    
    # Display charts for the selected ticker
    selected_ticker = st.session_state.selected_ticker
    if selected_ticker and selected_ticker in st.session_state.analyzers:
        analyzer = st.session_state.analyzers[selected_ticker]
        fig_candle, fig_multi = analyzer.create_figures(analyzer.data)
        
        # Candlestick chart with auto-scaling
        st.plotly_chart(fig_candle, use_container_width=False, config={'displayModeBar': True})
        
        # Multi-panel chart
        st.plotly_chart(fig_multi, use_container_width=False, config={'displayModeBar': True})
    else:
        if selected_ticker:
            st.error(f"❌ 股票 {selected_ticker} 的数据不可用")
else:
    if st.button("🔄 刷新S&P 500列表"):
        st.cache_data.clear()
        st.rerun()