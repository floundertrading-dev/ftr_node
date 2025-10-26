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

# Data processing and loading
@st.cache_data
def load_and_process_data():
    """
    Load individual wholesale data files and merge them into a single dataset
    """
    # Directory containing the files
    directory = r"C:\Users\1506043\Downloads"
    
    # List of data files to process
    highlighted_files = [
        "Wholesale_data_for_a_single_node_20251026012058.csv",
        "Wholesale_data_for_a_single_node_20251026012003.csv",
        "Wholesale_data_for_a_single_node_20251026011653.csv",
        "Wholesale_data_for_a_single_node_20251026011358.csv",
        "Wholesale_data_for_a_single_node_20251026011258.csv",
        "Wholesale_data_for_a_single_node_20251026011131.csv",
        "Wholesale_data_for_a_single_node_20251026011055.csv",
        "Wholesale_data_for_a_single_node_20251026011001.csv"
    ]
    
    # Check if merged file already exists
    merged_file_path = os.path.join(directory, "merged_highlighted_wholesale_data.csv")
    
    if os.path.exists(merged_file_path):
        # Load existing merged file
        st.info(f"Loading cached data from: {merged_file_path}")
        merged_data = pd.read_csv(merged_file_path)
    else:
        # Process and merge individual files
        st.info("Processing individual wholesale data files...")
        data_frames = []
        
        for file_name in highlighted_files:
            file_path = os.path.join(directory, file_name)
            if os.path.exists(file_path):
                # Skip first 9 rows (metadata), row 9 contains the column headers
                df = pd.read_csv(file_path, skiprows=9)
                data_frames.append(df)
            else:
                st.warning(f"File not found: {file_name}")
        
        if not data_frames:
            st.error("No data files found! Please check the file paths.")
            st.stop()
        
        # Concatenate all DataFrames
        merged_data = pd.concat(data_frames, ignore_index=True)
        
        # Save merged data for future use
        merged_data.to_csv(merged_file_path, index=False)
        st.success(f"Merged data saved to: {merged_file_path}")
    
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
