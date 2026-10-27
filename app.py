
import streamlit as st
import pandas as pd
from data_loader import load_dataset
from analytics import (
    count_equipment,
    average_health_score,
    find_recorded_failures,
    find_maintenance_due,
)
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
    "Ask questions about your IoT equipment and "
    "explore your dataset."
)

# 3. Load the dataset
@st.cache_data
def get_data():
    return load_dataset()

try:
    df = get_data()
except Exception as error:
    st.error(f"Could not load the dataset: {error}")
    st.info(
        "Check that the CSV is in the data folder "
        "and that data_loader.py works correctly."
    )
    st.stop()

# DATA PROVENANCE: information about the loaded dataset

st.subheader("Data source and coverage")

source_file = "data/iot_operations_01.csv"

st.write("**Source file:**", source_file)
st.write("**Total rows:**", f"{len(df):,}")
st.write("**Total columns:**", len(df.columns))

st.write("**Available columns:**")
st.code(", ".join(df.columns.astype(str)))

# Convert observation_date to dates for reporting.
if "observation_date" in df.columns:
    dates = pd.to_datetime(
        df["observation_date"],
        errors="coerce"
    ).dropna()

    if not dates.empty:
        st.write(
            "**Earliest observation:**",
            str(dates.min().date())
        )
        st.write(
            "**Latest observation:**",
            str(dates.max().date())
        )
    else:
        st.info("No valid observation dates were found.")

# 4. Prepare the conversation history
if "messages" not in st.session_state:
    st.session_state.messages = []

# 5. Create the example questions
st.subheader("Try an example question")

examples = [
    "How many records are in the dataset?",
    "What is the average health score?",
    "How many recorded failures are there?",
    "How many maintenance records are due?",
]

columns = st.columns(2)

for index, question in enumerate(examples):
    if columns[index % 2].button(
        question,
        key=f"example_{index}",
        use_container_width=True,
    ):
        st.session_state.pending_question = question

# 6. Display the results area
st.subheader("Conversation")


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message["role"] == "assistant":
            with st.expander("Check answer source"):
                st.write(
                    "**Source:** data/iot_operations_01.csv"
                )
                st.write(
                    "**Dataset records available:**",
                    f"{len(df):,}"
                )

                if "health score" in message["content"].lower():
                    st.write(
                        "**Relevant column:** "
                        "ai_health_index_score"
                    )

                elif "failure" in message["content"].lower():
                    st.write(
                        "**Relevant column:** "
                        "unscheduled_failure_within_7d"
                    )

                elif "maintenance" in message["content"].lower():
                    st.write(
                        "**Relevant column:** "
                        "scheduled_pm_due_within_7d"
                    )

                elif "records" in message["content"].lower():
                    st.write(
                        "**Relevant data:** all dataset rows"
                    )

        if "table" in message:
            st.dataframe(
                message["table"],
                use_container_width=True
            )

st.sidebar.header("Dataset filters")

# Get actual equipment types from the CSV.
equipment_types = sorted(
    df["asset_type"].dropna().astype(str).unique().tolist()
)

selected_type = st.sidebar.selectbox(
    "Equipment type",
    ["All types"] + equipment_types
)

# Start with all records.
filtered_df = df.copy()

# Apply the selected equipment type.
if selected_type != "All types":
    filtered_df = filtered_df[
        filtered_df["asset_type"].astype(str)
        == selected_type
    ]

st.sidebar.write(
    f"Matching records: {len(filtered_df):,}"
)



# 7. Create the chat input
question = st.chat_input(
    "Ask a question about your IoT dataset..."
)

# Process either a typed question or an example question
if question:
    st.session_state.pending_question = question

if "pending_question" in st.session_state:
    user_question = st.session_state.pop("pending_question")

    # Save and display the user's question
    st.session_state.messages.append(
        {"role": "user", "content": user_question}
    )

    normalized = user_question.casefold()
    answer = ""
    result_table = None

    # 8. Match the question to an analytics function
    answer = understand_question(user_question, df)

st.session_state.messages.append(
    {
        "role": "assistant",
        "content": answer,
    }
)
st.rerun()
