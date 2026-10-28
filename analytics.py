
import pandas as pd
from data_loader import get_dataset_from_database


def count_equipment(df):
    """Count the number of records and unique assets."""

    return {
        "total_records": len(df),
        "unique_assets": df["asset_id"].nunique()
    }


def average_health_score(df):
    """Calculate the average recorded health score."""

    scores = pd.to_numeric(
        df["ai_health_index_score"],
        errors="coerce"
    )

    if scores.notna().sum() == 0:
        return None

    return round(scores.mean(), 2)


def filter_by_equipment_type(df, equipment_type):
    """Return records matching an equipment type."""

    matching = df[
        df["asset_type"].astype(str).str.strip().str.casefold()
        == equipment_type.strip().casefold()
    ]

    return matching


def find_recorded_failures(df):
    """Find records marked as unscheduled failures."""

    failure_values = (
        df["unscheduled_failure_within_7d"]
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    return df[failure_values.isin(["yes", "true", "1"])]


def find_maintenance_due(df):
    """Find records marked as maintenance due within 7 days."""

    maintenance_values = (
        df["scheduled_pm_due_within_7d"]
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    return df[maintenance_values.isin(["yes", "true", "1"])]


if __name__ == "__main__":
    # Load the actual CSV using our existing file
    data = get_dataset_from_database()

    # 1. Count records and unique assets
    counts = count_equipment(data)
    print("\n--- Equipment Count ---")
    print("Total records:", counts["total_records"])
    print("Unique assets:", counts["unique_assets"])

    # 2. Calculate average health score
    print("\n--- Average Health Score ---")
    print("Average:", average_health_score(data))

    # 3. Find equipment types in the dataset
    print("\n--- Available Equipment Types ---")
    print(data["asset_type"].value_counts(dropna=False))

    # 4. Find recorded failures
    failures = find_recorded_failures(data)
    print("\n--- Recorded Failures ---")
    print("Matching records:", len(failures))
    print(failures[["asset_id", "asset_type",
                    "unscheduled_failure_within_7d"]].head())

    # 5. Find maintenance due
    maintenance = find_maintenance_due(data)
    print("\n--- Maintenance Due Within 7 Days ---")
    print("Matching records:", len(maintenance))
    print(maintenance[["asset_id", "asset_type",
                       "scheduled_pm_due_within_7d"]].head())

    # 6. Example: filter by equipment type
    # Replace "Pump" with a type shown in the output above.
    pumps = filter_by_equipment_type(data, "Pump")
    print("\n--- Example Equipment Type Filter ---")
    print("Matching pump records:", len(pumps))
    print(pumps[["asset_id", "asset_type"]].head())
