import os
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(page_title="NZ FTR Node Price Dashboard", layout="wide")

# Title
st.title("NZ FTR Node Price Dashboard")
st.markdown("Interactive dashboard for visualizing daily spot prices for FTR nodes")

@st.cache_data
def load_and_process_data():
    """
    Dynamically downloads and merges wholesale data for specified nodes
    from 2015-01-01 to yesterday.
    """
    
    # --- 1. Define Node Codes and Base URL ---
    # These are the codes from your screenshot
    NODE_CODES = [
        "OTA2201",
        "WKM2201",
        "RDF2201",
        "SFD2201",
        "HAY2201",
        "KIK2201",
        "ISL2201",
        "BEN2201",
        "INV2201"
    ]
    BASE_URL = "https://www.emi.ea.govt.nz/Wholesale/Download/DataReport/CSV/CLA3WR"

    # --- 2. Set Dynamic Date Range ---
    start_date_str = "20150101"
    
    # Get today and subtract one day to get yesterday
    yesterday = date.today() - timedelta(days=1)
    end_date_str = yesterday.strftime("%Y%m%d")

    st.info(f"Downloading data for {len(NODE_CODES)} nodes from {start_date_str} to {end_date_str}...")

    # --- 3. Download and Process Data ---
    data_frames = []
    
    # Use a session for efficient (faster) downloads
    with requests.Session() as session:
        for node_code in NODE_CODES:
            # Set the query parameters for the URL
            params = {
                'DateFrom': start_date_str,
                'DateTo': end_date_str,
                'POC': node_code, # This is the dynamic node code
                '_rsdr': 'W1',
                '_si': 'v|3'
            }
            
            try:
                # Make the GET request to download the data
                response = session.get(BASE_URL, params=params)
                
                # Check if the download was successful
                if response.status_code == 200:
                    st.write(f"Successfully downloaded data for {node_code}...")
                    
                    # Use StringIO to treat the downloaded text (response.text)
                    # as if it were a file on disk.
                    # We skip the first 9 rows, just like in your original code.
                    csv_file_in_memory = StringIO(response.text)
                    df = pd.read_csv(csv_file_in_memory, skiprows=9)
                    
                    # Add the new DataFrame to our list
                    data_frames.append(df)
                else:
                    # Report an error if the download failed for a node
                    st.warning(f"Failed to download data for {node_code}. Status: {response.status_code}")
            
            except requests.RequestException as e:
                st.error(f"Error during download for {node_code}: {e}")

    # --- 4. Merge and Return Data ---
    if not data_frames:
        st.error("No data was successfully downloaded! Please check the network connection or URL.")
        st.stop()
    
    # Concatenate all individual DataFrames into one large DataFrame
    st.success("All data downloaded. Merging DataFrames...")
    merged_data = pd.concat(data_frames, ignore_index=True)
    
    st.success("Data processing complete!")
    return merged_data
    
    # Convert Trading date to datetime
    merged_data['Trading date'] = pd.to_datetime(merged_data['Trading date'], dayfirst=True)
    
    # Calculate daily average price for each node
    daily_avg = (
        merged_data
        .groupby(['Trading date', 'Point of connection'])['$/MWh']
        .mean()
        .reset_index()
    )
    
    return daily_avg

# Load the data
try:
    daily_avg = load_and_process_data()
    
    # Get min and max dates
    min_date = daily_avg['Trading date'].min().date()
    max_date = daily_avg['Trading date'].max().date()
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Date range selector
    start_date = st.sidebar.date_input(
        "Start Date",
        value=min_date,
        min_value=min_date,
        max_value=max_date
    )
    
    end_date = st.sidebar.date_input(
        "End Date",
        value=max_date,
        min_value=min_date,
        max_value=max_date
    )
    
    # Node selector (optional - select specific nodes)
    all_nodes = sorted(daily_avg['Point of connection'].unique())
    selected_nodes = st.sidebar.multiselect(
        "Select Nodes",
        options=all_nodes,
        default=all_nodes
    )
    
    # Filter data based on selections
    filtered_data = daily_avg[
        (daily_avg['Trading date'].dt.date >= start_date) & 
        (daily_avg['Trading date'].dt.date <= end_date) &
        (daily_avg['Point of connection'].isin(selected_nodes))
    ]
    
    # Display summary metrics
    if not filtered_data.empty:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Days", len(filtered_data['Trading date'].unique()))
        
        with col2:
            avg_price = filtered_data['$/MWh'].mean()
            st.metric("Average Price", f"${avg_price:.2f}/MWh")
        
        with col3:
            max_price = filtered_data['$/MWh'].max()
            st.metric("Max Price", f"${max_price:.2f}/MWh")
        
        # Create the plot
        fig = px.line(
            filtered_data,
            x='Trading date',
            y='$/MWh',
            color='Point of connection',
            title=f'Daily Average Spot Prices by Node ({start_date} to {end_date})',
            labels={'Trading date': 'Date', '$/MWh': 'Avg Price ($/MWh)', 'Point of connection': 'Node'}
        )
        
        fig.update_layout(
            height=500,
            hovermode='x unified'
        )
        
        # Hide date in hover tooltip
        fig.update_traces(hovertemplate='%{y:.2f} $/MWh<extra>%{fullData.name}</extra>')
        
        # Display the plot
        st.plotly_chart(fig, use_container_width=True)
        
        # Show data table (optional)
        if st.checkbox("Show Data Table"):
            st.dataframe(filtered_data, use_container_width=True)
        
        # Download button
        csv = filtered_data.to_csv(index=False)
        st.download_button(
            label="Download Filtered Data as CSV",
            data=csv,
            file_name=f"ftr_prices_{start_date}_to_{end_date}.csv",
            mime="text/csv"
        )
    else:
        st.warning("No data available for the selected date range and nodes.")

except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    st.info("Please ensure the wholesale data CSV files are in C:\\Users\\1506043\\Downloads")
