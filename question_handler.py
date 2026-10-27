from analytics import (
    count_equipment,
    average_health_score,
    find_recorded_failures,
    find_maintenance_due,
)


def understand_question(question, df):
    text = question.casefold().strip()

    record_questions = [
        "how many records",
        "total records",
        "number of records",
        "count records",
    ]

    if any(phrase in text for phrase in record_questions):
        result = count_equipment(df)
        return f"The dataset contains {result['total_records']:,} records."

    asset_questions = [
        "unique assets",
        "distinct assets",
        "number of assets",
        "how many assets",
    ]

    if any(phrase in text for phrase in asset_questions):
        result = count_equipment(df)
        return f"The dataset contains {result['unique_assets']:,} unique asset IDs."

    if "health" in text:
        score = average_health_score(df)

        if score is None:
            return "No numeric health scores are available."

        return f"The average recorded health score is {score}."

    if "failure" in text:
        failures = find_recorded_failures(df)
        return f"Found {len(failures):,} records marked as unscheduled failures."

    if "maintenance" in text:
        maintenance = find_maintenance_due(df)
        return f"Found {len(maintenance):,} records marked as maintenance due within 7 days."

    return (
        "I can't answer that question using the current rules. "
        "Try asking about records, assets, health scores, "
        "failures, or maintenance."
    )