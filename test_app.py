import streamlit as st
from data import DataManager
from datetime import datetime

# Streamlit app
st.title("Stock Data Fetcher Tester")

# User inputs
symbol = st.text_input("Stock Symbol", value="AAPL")
start_date = st.date_input("Start Date", value=datetime(2023, 1, 1))
end_date = st.date_input("End Date", value=datetime.today())
timeframe = st.selectbox("Timeframe", ["Daily", "Hourly"])
mode = st.selectbox("Mode", ["Fallback", "Individual"])

provider = None
if mode == "Individual":
    dm = DataManager()  # Instantiate early to access PROVIDERS
    provider = st.selectbox("Provider", dm.PROVIDERS)

if st.button("Fetch Data"):
    dm = DataManager()
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    try:
        if timeframe == "Daily":
            if mode == "Fallback":
                df = dm.fetch_daily_data(symbol, start_str, end_str)
            else:
                fetch_func = getattr(dm, f'fetch_from_{provider}')
                st.write(f"Fetching daily data from {provider}")
                df = fetch_func(symbol, start_str, end_str)
                if df.empty:
                    st.write(f"No data fetched from {provider}")
        else:  # Hourly
            if mode == "Fallback":
                df = dm.fetch_hourly_data(symbol, start_str, end_str)
            else:
                fetch_func = getattr(dm, f'fetch_from_{provider}_hourly')
                st.write(f"Fetching hourly data from {provider}")
                df = fetch_func(symbol, start_str, end_str)
                if df.empty:
                    st.write(f"No data fetched from {provider}")
        
        if not df.empty:
            st.success("Data fetched successfully!")
            st.dataframe(df)
        else:
            st.warning("No data available for the given parameters.")
    except Exception as e:
        st.error(f"Error: {str(e)}")