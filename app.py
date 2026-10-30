import streamlit as st
import pandas as pd

from data_loader import load_dataset
from database import initialize_database
from auth import login_user

from chat_history import (
    create_conversation,
    get_user_conversations,
    save_message,
    get_conversation_messages,
    rename_conversation,
    delete_conversation
)

from rag_engine import (
    generate_rag_answer,
    index_documents,
    get_knowledge_base_count,
)


# --------------------------------------------------
# 1. Configure the application
# --------------------------------------------------
st.set_page_config(
    page_title="EdgeSight Query Nexus",
    page_icon="🤖",
    layout="wide",
)
# Initialize database
initialize_database()

# Initialize login session
if "user" not in st.session_state:
    st.session_state.user = None

# Show login page if user is not logged in
if st.session_state.user is None:

    st.title("🤖 EdgeSight Query Nexus")
    st.subheader("Login to your account")

    with st.form("login_form"):

        username = st.text_input("Username")
        password = st.text_input(
            "Password",
            type="password"
        )

        login_button = st.form_submit_button("Login")

        if login_button:

            user = login_user(username, password)

            if user:
                st.session_state.user = user
                st.success("Login successful!")
                st.rerun()

            else:
                st.error("Invalid username or password.")

    st.stop()

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
# 3. Initialize chat session
# --------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None


# --------------------------------------------------
# 4. EdgeSight branding and sidebar
# --------------------------------------------------

user_id = st.session_state.user["user_id"]

# Custom interface styling
st.markdown("""
<style>
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2rem;
    }

    [data-testid="stSidebar"] {
        background-color: #101827;
    }

    [data-testid="stSidebar"] * {
        color: #E8EEF7;
    }

    .edge-brand {
        font-size: 25px;
        font-weight: 800;
        color: #63D6C5;
        letter-spacing: -1px;
    }

    .edge-subtitle {
        color: #A9B8CB;
        font-size: 11px;
        letter-spacing: 2px;
    }

    .edge-welcome {
        padding: 24px;
        border-radius: 18px;
        background: linear-gradient(120deg, #142B49, #176C75);
        color: white;
        margin-bottom: 20px;
    }

    .edge-welcome h2 {
        color: white;
    }

    div[data-testid="stChatMessage"] {
        border-radius: 12px;
        padding: 10px;
    }

    .stChatInput {
        border-radius: 15px;
    }
</style>
""", unsafe_allow_html=True)


# Sidebar branding
st.sidebar.markdown("""
<div style="padding: 12px 4px 20px 4px;">
    <div style="font-size:30px;">◈</div>
    <div class="edge-brand">EdgeSight</div>
    <div class="edge-subtitle">QUERY NEXUS</div>
    <p style="font-size:12px;color:#A9B8CB;">
        Intelligent IoT Operations Assistant
    </p>
</div>
""", unsafe_allow_html=True)

st.sidebar.caption(
    f"Logged in as {st.session_state.user['username']}"
)

# Logout button — only one instance
if st.sidebar.button(
    "↪ Logout",
    key=f"logout_{user_id}",
    use_container_width=True
):
    st.session_state.user = None
    st.session_state.messages = []
    st.session_state.pending_question = None
    st.session_state.current_conversation_id = None
    st.rerun()


# --------------------------------------------------
# Chat history sidebar
# --------------------------------------------------

st.sidebar.divider()
st.sidebar.subheader("💬 Your conversations")

# Only ONE New Chat button
if st.sidebar.button(
    "＋ New Chat",
    key="edgesight_new_chat",
    use_container_width=True
):
    st.session_state.current_conversation_id = None
    st.session_state.messages = []
    st.session_state.pending_question = None
    st.rerun()


# Fetch saved conversations from SQLite
conversations = get_user_conversations(user_id)

if conversations:

    for conversation in conversations:

        conversation_id = conversation["conversation_id"]
        title = conversation["title"]

        # Open a saved conversation
        if st.sidebar.button(
            f"💬 {title}",
            key=f"open_conversation_{conversation_id}",
            use_container_width=True
        ):
            st.session_state.current_conversation_id = conversation_id

            st.session_state.messages = get_conversation_messages(
                user_id,
                conversation_id
            )

            st.session_state.pending_question = None
            st.rerun()

        # Rename and delete controls
        with st.sidebar.expander(
            "⚙ Manage chat",
            expanded=False
        ):

            new_title = st.text_input(
                "Conversation title",
                value=title,
                key=f"rename_input_{conversation_id}"
            )

            if st.button(
                "Rename",
                key=f"rename_button_{conversation_id}",
                use_container_width=True
            ):
                if rename_conversation(
                    user_id,
                    conversation_id,
                    new_title
                ):
                    st.success("Conversation renamed.")
                    st.rerun()
                else:
                    st.warning("Enter a valid title (1–100 characters).")

            if st.button(
                "Delete conversation",
                key=f"delete_button_{conversation_id}",
                use_container_width=True
            ):
                delete_conversation(user_id, conversation_id)

                if st.session_state.current_conversation_id == conversation_id:
                    st.session_state.current_conversation_id = None
                    st.session_state.messages = []

                st.rerun()

else:
    st.sidebar.caption("Your conversations will appear here.")
selected_page = st.sidebar.radio(
    "choose a feature",
    [
        "Chat",
        "Knowledge Base",
        "Overview",
        "Sensor Charts",
        "Equipment Health",
        "Explore Records",
    ],
    key="selected_page",
)

# The equipment filter is only shown on dashboard pages.
if selected_page not in ["Chat", "Knowledge Base"]:
    
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
    # Chat and Knowledge Base use the complete dataset, without dashboard filters.
    filtered_df = df.copy()



# --------------------------------------------------
# 5. Chat page
# --------------------------------------------------

if selected_page == "Chat":

    st.markdown("""
    <div class="edge-welcome">
        <h2>◈ Welcome to EdgeSight Query Nexus</h2>
        <p>
            Your intelligent assistant for IoT operations,
            equipment monitoring and predictive maintenance.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Welcome suggestions
    examples = [
        "How many records are in the dataset?",
        "What is the average health score?",
        "How many recorded failures are there?",
        "How many maintenance records are due?"
    ]

    if not st.session_state.messages:

        st.subheader("What would you like to explore?")

        col1, col2 = st.columns(2)

        for index, example in enumerate(examples):

            with (col1 if index % 2 == 0 else col2):

                if st.button(
                    f"✦ {example}",
                    key=f"edge_example_{index}",
                    use_container_width=True
                ):
                    st.session_state.pending_question = example

    # Chat input
    question = st.chat_input(
        "Message EdgeSight Query Nexus..."
    )

    if question and question.strip():
        st.session_state.pending_question = question.strip()

    # Process a new question
    if st.session_state.pending_question:

        user_question = st.session_state.pending_question
        st.session_state.pending_question = None

        # Create conversation when the first message arrives
        if st.session_state.current_conversation_id is None:

            st.session_state.current_conversation_id = create_conversation(
                user_id,
                title=user_question[:40]
            )

        conversation_id = st.session_state.current_conversation_id

        # Save user message
        st.session_state.messages.append({
            "role": "user",
            "content": user_question
        })

        save_message(
            user_id,
            conversation_id,
            "user",
            user_question
        )

        # Generate AI answer
        try:

            with st.spinner("EdgeSight is analyzing your IoT data..."):

                answer = generate_rag_answer(
                    user_question,
                    df,
                    chat_history=st.session_state.messages[:-1]
                )

                if not isinstance(answer, str):
                    answer = str(answer)

        except Exception as error:

            answer = (
                "I couldn't generate a response. "
                "Please check that Ollama is running and that "
                "the required models are installed.\n\n"
                f"Technical details: {error}"
            )

        # Save assistant response
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer
        })

        save_message(
            user_id,
            conversation_id,
            "assistant",
            answer
        )

        # Refresh sidebar to show the new conversation
        st.rerun()

    # Always display conversation history
    for message in st.session_state.messages:

        if message["role"] in ["user", "assistant"]:

            with st.chat_message(message["role"]):

                st.markdown(message["content"])


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
        # --------------------------------------------------
# 10. Knowledge Base page
# --------------------------------------------------
elif selected_page == "Knowledge Base":

    st.title("📚 IoT Document Knowledge Base")

    st.write(
        "Add PDF manuals and technical documents to your "
        "EdgeSight AI assistant."
    )

    st.info(
        "Place your PDF, TXT or Markdown files inside the "
        "documents folder in your project."
    )

    document_count = get_knowledge_base_count()

    col1, col2 = st.columns(2)

    col1.metric(
        "Indexed Document Chunks",
        document_count
    )

    documents_folder = "documents"

    from pathlib import Path

    document_files = []

    for extension in ["*.pdf", "*.txt", "*.md"]:
        document_files.extend(
            Path(documents_folder).glob(extension)
        )

    col2.metric(
        "Files Available",
        len(document_files)
    )

    st.subheader("Available Documents")

    if document_files:
        for file in document_files:
            st.write(f"📄 {file.name}")
    else:
        st.warning(
            "No documents found. Add a PDF or text file "
            "to your documents folder."
        )

    st.divider()

    if st.button(
        "🔄 Index / Update Documents",
        use_container_width=True
    ):

        with st.spinner(
            "Reading documents and creating embeddings..."
        ):

            try:
                result = index_documents()

                if result["success"]:
                    st.success(result["message"])

                    st.write(
                        f"Files processed: {result['files']}"
                    )

                    st.write(
                        f"Chunks indexed: {result['chunks']}"
                    )

                    st.rerun()

                else:
                    st.warning(result["message"])

            except Exception as error:
                st.error(
                    f"Document indexing failed: {error}"
                )

    st.caption(
        "After adding or changing documents, run indexing "
        "again before asking questions about them."
    )