import pandas as pd
from data_loader import load_dataset
from analytics import (
    count_equipment,
    average_health_score,
    filter_by_equipment_type,
    find_recorded_failures,
    find_maintenance_due,
)

data = load_dataset()

# Check 1: Total records
assert count_equipment(data)["total_records"] == len(data)
print("PASS: Total record count")

# Check 2: Unique asset count
assert (
    count_equipment(data)["unique_assets"]
    == data["asset_id"].nunique()
)
print("PASS: Unique asset count")

# Check 3: Average health score
expected_scores = pd.to_numeric(
    data["ai_health_index_score"],
    errors="coerce"
)
expected_average = (
    round(expected_scores.mean(), 2)
    if expected_scores.notna().any()
    else None
)

assert average_health_score(data) == expected_average
print("PASS: Average health score")

# Check 4: Equipment type filter
if data["asset_type"].notna().any():
    example_type = data["asset_type"].dropna().iloc[0]
    result = filter_by_equipment_type(data, str(example_type))
    expected = data[
        data["asset_type"].astype(str).str.strip().str.casefold()
        == str(example_type).strip().casefold()
    ]
    assert result.equals(expected)
print("PASS: Equipment type filter")

# Check 5: Failure filter
expected_failures = data[
    data["unscheduled_failure_within_7d"]
    .astype(str).str.strip().str.casefold()
    .isin(["yes", "true", "1"])
]
assert find_recorded_failures(data).equals(expected_failures)
print("PASS: Recorded failure filter")

# Check 6: Maintenance filter
expected_maintenance = data[
    data["scheduled_pm_due_within_7d"]
    .astype(str).str.strip().str.casefold()
    .isin(["yes", "true", "1"])
]
assert find_maintenance_due(data).equals(expected_maintenance)
print("PASS: Maintenance filter")

print("\nAll analytics checks passed!")
