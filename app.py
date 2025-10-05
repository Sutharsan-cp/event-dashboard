import streamlit as st
import pandas as pd
import plotly.express as px
import io

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Registration Analysis Dashboard",
    layout="wide",
)

# --- HELPER FUNCTIONS ---
@st.cache_data
def preprocess_data(df):
    """Cleans and preprocesses the raw registration data."""
    df['Created At'] = pd.to_datetime(df['Created At'], errors='coerce', utc=True)
    df.dropna(subset=['Created At'], inplace=True)

    df['Registration Date'] = df['Created At'].dt.date
    df['Year of Study Cleaned'] = pd.to_numeric(df['Year of Study'], errors='coerce')
    df.dropna(subset=['Year of Study Cleaned'], inplace=True)
    df['Year of Study Cleaned'] = df['Year of Study Cleaned'].astype(int).astype(str)
    return df

    return df

@st.cache_data
def to_csv(df):
    """Converts a DataFrame to a CSV string for downloading."""
    return df.to_csv(index=False).encode('utf-8')

# --- MAIN APPLICATION ---
st.title("🎉 Event Registration Dashboard")
st.markdown("Upload your registration CSV for an automated, in-depth analysis.")

uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is None:
    st.info("Please upload a CSV file to get started.", icon="👈")
    st.stop()

try:
    # Read uploaded file robustly: decode bytes to UTF-8 (ignore errors),
    # normalize newlines, and let pandas parse from a StringIO buffer.
    content = uploaded_file.getvalue().decode('utf-8', errors='ignore')
    content = content.replace('\r\n', '\n')
    df_raw = pd.read_csv(io.StringIO(content), on_bad_lines='skip')
    df_raw.columns = df_raw.columns.str.replace('\ufeff', '', regex=True)
    if df_raw is None or df_raw.empty:
        st.error("The uploaded CSV file is empty or could not be read.", icon="🚨")
        st.stop()
    df = preprocess_data(df_raw.copy())
except Exception as e:
    st.error(f"⚠️ Could not read the CSV file. Try re-saving it as UTF-8 format.\n\nError details: {e}")
    st.stop()

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filter Your Data 👇")
college_list = sorted(df['College Name'].dropna().unique())
selected_colleges = st.sidebar.multiselect('Filter by College:', options=college_list, default=college_list)
year_list = sorted(df['Year of Study Cleaned'].unique())
selected_years = st.sidebar.multiselect('Filter by Year of Study:', options=year_list, default=year_list)
min_date, max_date = df['Registration Date'].min(), df['Registration Date'].max()
selected_date_range = st.sidebar.date_input('Filter by Registration Date:', value=(min_date, max_date), min_value=min_date, max_value=max_date)

start_date, end_date = selected_date_range
df_filtered = df[
    (df['College Name'].isin(selected_colleges)) &
    (df['Year of Study Cleaned'].isin(selected_years)) &
    (df['Registration Date'] >= start_date) &
    (df['Registration Date'] <= end_date)
]

if df_filtered.empty:
    st.warning("No data matches the current filter settings.")
    st.stop()

# --- DASHBOARD UI ---
st.markdown("---")
st.header("📈 Key Metrics Overview")
df_completed = df_filtered.dropna(subset=['First Name', 'College Name', 'Gender'])
kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric(label="Total Registrations (Filtered)", value=f"{len(df_filtered)}")
kpi2.metric(label="Completed Profiles", value=f"{len(df_completed)}")
kpi3.metric(label="Top College in Selection", value=df_completed['College Name'].mode()[0], delta=f"{df_completed['College Name'].value_counts().iloc[0]} Registrations")
st.markdown("---")

st.header("Detailed Analysis")
tab1, tab2, tab3, tab4 = st.tabs(["🗓️ Timeline", "🎓 Demographics", "📊 Event Analytics", "📋 Full Data"])

with tab1:
    st.subheader("Registrations Over Time")
    plot_type_timeline = st.selectbox(
        "Choose a visualization type for the timeline:",
        ("Line Chart", "Bar Chart", "Area Chart", "Data Table"),
        key='timeline_plot_selector'
    )
    daily_registrations = df_filtered.groupby('Registration Date').size().reset_index(name='Count')
    daily_registrations.rename(columns={'Registration Date': 'Date'}, inplace=True)
    if plot_type_timeline == "Line Chart":
        fig = px.line(daily_registrations, x='Date', y='Count', title='Daily Registration Volume', markers=True)
        st.plotly_chart(fig, use_container_width=True)
    elif plot_type_timeline == "Bar Chart":
        fig = px.bar(daily_registrations, x='Date', y='Count', title='Daily Registration Volume')
        st.plotly_chart(fig, use_container_width=True)
    elif plot_type_timeline == "Area Chart":
        fig = px.area(daily_registrations, x='Date', y='Count', title='Cumulative Registration Volume', markers=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.dataframe(daily_registrations)

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top 10 Colleges")
        college_counts = df_completed['College Name'].value_counts().nlargest(10).reset_index()
        college_counts.columns = ['College', 'Count']
        fig_bar_college = px.bar(college_counts, x='Count', y='College', orientation='h', title='Top Colleges')
        fig_bar_college.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar_college, use_container_width=True)
        st.subheader("Distribution by Year of Study")
        year_counts = df_filtered['Year of Study Cleaned'].value_counts().reset_index()
        year_counts.columns = ['Year', 'Count']
        fig_pie_year = px.pie(year_counts, names='Year', values='Count', title='Proportion by Year')
        st.plotly_chart(fig_pie_year, use_container_width=True)
    with col2:
        st.subheader("Gender Distribution")
        gender_counts = df_completed['Gender'].value_counts().reset_index()
        gender_counts.columns = ['Gender', 'Count']
        fig_donut_gender = px.pie(gender_counts, names='Gender', values='Count', title='Registrations by Gender', hole=0.4)
        st.plotly_chart(fig_donut_gender, use_container_width=True)
        st.subheader("Top 10 Degrees/Branches")
        degree_counts = df_completed['Degree'].value_counts().nlargest(10).reset_index()
        degree_counts.columns = ['Degree', 'Count']
        fig_bar_degree = px.bar(degree_counts, x='Count', y='Degree', orientation='h', title='Most Popular Degrees')
        fig_bar_degree.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar_degree, use_container_width=True)


with tab3:
    st.header("📊 In-Depth Event Analytics")
    events_df = df_filtered.dropna(subset=['Registered Events']).copy()
    events_df['Registered Events'] = events_df['Registered Events'].str.split(';')
    events_exploded = events_df.explode('Registered Events')
    events_exploded['Registered Events'] = events_exploded['Registered Events'].str.strip()
    
    if events_exploded.empty:
        st.warning("No event registration data found for the current filter selection.")
    else:
        with st.container(border=True):
            st.subheader("Event Popularity")
            plot_type = st.selectbox("Choose a visualization type:", ("Bar Chart", "Pie Chart", "Data Table"))
            event_counts = events_exploded['Registered Events'].value_counts().reset_index()
            event_counts.columns = ['Event', 'Registrations']
            if plot_type == "Bar Chart":
                fig = px.bar(event_counts, x='Registrations', y='Event', orientation='h')
                fig.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
            elif plot_type == "Pie Chart":
                fig = px.pie(event_counts, names='Event', values='Registrations')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.dataframe(event_counts)

        with st.container(border=True):
            st.subheader("Participants and Unique Teams per Event")

            # 1. Calculate total participants per event
            total_participants = events_exploded['Registered Events'].value_counts().reset_index()
            total_participants.columns = ['Event', 'Total Participants']

            # 2. Calculate unique teams per event
            unique_teams = events_exploded.groupby('Registered Events')['Teams'].nunique().reset_index()
            unique_teams.columns = ['Event', 'Number of Unique Teams']

            # 3. Merge the two dataframes
            event_summary_df = pd.merge(total_participants, unique_teams, on='Event', how='left')
            event_summary_df['Number of Unique Teams'] = event_summary_df['Number of Unique Teams'].fillna(0).astype(int)
            
            # Add tabs for visualization and data table
            viz_tab, data_tab = st.tabs(["📊 Charts View", "📋 Table View"])

            with viz_tab:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Chart for Total Participants
                    fig_participants = px.bar(
                        event_summary_df,
                        x='Total Participants',
                        y='Event',
                        orientation='h',
                        title='Total Participants per Event'
                    )
                    fig_participants.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_participants, use_container_width=True)
                    
                with col2:
                    # Chart for Number of Unique Teams
                    teams_only_df = event_summary_df[event_summary_df['Number of Unique Teams'] > 0]
                    fig_teams = px.bar(
                        teams_only_df,
                        x='Number of Unique Teams',
                        y='Event',
                        orientation='h',
                        title='Number of Unique Teams per Event'
                    )
                    fig_teams.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_teams, use_container_width=True)

            with data_tab:
                # Display the summary table
                st.dataframe(event_summary_df)
            
        with st.container(border=True):
            st.subheader("Drill-Down: College Interest by Event")
            event_list = sorted(events_exploded['Registered Events'].unique())
            selected_event = st.selectbox("Select an event to see college registrations:", event_list)
            if selected_event:
                event_specific_df = events_exploded[events_exploded['Registered Events'] == selected_event]
                college_interest = event_specific_df['College Name'].value_counts().nlargest(10).reset_index()
                college_interest.columns = ['College', 'Registrations']
                fig = px.bar(college_interest, x='Registrations', y='College', orientation='h', title=f"Top 10 Colleges Registering for {selected_event}")
                fig.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("Browse and Export Full Data")
    st.dataframe(df_filtered)
    csv = to_csv(df_filtered)
    st.download_button(
        label="📥 Download Filtered Data as CSV",
        data=csv,
        file_name='filtered_registrations.csv',
        mime='text/csv',
    )
    