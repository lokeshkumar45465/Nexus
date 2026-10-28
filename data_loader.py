
from pathlib import Path
import sqlite3
import pandas as pd

# 1. Find the folder containing this Python file
PROJECT_FOLDER = Path(__file__).resolve().parent

# 2. Find the CSV dataset
DATASET_PATH = PROJECT_FOLDER / "data" / "iot_operations_01.csv"

# 3. Set the location of our SQLite database
DATABASE_PATH = PROJECT_FOLDER / "data" / "edgesight.db"

# 4. Name the database table
TABLE_NAME = "iot_operations"

# 5. List the columns our project expects
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

    df = pd.read_csv(DATASET_PATH)

    # Remove accidental spaces around column names
    df.columns = df.columns.str.strip()

    # Check whether required columns are missing
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


def initialize_database(force_reload=False):
    """Create the SQLite database and import CSV data if needed."""

    # Ensure the data folder exists
    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # Open a connection to SQLite
    conn = sqlite3.connect(DATABASE_PATH)

    try:
        # Check whether our table already exists
        result = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = ?
            """,
            (TABLE_NAME,)
        ).fetchone()

        table_exists = result is not None

        # Import the CSV if the table is missing,
        # or reload it when explicitly requested
        if not table_exists or force_reload:
            df = load_dataset()

            df.to_sql(
                TABLE_NAME,
                conn,
                if_exists="replace",
                index=False
            )

            print(
                f"Imported {len(df)} records into SQLite."
            )

    finally:
        conn.close()


def get_dataset_from_database():
    """Read IoT records from the SQLite database."""

    # Create and initialize the database if needed
    initialize_database()

    conn = sqlite3.connect(DATABASE_PATH)

    try:
        df = pd.read_sql_query(
            f'SELECT * FROM "{TABLE_NAME}"',
            conn
        )
    finally:
        conn.close()

    return df


def refresh_database():
    """Reload the database from the latest CSV file."""

    initialize_database(force_reload=True)


if __name__ == "__main__":
    # Load the original CSV
    data = load_dataset()

    print("CSV loaded successfully!")
    print("Number of rows:", len(data))
    print("Number of columns:", len(data.columns))

    # Create the database and import data
    initialize_database()

    # Read data back from SQLite
    database_data = get_dataset_from_database()

    print("\nSQLite database loaded successfully!")
    print("Database location:", DATABASE_PATH)
    print("Database rows:", len(database_data))

    print("\nFirst five database records:")
    print(database_data.head())

    print("\nDataset information:")
    database_data.info()