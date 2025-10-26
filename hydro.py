import os
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
import requests
from io import StringIO

# Page configuration
st.set_page_config(page_title="NZ Lake Storage Dashboard", layout="wide")

# Title
st.title("NZ Lake Storage Dashboard")
st.markdown("Interactive dashboard for visualizing lake storage levels across New Zealand hydro lakes")

@st.cache_data
def load_and_process_data():
    """
    Downloads and merges lake storage data from EMI website
    """
    
    # --- 1. Define Lake Storage URLs ---
    LAKE_URLS = {
        "Lake Taupo": "https://www.emi.ea.govt.nz/Environment/Datasets/HydrologicalModellingDataset/3_StorageAndSpill_20231231/3.1_Storage/NI_TPO_Storage_LakeTaupo.csv",
        "Lake Waikaremoana": "https://www.emi.ea.govt.nz/Environment/Datasets/HydrologicalModellingDataset/3_StorageAndSpill_20231231/3.1_Storage/NI_WKA_Storage_LakeWaikaremoana.csv",
        "Lake Hawea": "https://www.emi.ea.govt.nz/Environment/Datasets/HydrologicalModellingDataset/3_StorageAndSpill_20231231/3.1_Storage/SI_HWE_Storage_LakeHawea.csv",
        "Lake Manapouri": "https://www.emi.ea.govt.nz/Environment/Datasets/HydrologicalModellingDataset/3_StorageAndSpill_20231231/3.1_Storage/SI_MAN_Storage_LakeManapouri.csv",
        "Lake Ohau": "https://www.emi.ea.govt.nz/Environment/Datasets/HydrologicalModellingDataset/3_StorageAndSpill_20231231/3.1_Storage/SI_OHA_Storage_LakeOhau.csv",
        "Lake Pukaki": "https://www.emi.ea.govt.nz/Environment/Datasets/HydrologicalModellingDataset/3_StorageAndSpill_20231231/3.1_Storage/SI_PKI_Storage_LakePukaki.csv",
        "Lake Te Anau": "https://www.emi.ea.govt.nz/Environment/Datasets/HydrologicalModellingDataset/3_StorageAndSpill_20231231/3.1_Storage/SI_TAU_Storage_LakeTeAnau.csv",
        "Lake Tekapo": "https://www.emi.ea.govt.nz/Environment/Datasets/HydrologicalModellingDataset/3_StorageAndSpill_20231231/3.1_Storage/SI_TKA_Storage_LakeTekapo.csv",
        "Lake Wanaka": "https://www.emi.ea.govt.nz/Environment/Datasets/HydrologicalModellingDataset/3_StorageAndSpill_20231231/3.1_Storage/SI_WAN_Storage_LakeWanaka.csv",
        "Lake Wakatipu": "https://www.emi.ea.govt.nz/Environment/Datasets/HydrologicalModellingDataset/3_StorageAndSpill_20231231/3.1_Storage/SI_WPU_Storage_LakeWakatipu.csv"
    }

    st.info(f"Downloading storage data for {len(LAKE_URLS)} lakes...")

    # --- 2. Download and Process Data ---
    data_frames = []
    
    # Use a session for efficient downloads
    with requests.Session() as session:
        for lake_name, url in LAKE_URLS.items():
            try:
                st.write(f"Downloading data for {lake_name}...")
                
                # Make the GET request to download the data
                response = session.get(url)
                
                # Check if the download was successful
                if response.status_code == 200:
                    st.write(f"✅ Successfully downloaded data for {lake_name}")
                    
                    # Show first few lines of the response to debug
                    lines = response.text.split('\n')[:10]
                    st.write(f"First few lines from {lake_name}:")
                    for i, line in enumerate(lines):
                        st.write(f"Line {i}: {line}")
                    
                    # Use StringIO to treat the downloaded text as a file
                    csv_file_in_memory = StringIO(response.text)
                    df = pd.read_csv(csv_file_in_memory)
                    
                    st.write(f"Shape of data from {lake_name}: {df.shape}")
                    st.write(f"Columns: {df.columns.tolist()}")
                    
                    # Add lake name column for identification
                    df['Lake'] = lake_name
                    
                    # Add the DataFrame to our list
                    data_frames.append(df)
                else:
                    st.warning(f"❌ Failed to download data for {lake_name}. Status: {response.status_code}")
            
            except requests.RequestException as e:
                st.error(f"Error downloading {lake_name}: {e}")

    # --- 3. Merge and Process Data ---
    if not data_frames:
        st.error("No data was successfully downloaded! Please check the network connection.")
        st.stop()
    
    # Concatenate all DataFrames
    st.success("All data downloaded. Merging DataFrames...")
    merged_data = pd.concat(data_frames, ignore_index=True)
    
    # Process the data based on the known CSV format
    st.write("Data columns found:", merged_data.columns.tolist())
    
    # The CSV format has these specific columns:
    # Date, Time, Lake level (m), Active storage (Mm³), Active contingent storage (Mm³), QualityCode
    
    # Check if we have the expected columns (using the actual column names from the CSV)
    expected_cols = ['Date', 'Time', 'Lake level (m)', 'Active storage (Mm³)']
    missing_cols = [col for col in expected_cols if col not in merged_data.columns]
    
    if missing_cols:
        st.error(f"Missing expected columns: {missing_cols}")
        st.write("Available columns:", merged_data.columns.tolist())
        st.write("Sample data:")
        st.dataframe(merged_data.head())
        st.stop()
    
    # Combine Date and Time into a single datetime column
    # Let's first check the format of the date/time data
    st.write("Sample date/time data:")
    st.write("Date samples:", merged_data['Date'].head().tolist())
    st.write("Time samples:", merged_data['Time'].head().tolist())
    
    # Try different date formats
    merged_data['DateTime'] = pd.to_datetime(
        merged_data['Date'] + ' ' + merged_data['Time'], 
        errors='coerce'
    )
    
    # Check how many valid dates we got
    valid_dates = merged_data['DateTime'].notna().sum()
    st.write(f"Valid dates after parsing: {valid_dates} out of {len(merged_data)}")
    
    if valid_dates == 0:
        # Try alternative date formats
        st.warning("Standard date parsing failed, trying alternative formats...")
        
        # Try format without time first
        merged_data['DateTime'] = pd.to_datetime(merged_data['Date'], errors='coerce')
        valid_dates = merged_data['DateTime'].notna().sum()
        st.write(f"Valid dates with date-only parsing: {valid_dates}")
        
        if valid_dates == 0:
            # Try dd/mm/yyyy format specifically
            merged_data['DateTime'] = pd.to_datetime(
                merged_data['Date'], 
                format='%d/%m/%Y',
                errors='coerce'
            )
            valid_dates = merged_data['DateTime'].notna().sum()
            st.write(f"Valid dates with dd/mm/yyyy format: {valid_dates}")
    
    # Remove rows with invalid dates
    before_count = len(merged_data)
    merged_data = merged_data.dropna(subset=['DateTime'])
    after_count = len(merged_data)
    st.write(f"Records after removing invalid dates: {after_count} (removed {before_count - after_count})")
    
    if len(merged_data) == 0:
        st.error("No valid dates found! Please check the date format in the CSV files.")
        st.write("Sample of original data:")
        st.dataframe(merged_data.head(10))
        st.stop()
    
    # Clean up the Active storage column (using the correct column name)
    merged_data['Active storage (Mm³)'] = pd.to_numeric(
        merged_data['Active storage (Mm³)'], 
        errors='coerce'
    )
    
    # Remove rows with invalid storage values
    merged_data = merged_data.dropna(subset=['Active storage (Mm³)'])
    
    # Create final dataset with renamed columns for easier use
    final_data = merged_data[['DateTime', 'Active storage (Mm³)', 'Lake level (m)', 'Lake']].copy()
    final_data = final_data.rename(columns={
        'DateTime': 'Date',
        'Active storage (Mm³)': 'Storage',
        'Lake level (m)': 'Lake_Level'
    })
    
    st.success("Data processing complete!")
    st.write(f"Processed {len(final_data)} records across {final_data['Lake'].nunique()} lakes")
    return final_data

# Load the data
try:
    lake_data = load_and_process_data()
    
    # Check if we have any data
    if lake_data is None or len(lake_data) == 0:
        st.error("No data was successfully processed!")
        st.stop()
    
    # Get min and max dates
    min_date = lake_data['Date'].min().date()
    max_date = lake_data['Date'].max().date()
    
    st.success(f"Successfully loaded data from {min_date} to {max_date}")
    
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
    
    # Lake selector
    all_lakes = sorted(lake_data['Lake'].unique())
    selected_lakes = st.sidebar.multiselect(
        "Select Lakes",
        options=all_lakes,
        default=all_lakes
    )
    
    # Filter data based on selections
    filtered_data = lake_data[
        (lake_data['Date'].dt.date >= start_date) & 
        (lake_data['Date'].dt.date <= end_date) &
        (lake_data['Lake'].isin(selected_lakes))
    ]
    
    # Display summary metrics
    if not filtered_data.empty:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Days", len(filtered_data['Date'].unique()))
        
        with col2:
            avg_storage = filtered_data['Storage'].mean()
            st.metric("Average Storage", f"{avg_storage:.1f} MmÂ³")
        
        with col3:
            avg_level = filtered_data['Lake_Level'].mean()
            st.metric("Average Level", f"{avg_level:.2f} m")
        
        # Create the main storage plot
        fig = px.line(
            filtered_data,
            x='Date',
            y='Storage',
            color='Lake',
            title=f'Lake Storage Levels ({start_date} to {end_date})',
            labels={'Date': 'Date', 'Storage': 'Active Storage (Mm³)', 'Lake': 'Lake'}
        )
        
        fig.update_layout(
            height=600,
            hovermode='x unified'
        )
        
        # Display the plot
        st.plotly_chart(fig, use_container_width=True)
        
        # Create a second plot for lake levels
        st.subheader("Lake Water Levels")
        
        fig_level = px.line(
            filtered_data,
            x='Date',
            y='Lake_Level',
            color='Lake',
            title=f'Lake Water Levels ({start_date} to {end_date})',
            labels={'Date': 'Date', 'Lake_Level': 'Water Level (m)', 'Lake': 'Lake'}
        )
        
        fig_level.update_layout(
            height=500,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_level, use_container_width=True)
        
        # Create a comparison chart showing current vs historical levels
        st.subheader("Storage Level Comparison")
        
        # Calculate some statistics for each lake
        lake_stats = filtered_data.groupby('Lake')['Storage'].agg(['mean', 'min', 'max', 'last']).reset_index()
        lake_stats.columns = ['Lake', 'Average', 'Minimum', 'Maximum', 'Latest']
        
        # Create a bar chart for comparison
        fig_comparison = px.bar(
            lake_stats,
            x='Lake',
            y=['Average', 'Latest'],
            title='Average vs Latest Storage Levels by Lake',
            barmode='group'
        )
        
        fig_comparison.update_layout(height=400)
        st.plotly_chart(fig_comparison, use_container_width=True)
        
        # Show data table (optional)
        if st.checkbox("Show Data Table"):
            st.dataframe(filtered_data, use_container_width=True)
        
        # Show statistics table
        if st.checkbox("Show Lake Statistics"):
            st.dataframe(lake_stats, use_container_width=True)
        
        # Download button
        csv = filtered_data.to_csv(index=False)
        st.download_button(
            label="Download Filtered Data as CSV",
            data=csv,
            file_name=f"lake_storage_{start_date}_to_{end_date}.csv",
            mime="text/csv"
        )
    else:
        st.warning("No data available for the selected date range and lakes.")

except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    st.info("Please check your internet connection and try again.")
