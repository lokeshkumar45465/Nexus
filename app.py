
import streamlit as st
import pandas as pd

from data_loader import load_dataset
from question_handler import understand_question


# 1. Configure the webpage
st.set_page_config(
    page_title="EdgeSight Query Nexus",
    page_icon="🤖",
    layout="wide",
)


# 2. Display the application title
st.title("🤖 EdgeSight Query Nexus")
st.write(
    "Ask questions about your IoT equipment, "
    "explore recorded data, and review equipment health."
)


# 3. Load the dataset safely
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


# 4. Check that the columns used by the dashboard exist
required_dashboard_columns = [
    "asset_id",
    "asset_type",
    "ai_health_index_score",
]

missing_columns = [
    column
    for column in required_dashboard_columns
    if column not in df.columns
]

if missing_columns:
    st.error(
        f"The dataset is missing required dashboard columns: "
        f"{', '.join(missing_columns)}"
    )
    st.stop()


# 5. Prepare the conversation history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None


# 6. Data source and coverage
with st.expander("Dataset source and coverage", expanded=False):
    st.write("**Source file:** data/iot_operations_01.csv")
    st.write(f"**Total rows:** {len(df):,}")
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
                "**Earliest observation:**",
                str(dates.min().date()),
            )
            st.write(
                "**Latest observation:**",
                str(dates.max().date()),
            )
        else:
            st.info("No valid observation dates were found.")


# 7. Equipment type filter
st.sidebar.header("Dashboard filters")

asset_types = sorted(
    df["asset_type"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

selected_type = st.sidebar.selectbox(
    "Equipment type",
    options=["All equipment types"] + asset_types,
)

if selected_type == "All equipment types":
    filtered_df = df.copy()
else:
    filtered_df = df[
        df["asset_type"].astype(str) == selected_type
    ].copy()

st.sidebar.write(
    f"**Matching records:** {len(filtered_df):,}"
)


# 8. Example questions
st.subheader("Try an example question")

examples = [
    "How many records are in the dataset?",
    "What is the average health score?",
    "How many recorded failures are there?",
    "How many maintenance records are due?",
]

example_columns = st.columns(2)

for index, example in enumerate(examples):
    if example_columns[index % 2].button(
        example,
        key=f"example_{index}",
        use_container_width=True,
    ):
        st.session_state.pending_question = example


# 9. Chat input
question = st.chat_input(
    "Ask a question about your IoT dataset..."
)

if question and question.strip():
    st.session_state.pending_question = question.strip()


# 10. Process the question BEFORE displaying the conversation
if st.session_state.pending_question:
    user_question = st.session_state.pending_question

    # Clear the pending question so it is not processed repeatedly.
    st.session_state.pending_question = None

    # Save the user's question.
    st.session_state.messages.append({
        "role": "user",
        "content": user_question,
    })

    # Calculate the answer before using the answer variable.
    try:
        answer = understand_question(user_question, filtered_df)

        if not isinstance(answer, str):
            answer = str(answer)

    except Exception as error:
        answer = (
            "Sorry, I couldn't process that question. "
            f"Details: {error}"
        )

    # Save the assistant's answer exactly once.
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
    })


# 11. Display the conversation
st.subheader("Conversation")

if not st.session_state.messages:
    st.info(
        "Choose an example question above or type a question "
        "in the chat box."
    )

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message["role"] == "assistant":
            with st.expander("Check answer source"):
                st.write(
                    "**Source:** data/iot_operations_01.csv"
                )
                st.write(
                    "**Records available to this answer:**",
                    f"{len(filtered_df):,}",
                )

                content = message["content"].casefold()

                if "health" in content:
                    st.write(
                        "**Relevant column:** "
                        "ai_health_index_score"
                    )
                elif "failure" in content:
                    st.write(
                        "**Relevant column:** "
                        "unscheduled_failure_within_7d"
                    )
                elif "maintenance" in content:
                    st.write(
                        "**Relevant column:** "
                        "scheduled_pm_due_within_7d"
                    )
                elif "record" in content:
                    st.write(
                        "**Relevant data:** dataset rows"
                    )


# 12. IoT Operations Dashboard
st.header("IoT Operations Dashboard")

col1, col2, col3 = st.columns(3)

col1.metric(
    "Matching records",
    f"{len(filtered_df):,}",
)

col2.metric(
    "Unique assets",
    f"{filtered_df['asset_id'].nunique():,}",
)

health_scores = pd.to_numeric(
    filtered_df["ai_health_index_score"],
    errors="coerce",
)

if health_scores.notna().any():
    average_health = round(health_scores.mean(), 2)
    health_display = str(average_health)
else:
    health_display = "No data"

col3.metric(
    "Average health score",
    health_display,
)


# 13. Records by equipment type
st.subheader("Records by equipment type")

if not filtered_df.empty:
    type_counts = filtered_df["asset_type"].value_counts()
    st.bar_chart(type_counts)
else:
    st.info("No equipment records match the selected filter.")


# 14. Display dataset records
st.subheader("Explore records")

if not filtered_df.empty:
    st.dataframe(
        filtered_df.head(100),
        use_container_width=True,
        hide_index=True,
    )
    st.caption("Showing up to 100 matching records.")
else:
    st.info("There are no records to display.")
