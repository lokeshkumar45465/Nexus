"""EdgeSight Query Nexus Streamlit application.

Authentication is deliberately bypassed while the interface is being designed.
Restore the authentication flow before deploying this application beyond a local,
trusted development environment.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from chat_history import (
    create_conversation,
    delete_conversation,
    get_conversation_messages,
    get_user_conversations,
    rename_conversation,
    save_message,
)
from data_loader import load_dataset
from database import initialize_database
from rag_engine import (
    generate_rag_answer,
    get_knowledge_base_count,
    index_documents,
)


# -----------------------------------------------------------------------------
# Application configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="EdgeSight Query Nexus",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)


DEVELOPMENT_USER = {
    "user_id": "edgesight-local-development",
    "username": "Local development",
}

PAGE_LABELS = {
    "About": "◈  About",
    "Chat": "✦  New chat",
    "Overview": "▦  Operations overview",
    "Equipment Health": "⌁  Equipment health",
    "Sensor Charts": "⌁  Sensor charts",
    "Explore Records": "▤  Explore records",
    "Knowledge Base": "▧  Knowledge base",
}

DASHBOARD_PAGES = {
    "Overview",
    "Equipment Health",
    "Sensor Charts",
    "Explore Records",
}


def inject_styles() -> None:
    """Apply the compact dark visual system used throughout the app."""
    st.markdown(
        """
        <style>
        :root {
            --edge-canvas: #08111f;
            --edge-surface: #0f1d31;
            --edge-surface-raised: #152843;
            --edge-border: #233a59;
            --edge-muted: #91a4bd;
            --edge-text: #edf5ff;
            --edge-primary: #4ea1ff;
            --edge-primary-strong: #287ee8;
            --edge-success: #49d6ae;
        }

        .stApp, [data-testid="stMain"] {
            background: var(--edge-canvas);
            color: var(--edge-text);
        }

        .block-container {
            max-width: 1280px;
            padding: 1.6rem 2.2rem 2.5rem;
        }

        [data-testid="stSidebar"] {
            background: #0b1728;
            border-right: 1px solid var(--edge-border);
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1rem;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label {
            border-radius: 9px;
            margin: 1px 0;
            padding: 6px 7px;
            transition: background 160ms ease;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
            background: #152b48;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] p,
        [data-testid="stSidebar"] .stCaption,
        [data-testid="stSidebar"] p {
            color: #a8b9ce;
        }

        .edge-brand {
            color: var(--edge-text);
            font-size: 1.45rem;
            font-weight: 750;
            letter-spacing: -0.04em;
            line-height: 1.1;
        }

        .edge-kicker {
            color: var(--edge-primary);
            font-size: 0.67rem;
            font-weight: 700;
            letter-spacing: 0.17em;
            margin-top: 0.3rem;
            text-transform: uppercase;
        }

        .edge-sidebar-heading {
            color: #7891b0;
            font-size: 0.65rem;
            font-weight: 700;
            letter-spacing: 0.13em;
            margin: 1rem 0 0.2rem;
            text-transform: uppercase;
        }

        .edge-page-kicker {
            color: var(--edge-primary);
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.14em;
            margin-bottom: 0.35rem;
            text-transform: uppercase;
        }

        .edge-page-title {
            color: var(--edge-text);
            font-size: clamp(2rem, 4vw, 3.1rem);
            font-weight: 760;
            letter-spacing: -0.055em;
            line-height: 1.08;
            margin: 0;
        }

        .edge-page-subtitle {
            color: var(--edge-muted);
            font-size: 1rem;
            line-height: 1.65;
            margin: 0.8rem 0 1.5rem;
            max-width: 780px;
        }

        .edge-hero {
            background:
                radial-gradient(circle at top right, rgba(78, 161, 255, 0.18), transparent 34%),
                linear-gradient(135deg, #102642 0%, #0d1b2f 55%, #0a1525 100%);
            border: 1px solid #28496d;
            border-radius: 20px;
            margin: 0.8rem 0 1.5rem;
            overflow: hidden;
            padding: clamp(1.6rem, 5vw, 3.6rem);
        }

        .edge-hero-mark {
            color: var(--edge-primary);
            font-size: 1.15rem;
            font-weight: 800;
            letter-spacing: 0.16em;
            text-transform: uppercase;
        }

        .edge-hero h1 {
            color: var(--edge-text);
            font-size: clamp(2.2rem, 5vw, 4.1rem);
            letter-spacing: -0.065em;
            line-height: 1.02;
            margin: 0.7rem 0 1rem;
            max-width: 800px;
        }

        .edge-hero p {
            color: #b9cbe0;
            font-size: 1.05rem;
            line-height: 1.75;
            margin: 0;
            max-width: 680px;
        }

        .edge-card {
            background: var(--edge-surface);
            border: 1px solid var(--edge-border);
            border-radius: 14px;
            min-height: 178px;
            padding: 1.15rem 1.2rem;
        }

        .edge-card-mark {
            color: var(--edge-success);
            font-size: 1.25rem;
            font-weight: 800;
        }

        .edge-card h3 {
            color: var(--edge-text);
            font-size: 1.02rem;
            margin: 0.75rem 0 0.4rem;
        }

        .edge-card p {
            color: var(--edge-muted);
            font-size: 0.9rem;
            line-height: 1.55;
            margin: 0;
        }

        .edge-dev-note {
            background: rgba(255, 190, 92, 0.08);
            border: 1px solid rgba(255, 190, 92, 0.34);
            border-radius: 12px;
            color: #f2d49a;
            font-size: 0.9rem;
            line-height: 1.55;
            margin-top: 1.2rem;
            padding: 0.85rem 1rem;
        }

        [data-testid="stChatMessage"] {
            background: var(--edge-surface);
            border: 1px solid var(--edge-border);
            border-radius: 14px;
            margin-bottom: 0.8rem;
            padding: 0.85rem 1rem;
        }

        [data-testid="stChatMessage"] p,
        [data-testid="stChatMessage"] li {
            color: var(--edge-text);
            line-height: 1.65;
        }

        [data-testid="stChatInput"] {
            background: var(--edge-surface-raised);
            border: 1px solid #31557d;
            border-radius: 14px;
        }

        [data-testid="stChatInput"] textarea {
            color: var(--edge-text);
        }

        .stButton > button,
        .stDownloadButton > button {
            background: var(--edge-primary-strong);
            border: 1px solid var(--edge-primary-strong);
            border-radius: 9px;
            color: #ffffff;
            font-weight: 600;
            min-height: 2.35rem;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover {
            background: var(--edge-primary);
            border-color: var(--edge-primary);
            color: #07101c;
        }

        [data-testid="stMetric"] {
            background: var(--edge-surface);
            border: 1px solid var(--edge-border);
            border-radius: 12px;
            padding: 0.8rem;
        }

        [data-testid="stMetricLabel"] p {
            color: var(--edge-muted);
        }

        [data-testid="stDataFrame"],
        [data-testid="stExpander"] {
            border: 1px solid var(--edge-border);
            border-radius: 12px;
        }

        hr {
            border-color: var(--edge-border);
        }

        @media (max-width: 720px) {
            .block-container {
                padding: 1rem 1rem 2rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialise_session() -> None:
    """Set predictable local-development state for every app session."""
    defaults = {
        "development_user": DEVELOPMENT_USER.copy(),
        "messages": [],
        "current_conversation_id": None,
        "selected_page": "About",
        "sidebar_page": "About",
        "conversation_feedback": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def local_user_id() -> str:
    """Return the one local identity used by all conversation APIs."""
    return st.session_state.development_user["user_id"]


def new_chat() -> None:
    st.session_state.current_conversation_id = None
    st.session_state.messages = []
    st.session_state.sidebar_page = "Chat"
    st.session_state.selected_page = "Chat"


def open_conversation(conversation_id: str) -> None:
    """Load a saved conversation and move the workspace to Chat."""
    try:
        st.session_state.messages = get_conversation_messages(
            local_user_id(),
            conversation_id,
        )
        st.session_state.current_conversation_id = conversation_id
        st.session_state.sidebar_page = "Chat"
        st.session_state.selected_page = "Chat"
    except Exception as error:
        st.session_state.conversation_feedback = (
            f"Could not open that conversation: {error}"
        )


def rename_saved_conversation(conversation_id: str, input_key: str) -> None:
    title = st.session_state.get(input_key, "").strip()
    if rename_conversation(local_user_id(), conversation_id, title):
        st.session_state.conversation_feedback = "Conversation renamed."
    else:
        st.session_state.conversation_feedback = (
            "Enter a conversation title between 1 and 100 characters."
        )


def remove_saved_conversation(conversation_id: str) -> None:
    delete_conversation(local_user_id(), conversation_id)
    if st.session_state.current_conversation_id == conversation_id:
        st.session_state.current_conversation_id = None
        st.session_state.messages = []
    st.session_state.conversation_feedback = "Conversation deleted."


@st.cache_data(show_spinner=False)
def get_data() -> pd.DataFrame:
    return load_dataset()


def render_page_header(kicker: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="edge-page-kicker">{kicker}</div>
        <h1 class="edge-page-title">{title}</h1>
        <p class="edge-page-subtitle">{subtitle}</p>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(df: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    """Render compact navigation, saved chats, and dashboard filters."""
    user_id = local_user_id()

    st.sidebar.markdown(
        """
        <div style="padding: 0.25rem 0.25rem 0.8rem;">
            <div style="color:#4ea1ff;font-size:1.35rem;line-height:1;">◈</div>
            <div class="edge-brand">EdgeSight</div>
            <div class="edge-kicker">Query Nexus</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.caption("Local interface development mode")

    st.sidebar.button(
        "＋ New chat",
        key="edgesight_new_chat",
        on_click=new_chat,
        use_container_width=True,
    )

    st.sidebar.markdown('<div class="edge-sidebar-heading">Workspace</div>', unsafe_allow_html=True)
    page_options = list(PAGE_LABELS)
    selected_page = st.sidebar.radio(
        "Navigate",
        options=page_options,
        format_func=lambda page: PAGE_LABELS[page],
        label_visibility="collapsed",
        key="sidebar_page",
    )
    st.session_state.selected_page = selected_page

    st.sidebar.divider()
    st.sidebar.markdown('<div class="edge-sidebar-heading">Conversations</div>', unsafe_allow_html=True)
    try:
        conversations = get_user_conversations(user_id)
    except Exception as error:
        conversations = []
        st.sidebar.warning(f"Chat history is temporarily unavailable: {error}")

    if conversations:
        for conversation in conversations:
            conversation_id = conversation["conversation_id"]
            title = conversation["title"] or "Untitled conversation"
            input_key = f"rename_input_{conversation_id}"

            # One expander per chat keeps the sidebar compact without nesting
            # expanders, which Streamlit does not support.
            with st.sidebar.expander(f"💬 {title}", expanded=False):
                st.button(
                    "Open conversation",
                    key=f"open_conversation_{conversation_id}",
                    on_click=open_conversation,
                    args=(conversation_id,),
                    use_container_width=True,
                )
                st.text_input(
                    "Conversation title",
                    value=title,
                    key=input_key,
                )
                st.button(
                    "Rename",
                    key=f"rename_button_{conversation_id}",
                    on_click=rename_saved_conversation,
                    args=(conversation_id, input_key),
                    use_container_width=True,
                )
                st.button(
                    "Delete conversation",
                    key=f"delete_button_{conversation_id}",
                    on_click=remove_saved_conversation,
                    args=(conversation_id,),
                    use_container_width=True,
                )
    else:
        st.sidebar.caption("Saved conversations will appear here.")

    if st.session_state.conversation_feedback:
        st.sidebar.info(st.session_state.conversation_feedback)
        st.session_state.conversation_feedback = None

    filtered_df = df.copy()
    if selected_page in DASHBOARD_PAGES:
        st.sidebar.divider()
        st.sidebar.markdown('<div class="edge-sidebar-heading">Data filter</div>', unsafe_allow_html=True)
        if "asset_type" in df.columns:
            asset_types = sorted(
                df["asset_type"].dropna().astype(str).unique().tolist()
            )
            selected_type = st.sidebar.selectbox(
                "Equipment type",
                options=["All equipment types", *asset_types],
                key="dashboard_asset_type",
            )
            if selected_type != "All equipment types":
                filtered_df = df[
                    df["asset_type"].astype(str) == selected_type
                ].copy()
            st.sidebar.caption(f"{len(filtered_df):,} matching records")
        else:
            st.sidebar.info("Equipment type is unavailable in this dataset.")

    st.sidebar.divider()
    st.sidebar.caption("Use the arrow at the top-right to collapse this sidebar.")
    return selected_page, filtered_df


def render_about_page() -> None:
    st.markdown(
        """
        <section class="edge-hero">
            <div class="edge-hero-mark">◈ EdgeSight Query Nexus</div>
            <h1>IoT operations intelligence, in one focused workspace.</h1>
            <p>
                Explore equipment health, investigate operational signals, and ask
                questions of your connected data with an AI assistant built for
                maintenance and reliability teams.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    card_columns = st.columns(3)
    cards = [
        (
            "⌁",
            "Equipment health",
            "Review the latest health scores, sensor readings, failures, and maintenance signals for every asset.",
        ),
        (
            "◌",
            "Operational analytics",
            "Filter records, monitor sensor trends, and turn day-to-day telemetry into clear operational context.",
        ),
        (
            "✦",
            "AI-assisted inquiry",
            "Ask natural-language questions about your IoT data and indexed technical documentation from Chat.",
        ),
    ]
    for column, (mark, title, description) in zip(card_columns, cards):
        with column:
            st.markdown(
                f"""
                <section class="edge-card">
                    <div class="edge-card-mark">{mark}</div>
                    <h3>{title}</h3>
                    <p>{description}</p>
                </section>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        """
        <div class="edge-dev-note">
            <strong>Development-only configuration:</strong> login, admin, and password
            checks are currently bypassed and every saved conversation uses one local
            development identity. Restore authentication before deploying this app to
            shared, staging, or public environments.
        </div>
        """,
        unsafe_allow_html=True,
    )


def persist_message(conversation_id: str | None, role: str, content: str) -> None:
    """Persist when storage is available without losing the live chat on failure."""
    if conversation_id is None:
        return
    try:
        save_message(local_user_id(), conversation_id, role, content)
    except Exception as error:
        st.warning(
            "This response is visible in the current session but could not be saved: "
            f"{error}"
        )


def render_chat_page(df: pd.DataFrame) -> None:
    if not st.session_state.messages:
        st.markdown(
            """
            <section class="edge-hero">
                <div class="edge-hero-mark">AI operations assistant</div>
                <h1>What would you like to understand?</h1>
                <p>
                    Ask about equipment health, failure patterns, maintenance, sensors,
                    or the documents in your knowledge base.
                </p>
            </section>
            """,
            unsafe_allow_html=True,
        )
    else:
        render_page_header(
            "Conversation",
            "EdgeSight assistant",
            "Ask follow-up questions to continue analyzing your IoT operations data.",
        )
        for message in st.session_state.messages:
            if message.get("role") in {"user", "assistant"}:
                with st.chat_message(message["role"]):
                    st.markdown(str(message.get("content", "")))

    question = st.chat_input("Message EdgeSight Query Nexus…")
    if not question or not question.strip():
        return

    user_question = question.strip()
    conversation_id = st.session_state.current_conversation_id
    if conversation_id is None:
        try:
            conversation_id = create_conversation(
                local_user_id(),
                title=user_question[:60],
            )
            st.session_state.current_conversation_id = conversation_id
        except Exception as error:
            st.warning(
                "This chat will continue for the current session, but a saved "
                f"conversation could not be created: {error}"
            )

    st.session_state.messages.append({"role": "user", "content": user_question})
    persist_message(conversation_id, "user", user_question)

    try:
        with st.spinner("EdgeSight is analyzing your IoT data…"):
            answer = generate_rag_answer(
                user_question,
                df,
                chat_history=st.session_state.messages[:-1],
            )
        answer = str(answer)
    except Exception as error:
        answer = (
            "I couldn't generate a response. Check that Ollama is running and that "
            "the required models are installed.\n\n"
            f"Technical details: {error}"
        )

    st.session_state.messages.append({"role": "assistant", "content": answer})
    persist_message(conversation_id, "assistant", answer)
    st.rerun()


def render_overview_page(df: pd.DataFrame, filtered_df: pd.DataFrame) -> None:
    render_page_header(
        "Analytics",
        "IoT operations overview",
        "A concise summary of the records selected by the current equipment filter.",
    )
    total_records = len(filtered_df)
    unique_assets = (
        filtered_df["asset_id"].nunique() if "asset_id" in filtered_df.columns else 0
    )
    if "ai_health_index_score" in filtered_df.columns:
        health_scores = pd.to_numeric(
            filtered_df["ai_health_index_score"], errors="coerce"
        )
        average_health = (
            f"{health_scores.mean():.2f}" if health_scores.notna().any() else "No data"
        )
    else:
        average_health = "Unavailable"

    col1, col2, col3 = st.columns(3)
    col1.metric("Matching records", f"{total_records:,}")
    col2.metric("Unique assets", f"{unique_assets:,}")
    col3.metric("Average health score", average_health)

    st.divider()
    st.subheader("Records by equipment type")
    if "asset_type" not in filtered_df.columns:
        st.warning("The dataset does not contain an asset_type column.")
    elif filtered_df.empty:
        st.info("No records match the current equipment filter.")
    else:
        st.bar_chart(filtered_df["asset_type"].value_counts())

    with st.expander("Dataset source and coverage"):
        st.write("**Source file:** `data/iot_operations_01.csv`")
        st.write(f"**Total rows:** {len(df):,}")
        st.write(f"**Total columns:** {len(df.columns)}")
        st.code(", ".join(df.columns.astype(str)))
        if "observation_date" in df.columns:
            dates = pd.to_datetime(df["observation_date"], errors="coerce").dropna()
            if not dates.empty:
                st.write(f"**Earliest observation:** {dates.min().date()}")
                st.write(f"**Latest observation:** {dates.max().date()}")


def render_sensor_charts_page(filtered_df: pd.DataFrame) -> None:
    render_page_header(
        "Analytics",
        "Sensor readings over time",
        "Compare bearing temperature and vibration trends for the selected equipment.",
    )
    sensor_columns = [
        "observation_date",
        "bearing_temp_c",
        "vibration_rms_mm_s",
    ]
    missing_columns = [
        column for column in sensor_columns if column not in filtered_df.columns
    ]
    if missing_columns:
        st.warning("Missing sensor columns: " + ", ".join(missing_columns))
        return
    if filtered_df.empty:
        st.info("No records match the current equipment filter.")
        return

    sensor_df = filtered_df[sensor_columns].copy()
    sensor_df["observation_date"] = pd.to_datetime(
        sensor_df["observation_date"], errors="coerce"
    )
    sensor_df["bearing_temp_c"] = pd.to_numeric(
        sensor_df["bearing_temp_c"], errors="coerce"
    )
    sensor_df["vibration_rms_mm_s"] = pd.to_numeric(
        sensor_df["vibration_rms_mm_s"], errors="coerce"
    )

    temperature_column, vibration_column = st.columns(2)
    with temperature_column:
        st.subheader("Bearing temperature")
        temperature_data = sensor_df.dropna(
            subset=["observation_date", "bearing_temp_c"]
        )
        if temperature_data.empty:
            st.info("No dated temperature readings are available.")
        else:
            chart_data = (
                temperature_data.groupby("observation_date")["bearing_temp_c"]
                .mean()
                .sort_index()
            )
            st.line_chart(chart_data, y_label="Temperature (°C)")
            st.metric(
                "Average temperature",
                f"{temperature_data['bearing_temp_c'].mean():.2f} °C",
            )

    with vibration_column:
        st.subheader("Vibration level")
        vibration_data = sensor_df.dropna(
            subset=["observation_date", "vibration_rms_mm_s"]
        )
        if vibration_data.empty:
            st.info("No dated vibration readings are available.")
        else:
            chart_data = (
                vibration_data.groupby("observation_date")["vibration_rms_mm_s"]
                .mean()
                .sort_index()
            )
            st.line_chart(chart_data, y_label="Vibration (mm/s RMS)")
            st.metric(
                "Average vibration",
                f"{vibration_data['vibration_rms_mm_s'].mean():.2f} mm/s",
            )


def render_equipment_health_page(filtered_df: pd.DataFrame) -> None:
    render_page_header(
        "Analytics",
        "Detailed equipment health",
        "Review the latest observation for each asset, including sensor, failure, and maintenance signals.",
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
    available_columns = [
        column for column in health_columns if column in filtered_df.columns
    ]
    if "asset_id" not in filtered_df.columns:
        st.warning("The equipment health table requires an asset_id column.")
        return
    if filtered_df.empty:
        st.info("No equipment records match the current filter.")
        return

    health_df = filtered_df[available_columns].copy()
    if "observation_date" in health_df.columns:
        health_df["observation_date"] = pd.to_datetime(
            health_df["observation_date"], errors="coerce"
        )
        health_df = health_df.sort_values("observation_date", na_position="first")
        health_df = health_df.drop_duplicates(subset=["asset_id"], keep="last")

    numeric_columns = [
        "ai_health_index_score",
        "bearing_temp_c",
        "vibration_rms_mm_s",
        "num_sensor_alerts_last_7d",
        "prior_failures_last_12m",
    ]
    for column in numeric_columns:
        if column in health_df.columns:
            health_df[column] = pd.to_numeric(health_df[column], errors="coerce")

    health_df = health_df.rename(
        columns={
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
    )
    asset_search = st.text_input(
        "Search by asset ID",
        placeholder="Enter an asset ID…",
        key="health_asset_search",
    )
    if asset_search.strip():
        health_df = health_df[
            health_df["Asset ID"].astype(str).str.contains(
                asset_search.strip(), case=False, na=False, regex=False
            )
        ]

    st.caption(f"{len(health_df):,} assets displayed")
    if health_df.empty:
        st.info("No assets match your search.")
        return
    st.dataframe(health_df, use_container_width=True, hide_index=True)
    st.download_button(
        "Download equipment health table (CSV)",
        data=health_df.to_csv(index=False).encode("utf-8"),
        file_name="equipment_health_report.csv",
        mime="text/csv",
    )


def render_records_page(filtered_df: pd.DataFrame) -> None:
    render_page_header(
        "Analytics",
        "Explore records",
        "Inspect the IoT data behind EdgeSight and export the matching equipment records.",
    )
    if filtered_df.empty:
        st.info("There are no records to display for the current filter.")
        return
    st.caption(f"{len(filtered_df):,} matching records · showing the first 100")
    st.dataframe(filtered_df.head(100), use_container_width=True, hide_index=True)
    st.download_button(
        "Download filtered records (CSV)",
        data=filtered_df.to_csv(index=False).encode("utf-8"),
        file_name="iot_filtered_records.csv",
        mime="text/csv",
    )


def render_knowledge_base_page() -> None:
    render_page_header(
        "Knowledge base",
        "IoT document knowledge base",
        "Index technical manuals and notes so the assistant can use them in future answers.",
    )
    st.info("Place PDF, TXT, or Markdown files in the project's `documents` folder.")
    documents_folder = Path("documents")
    document_files = [
        file
        for extension in ("*.pdf", "*.txt", "*.md")
        for file in documents_folder.glob(extension)
    ]
    try:
        document_count = get_knowledge_base_count()
    except Exception as error:
        document_count = "Unavailable"
        st.warning(f"Could not read the knowledge base status: {error}")

    col1, col2 = st.columns(2)
    col1.metric("Indexed document chunks", document_count)
    col2.metric("Files available", len(document_files))

    st.subheader("Available documents")
    if document_files:
        for file in document_files:
            st.write(f"📄 {file.name}")
    else:
        st.warning("No documents found. Add a PDF or text file to the documents folder.")

    st.divider()
    if st.button("Index / update documents", use_container_width=True):
        with st.spinner("Reading documents and creating embeddings…"):
            try:
                result = index_documents()
                if result.get("success"):
                    st.success(result.get("message", "Documents indexed."))
                    st.write(f"Files processed: {result.get('files', 0)}")
                    st.write(f"Chunks indexed: {result.get('chunks', 0)}")
                    st.rerun()
                else:
                    st.warning(result.get("message", "Document indexing was not completed."))
            except Exception as error:
                st.error(f"Document indexing failed: {error}")
    st.caption("Re-index after adding or changing documents before asking about them in Chat.")


def main() -> None:
    inject_styles()
    initialise_session()

    # Auth is intentionally not imported or called. See DEVELOPMENT_USER above.
    initialize_database()

    try:
        df = get_data()
    except Exception as error:
        st.error(f"Could not load the dataset: {error}")
        st.info(
            "Check that data/iot_operations_01.csv exists and that data_loader.py works correctly."
        )
        st.stop()

    if df.empty:
        st.warning("The dataset is empty. Dashboard pages will have no records to display.")

    selected_page, filtered_df = render_sidebar(df)

    if selected_page == "About":
        render_about_page()
    elif selected_page == "Chat":
        render_chat_page(df)
    elif selected_page == "Overview":
        render_overview_page(df, filtered_df)
    elif selected_page == "Equipment Health":
        render_equipment_health_page(filtered_df)
    elif selected_page == "Sensor Charts":
        render_sensor_charts_page(filtered_df)
    elif selected_page == "Explore Records":
        render_records_page(filtered_df)
    elif selected_page == "Knowledge Base":
        render_knowledge_base_page()


if __name__ == "__main__":
    main()
