
from pathlib import Path
import pandas as pd

# 1. Find the folder containing this Python file
PROJECT_FOLDER = Path(__file__).resolve().parent

# 2. Find the CSV dataset
DATASET_PATH = PROJECT_FOLDER / "data" / "iot_operations_01.csv"

# 3. List the columns our project expects
REQUIRED_COLUMNS = [
    "asset_id",
    "observation_date",
    "asset_type",
    "bearing_temp_c",
    "vibration_rms_mm_s",
    "ai_health_index_score",
    "num_sensor_alerts_last_7d",
    "prior_failures_last_12m",
    "scheduled_pm_due_within_7d",
    "unscheduled_failure_within_7d",
]


def load_dataset():
    """Load the CSV and check that required columns exist."""

    # Check whether the CSV file exists
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}"
        )

    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv(DATASET_PATH)

    # Remove accidental spaces around column names
    df.columns = df.columns.str.strip()

    # Find required columns that are missing
    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    return df


if __name__ == "__main__":
    # Load the dataset
    data = load_dataset()

    # Display basic information
    print("Dataset loaded successfully!")
    print("Number of rows:", len(data))
    print("Number of columns:", len(data.columns))

    print("\nColumn names:")
    print(data.columns.tolist())

    print("\nFirst five records:")
    print(data.head())

    print("\nDataset information:")
    data.info()
