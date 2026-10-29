import streamlit as st
import pandas as pd

from data_loader import load_dataset
from ollama_chat import generate_ai_answer


# --------------------------------------------------
# 1. Configure the application
# --------------------------------------------------
st.set_page_config(
    page_title="EdgeSight Query Nexus",
    page_icon="🤖",
    layout="wide",
)


# --------------------------------------------------
# 2. Load the dataset
# --------------------------------------------------
@st.cache_data
def get_data():
    return load_dataset()


try:
    df = get_data()
except Exception as error:
    st.error(f"Could not load the dataset: {error}")
    st.info(
        "Check that data/iot_operations_01.csv exists "
        "and that data_loader.py works correctly."
    )
    st.stop()


if df.empty:
    st.warning("The dataset is empty. Please check your CSV file.")


# --------------------------------------------------
# 3. Initialize chat history
# --------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None


# --------------------------------------------------
# 4. Sidebar navigation
# --------------------------------------------------
st.sidebar.title("🤖 EdgeSight")
st.sidebar.caption("IoT Operations Assistant")

selected_page = st.sidebar.radio(
    "Choose a feature",
    [
        "Chat",
        "Overview",
        "Sensor Charts",
        "Equipment Health",
        "Explore Records",
    ],
    key="selected_page",
)

# The equipment filter is only shown on dashboard pages.
if selected_page != "Chat":
    st.sidebar.divider()
    st.sidebar.subheader("Dashboard Filters")

    if "asset_type" in df.columns:
        asset_types = sorted(
            df["asset_type"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        selected_type = st.sidebar.selectbox(
            "Equipment type",
            ["All equipment types"] + asset_types,
        )

        if selected_type == "All equipment types":
            filtered_df = df.copy()
        else:
            filtered_df = df[
                df["asset_type"].astype(str) == selected_type
            ].copy()

        st.sidebar.caption(
            f"Matching records: {len(filtered_df):,}"
        )
    else:
        filtered_df = df.copy()
        st.sidebar.info(
            "The dataset does not contain an asset_type column."
        )
else:
    # Chat uses the complete dataset, without dashboard filters.
    filtered_df = df.copy()


# --------------------------------------------------
# 5. Chat page
# --------------------------------------------------
if selected_page == "Chat":

    st.title("🤖 EdgeSight Query Nexus")
    st.caption(
        "Your AI assistant for IoT equipment, sensor readings, "
        "failures, maintenance, and equipment health."
    )

    st.divider()

    # Quick-action questions
    examples = [
        "How many records are in the dataset?",
        "What is the average health score?",
        "How many recorded failures are there?",
        "How many maintenance records are due?",
    ]

    # Show quick actions when the conversation is empty.
    if not st.session_state.messages:
        st.subheader("What would you like to know?")

        example_columns = st.columns(2)

        for index, example in enumerate(examples):
            with example_columns[index % 2]:
                if st.button(
                    example,
                    key=f"chat_example_{index}",
                    use_container_width=True,
                ):
                    st.session_state.pending_question = example

    # Read the question submitted in the chat box.
    question = st.chat_input(
        "Ask a question about your IoT dataset..."
    )

    if question and question.strip():
        st.session_state.pending_question = question.strip()

    # Process a new question before displaying messages.
    if st.session_state.pending_question:
        user_question = st.session_state.pending_question
        st.session_state.pending_question = None

        st.session_state.messages.append(
            {
                "role": "user",
                "content": user_question,
            }
        )

        try:
            answer = generate_ai_answer(
                user_question,
                df,
                chat_history=st.session_state.messages[:-1],
            )

            if not isinstance(answer, str):
                answer = str(answer)

        except Exception as error:
            answer = (
                "I couldn't generate an answer from Ollama.\n\n"
                "Please check that Ollama is running and that "
                "your configured model is installed.\n\n"
                f"Technical details: {error}"
            )

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
            }
        )

    # Display only the conversation on the Chat page.
    if st.session_state.messages:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    else:
        st.info(
            "Choose a quick question above or type your own "
            "question in the message box."
        )


# --------------------------------------------------
# 6. Overview page
# --------------------------------------------------
elif selected_page == "Overview":

    st.title("📊 IoT Operations Dashboard")
    st.caption(
        "A summary of the equipment records in your selected filter."
    )

    total_records = len(filtered_df)

    if "asset_id" in filtered_df.columns:
        unique_assets = filtered_df["asset_id"].nunique()
    else:
        unique_assets = 0

    if "ai_health_index_score" in filtered_df.columns:
        health_scores = pd.to_numeric(
            filtered_df["ai_health_index_score"],
            errors="coerce",
        )

        if health_scores.notna().any():
            average_health = f"{health_scores.mean():.2f}"
        else:
            average_health = "No data"
    else:
        average_health = "Column unavailable"

    col1, col2, col3 = st.columns(3)

    col1.metric("Matching Records", f"{total_records:,}")
    col2.metric("Unique Assets", f"{unique_assets:,}")
    col3.metric("Average Health Score", average_health)

    st.divider()

    # Records by equipment type
    st.subheader("Records by Equipment Type")

    if "asset_type" in filtered_df.columns:
        if not filtered_df.empty:
            type_counts = filtered_df["asset_type"].value_counts()
            st.bar_chart(type_counts)
        else:
            st.info("No records match the selected filter.")
    else:
        st.warning(
            "The dataset does not contain an asset_type column."
        )

    # Dataset source and coverage
    with st.expander("Dataset Source and Coverage"):
        st.write("**Source file:** `data/iot_operations_01.csv`")
        st.write(f"**Total rows in dataset:** {len(df):,}")
        st.write(f"**Total columns:** {len(df.columns)}")

        st.write("**Available columns:**")
        st.code(", ".join(df.columns.astype(str)))

        if "observation_date" in df.columns:
            dates = pd.to_datetime(
                df["observation_date"],
                errors="coerce",
            ).dropna()

            if not dates.empty:
                st.write(
                    f"**Earliest observation:** {dates.min().date()}"
                )
                st.write(
                    f"**Latest observation:** {dates.max().date()}"
                )
            else:
                st.info("No valid observation dates were found.")


# --------------------------------------------------
# 7. Sensor Charts page
# --------------------------------------------------
elif selected_page == "Sensor Charts":

    st.title("🌡️ Sensor Readings Over Time")
    st.write(
        "Explore bearing temperature and vibration readings "
        "for the selected equipment."
    )

    sensor_columns = [
        "observation_date",
        "bearing_temp_c",
        "vibration_rms_mm_s",
    ]

    missing_sensor_columns = [
        column
        for column in sensor_columns
        if column not in filtered_df.columns
    ]

    if missing_sensor_columns:
        st.warning(
            "Sensor charts cannot be displayed. Missing columns: "
            + ", ".join(missing_sensor_columns)
        )

    elif filtered_df.empty:
        st.info("No records match the selected equipment filter.")

    else:
        sensor_df = filtered_df[sensor_columns].copy()

        sensor_df["observation_date"] = pd.to_datetime(
            sensor_df["observation_date"],
            errors="coerce",
        )

        sensor_df["bearing_temp_c"] = pd.to_numeric(
            sensor_df["bearing_temp_c"],
            errors="coerce",
        )

        sensor_df["vibration_rms_mm_s"] = pd.to_numeric(
            sensor_df["vibration_rms_mm_s"],
            errors="coerce",
        )

        temperature_col, vibration_col = st.columns(2)

        # Temperature chart
        with temperature_col:
            st.subheader("Bearing Temperature")

            temperature_data = sensor_df.dropna(
                subset=["observation_date", "bearing_temp_c"]
            )

            if not temperature_data.empty:
                temperature_chart = (
                    temperature_data
                    .groupby("observation_date")["bearing_temp_c"]
                    .mean()
                    .sort_index()
                )

                st.line_chart(
                    temperature_chart,
                    y_label="Temperature (°C)",
                )

                st.metric(
                    "Average Temperature",
                    f"{temperature_data['bearing_temp_c'].mean():.2f} °C",
                )
            else:
                st.info(
                    "No valid temperature readings with dates found."
                )

        # Vibration chart
        with vibration_col:
            st.subheader("Vibration Level")

            vibration_data = sensor_df.dropna(
                subset=["observation_date", "vibration_rms_mm_s"]
            )

            if not vibration_data.empty:
                vibration_chart = (
                    vibration_data
                    .groupby("observation_date")["vibration_rms_mm_s"]
                    .mean()
                    .sort_index()
                )

                st.line_chart(
                    vibration_chart,
                    y_label="Vibration (mm/s RMS)",
                )

                st.metric(
                    "Average Vibration",
                    f"{vibration_data['vibration_rms_mm_s'].mean():.2f} mm/s",
                )
            else:
                st.info(
                    "No valid vibration readings with dates found."
                )


# --------------------------------------------------
# 8. Equipment Health page
# --------------------------------------------------
elif selected_page == "Equipment Health":

    st.title("🔎 Detailed Equipment Health")
    st.write(
        "Review the latest available observation for each asset, "
        "including sensor readings, failures, and maintenance."
    )

    health_columns = [
        "asset_id",
        "observation_date",
        "asset_type",
        "ai_health_index_score",
        "bearing_temp_c",
        "vibration_rms_mm_s",
        "num_sensor_alerts_last_7d",
        "prior_failures_last_12m",
        "scheduled_pm_due_within_7d",
        "unscheduled_failure_within_7d",
    ]

    available_health_columns = [
        column
        for column in health_columns
        if column in filtered_df.columns
    ]

    if "asset_id" not in filtered_df.columns:
        st.warning(
            "The equipment health table requires an asset_id column."
        )

    elif filtered_df.empty:
        st.info("No equipment records match the selected filter.")

    else:
        health_df = filtered_df[available_health_columns].copy()

        if "observation_date" in health_df.columns:
            health_df["observation_date"] = pd.to_datetime(
                health_df["observation_date"],
                errors="coerce",
            )

            health_df = health_df.sort_values(
                "observation_date",
                na_position="first",
            )

            # Keep the latest available observation for each asset.
            health_df = health_df.drop_duplicates(
                subset=["asset_id"],
                keep="last",
            )

        numeric_columns = [
            "ai_health_index_score",
            "bearing_temp_c",
            "vibration_rms_mm_s",
            "num_sensor_alerts_last_7d",
            "prior_failures_last_12m",
        ]

        for column in numeric_columns:
            if column in health_df.columns:
                health_df[column] = pd.to_numeric(
                    health_df[column],
                    errors="coerce",
                )

        column_names = {
            "asset_id": "Asset ID",
            "observation_date": "Observation Date",
            "asset_type": "Equipment Type",
            "ai_health_index_score": "Health Score",
            "bearing_temp_c": "Bearing Temperature (°C)",
            "vibration_rms_mm_s": "Vibration (mm/s RMS)",
            "num_sensor_alerts_last_7d": "Sensor Alerts (7 Days)",
            "prior_failures_last_12m": "Previous Failures (12 Months)",
            "scheduled_pm_due_within_7d": "Maintenance Due (7 Days)",
            "unscheduled_failure_within_7d": "Unscheduled Failure (7 Days)",
        }

        health_df = health_df.rename(columns=column_names)

        asset_search = st.text_input(
            "Search by Asset ID",
            placeholder="Enter an asset ID...",
            key="health_asset_search",
        )

        if asset_search.strip():
            health_df = health_df[
                health_df["Asset ID"]
                .astype(str)
                .str.contains(
                    asset_search.strip(),
                    case=False,
                    na=False,
                    regex=False,
                )
            ]

        st.write(f"**Assets displayed:** {len(health_df):,}")

        if health_df.empty:
            st.info("No assets match your search.")
        else:
            st.dataframe(
                health_df,
                use_container_width=True,
                hide_index=True,
            )

            csv_data = health_df.to_csv(index=False).encode("utf-8")

            st.download_button(
                label="Download Equipment Health Table (CSV)",
                data=csv_data,
                file_name="equipment_health_report.csv",
                mime="text/csv",
            )


# --------------------------------------------------
# 9. Explore Records page
# --------------------------------------------------
elif selected_page == "Explore Records":

    st.title("🗂️ Explore Records")
    st.write(
        "Inspect the IoT dataset and download the records "
        "that match your equipment filter."
    )

    if filtered_df.empty:
        st.info("There are no records to display.")

    else:
        st.write(f"**Matching records:** {len(filtered_df):,}")

        st.dataframe(
            filtered_df.head(100),
            use_container_width=True,
            hide_index=True,
        )

        st.caption("Showing up to 100 matching records.")

        csv_data = filtered_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Filtered Records (CSV)",
            data=csv_data,
            file_name="iot_filtered_records.csv",
            mime="text/csv",
        )