import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import re

# Set page configuration
st.set_page_config(
    page_title="EMI Futures Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 0.25rem solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# Import embedded data
try:
    from embedded_data import EMBEDDED_DATA
    DATA_AVAILABLE = True
except ImportError:
    st.error("⚠️ Embedded data not found. Please run the scraper notebook first to generate embedded_data.py")
    st.stop()

@st.cache_data
def parse_date_utc(date_str):
    """Parse Date.UTC string to datetime"""
    if date_str is None or pd.isna(date_str):
        return None
    match = re.search(r'Date\.UTC\((\d+),(\d+),(\d+)\)', str(date_str))
    if match:
        year, month, day = map(int, match.groups())
        try:
            return datetime(year, month + 1, day)
        except ValueError:
            return None
    return None

@st.cache_data
def process_series_data(series_data):
    """Convert series data to DataFrame"""
    df_list = []
    for series in series_data:
        name = series['name']
        data_points = series['data']
        df = pd.DataFrame(data_points, columns=['timestamp', 'price'])
        df['contract'] = name
        df['date'] = df['timestamp'].apply(parse_date_utc)
        df = df.dropna(subset=['date', 'price'])
        df_list.append(df)
    
    if df_list:
        return pd.concat(df_list, ignore_index=True)
    return pd.DataFrame()

def create_price_chart(df, selected_contracts, date_range):
    """Create interactive price chart"""
    fig = go.Figure()
    
    # Filter data
    filtered_df = df[df['contract'].isin(selected_contracts)].copy()
    
    if date_range and len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[
            (filtered_df['date'] >= pd.Timestamp(start_date)) &
            (filtered_df['date'] <= pd.Timestamp(end_date))
        ]
    
    # Color palette
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    # Add traces for each contract
    for i, contract in enumerate(selected_contracts):
        contract_data = filtered_df[filtered_df['contract'] == contract].sort_values('date')
        if not contract_data.empty:
            color = colors[i % len(colors)]
            fig.add_trace(go.Scatter(
                x=contract_data['date'],
                y=contract_data['price'],
                mode='lines+markers',
                name=contract,
                line=dict(color=color, width=2),
                marker=dict(size=4, color=color),
                hovertemplate='<b>%{fullData.name}</b><br>' +
                             'Date: %{x|%Y-%m-%d}<br>' +
                             'Price: $%{y:.2f}/MWh<extra></extra>'
            ))
    
    fig.update_layout(
        title=dict(
            text="Futures Price Trends",
            x=0.5,
            font=dict(size=20, color='#1f77b4')
        ),
        xaxis=dict(
            title="Date",
            gridcolor='#e0e0e0',
            showgrid=True
        ),
        yaxis=dict(
            title="Price ($/MWh)",
            gridcolor='#e0e0e0',
            showgrid=True
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=600
    )
    
    return fig

def main():
    st.markdown('<h1 class="main-header">📊 EMI Futures Dashboard</h1>', unsafe_allow_html=True)
    st.markdown("**Interactive visualization of New Zealand Electricity Futures Market data**")
    
    # Sidebar controls
    st.sidebar.markdown("### 🎛️ Controls")
    
    # Location and Duration selection
    col1, col2 = st.sidebar.columns(2)
    with col1:
        location = st.selectbox(
            "Location",
            ["BEN", "OTA"],
            help="BEN = Benmore, OTA = Otahuhu",
            key="location_select"
        )
    with col2:
        duration = st.selectbox(
            "Duration",
            ["QTR", "MON"],
            help="QTR = Quarterly, MON = Monthly",
            key="duration_select"
        )
    
    # Load and process data
    key = f"{location}_{duration}"
    
    if key not in EMBEDDED_DATA:
        st.error(f"No data available for {location} {duration}")
        return
    
    with st.spinner('Loading data...'):
        data = EMBEDDED_DATA[key]
        df = process_series_data(data['series'])
    
    if df.empty:
        st.error("No valid data to display")
        return
    
    # Get available contracts and categorize them
    available_contracts = sorted(df['contract'].unique())
    
    # Determine active vs historic contracts (active = traded in last 6 months)
    recent_threshold = pd.Timestamp.now() - pd.Timedelta(days=180)
    
    active_contracts = []
    historic_contracts = []
    
    for contract in available_contracts:
        contract_data = df[df['contract'] == contract]
        latest_date = contract_data['date'].max()
        
        if latest_date >= recent_threshold:
            active_contracts.append(contract)
        else:
            historic_contracts.append(contract)
    
    # Contract selection
    st.sidebar.markdown("### 📅 Contract Selection")
    
    # Filter type selection
    contract_type = st.sidebar.radio(
        "Contract Type",
        ["Active Contracts", "Historic Contracts", "All Contracts"],
        index=0,
        help="**Active:** Contracts with data in the last 6 months\n\n**Historic:** Expired contracts with older data",
        key="contract_type"
    )
    
    # Show counts
    st.sidebar.info(f"""
    **Active contracts:** {len(active_contracts)} (recent data)  
    **Historic contracts:** {len(historic_contracts)} (expired)  
    **Total:** {len(available_contracts)}
    """)
    
    # Determine which contracts to show based on filter
    if contract_type == "Active Contracts":
        filtered_contracts = active_contracts
        default_contracts = active_contracts[:min(8, len(active_contracts))]
    elif contract_type == "Historic Contracts":
        filtered_contracts = historic_contracts
        default_contracts = historic_contracts[:min(8, len(historic_contracts))]
    else:  # All Contracts
        filtered_contracts = available_contracts
        default_contracts = active_contracts[:min(8, len(active_contracts))] if active_contracts else available_contracts[:8]
    
    # Select all checkbox
    select_all = st.sidebar.checkbox(
        f"Select All {contract_type}", 
        value=False, 
        key="select_all"
    )
    
    if select_all:
        selected_contracts = filtered_contracts
    else:
        selected_contracts = st.sidebar.multiselect(
            "Choose Contracts",
            filtered_contracts,
            default=default_contracts,
            help="💡 Select contracts to display on the chart",
            key="contract_multiselect"
        )
    
    # Date range filter
    st.sidebar.markdown("### 📆 Date Range")
    min_date = df['date'].min().date()
    max_date = df['date'].max().date()
    
    date_range = st.sidebar.date_input(
        "Filter by date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        help="Filter data by date range",
        key="date_range_input"
    )
    
    # Display data info in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Data Info")
    st.sidebar.info(f"""
    **Data Range:**  
    {min_date} to {max_date}
    
    **Total Contracts:** {len(available_contracts)}  
    **Total Data Points:** {len(df):,}
    """)
    
    # Main content - Metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "📋 Available Contracts",
            len(available_contracts),
            help="Number of available contract series"
        )
    
    with col2:
        latest_prices = df.groupby('contract')['price'].last().dropna()
        avg_price = latest_prices.mean() if not latest_prices.empty else 0
        st.metric(
            "💰 Avg Latest Price",
            f"${avg_price:.2f}",
            help="Average price of the most recent data points"
        )
    
    with col3:
        if selected_contracts and len(selected_contracts) > 0:
            selected_df = df[df['contract'].isin(selected_contracts)]
            data_points = len(selected_df)
        else:
            data_points = len(df)
        st.metric(
            "📈 Selected Data Points",
            f"{data_points:,}",
            help="Number of data points for selected contracts"
        )
    
    # Chart
    st.markdown("---")
    
    # Dynamic title based on contract type
    if contract_type == "Active Contracts":
        chart_subtitle = "🟢 Showing Active Contracts (Recent Trading Data)"
    elif contract_type == "Historic Contracts":
        chart_subtitle = "🔵 Showing Historic Contracts (Expired)"
    else:
        chart_subtitle = "📊 Showing All Contracts"
    
    st.markdown(f"### 📈 Price Trends")
    st.caption(chart_subtitle)
    
    if selected_contracts:
        with st.spinner('Creating chart...'):
            fig = create_price_chart(df, selected_contracts, date_range)
            st.plotly_chart(fig, use_container_width=True)
        
        # Data table
        st.markdown("### 📋 Data Table")
        
        # Add note about data ranges
        if contract_type == "Active Contracts":
            st.caption("💡 Active contracts show recent trading data (last 6 months)")
        elif contract_type == "Historic Contracts":
            st.caption("💡 Historic contracts show data from when they were actively traded")
        
        with st.expander("🔍 View Raw Data"):
            # Filter data for table
            table_df = df[df['contract'].isin(selected_contracts)].copy()
            
            if date_range and len(date_range) == 2:
                start_date, end_date = date_range
                table_df = table_df[
                    (table_df['date'] >= pd.Timestamp(start_date)) &
                    (table_df['date'] <= pd.Timestamp(end_date))
                ]
            
            # Pivot for better viewing
            if not table_df.empty:
                pivot_df = table_df.pivot_table(
                    index='date', 
                    columns='contract', 
                    values='price',
                    aggfunc='first'
                )
                pivot_df = pivot_df.sort_index(ascending=False)  # Most recent first
                
                st.dataframe(
                    pivot_df.head(100).style.format("${:.2f}"),
                    use_container_width=True
                )
                
                # Download button
                csv = pivot_df.to_csv()
                st.download_button(
                    label="📥 Download Data as CSV",
                    data=csv,
                    file_name=f"emi_futures_{location}_{duration}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No data available for the selected filters")
    else:
        st.warning("⚠️ Please select at least one contract to display the chart.")
    
    # Footer
    st.markdown("---")
    st.caption(f"""
    **Data Source:** [EMI - Electricity Authority NZ](https://www.emi.ea.govt.nz)  
    **Location:** {location} | **Duration:** {duration}  
    **Last Updated:** {max_date} | **Dashboard Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """)

if __name__ == "__main__":
    main()
