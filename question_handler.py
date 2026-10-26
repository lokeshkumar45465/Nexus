
from analytics import (
    count_equipment,
    average_health_score,
    find_recorded_failures,
    find_maintenance_due,
)


def understand_question(question, df):
    """
    Recognize supported questions and return
    an answer based on the actual dataset.
    """

    # Convert the question to lowercase
    # and remove extra spaces.
    text = question.casefold().strip()

    # Rule 1: Count all dataset records.
    record_questions = [
        "how many records",
        "total records",
        "number of records",
        "count records",
    ]

    if any(phrase in text for phrase in record_questions):
        result = count_equipment(df)

        return (
            f"The dataset contains "
            f"{result['total_records']:,} records."
        )

    # Rule 2: Count unique assets.
    asset_questions = [
        "unique assets",
        "distinct assets",
        "number of assets",
        "how many assets",
    ]

    if any(phrase in text for phrase in asset_questions):
        result = count_equipment(df)

        return (
            f"The dataset contains "
            f"{result['unique_assets']:,} unique asset IDs."
        )

    # Rule 3: Calculate average health score.
    health_questions = [
        "average health",
        "average health score",
        "health score average",
    ]

    if any(phrase in text for phrase in health_questions):
        score = average_health_score(df)

        if score is None:
            return "No numeric health scores are available."

        return f"The average recorded health score is {score}."

    # Rule 4: Find recorded failures.
    if "failure" in text or "failures" in text:
        failures = find_recorded_failures(df)

        return (
            f"Found {len(failures):,} records marked "
            "as unscheduled failures."
        )

    # Rule 5: Find maintenance due.
    if "maintenance" in text:
        maintenance = find_maintenance_due(df)

        return (
            f"Found {len(maintenance):,} records marked "
            "as maintenance due within 7 days."
        )

    # Rule 6: Safely handle unsupported questions.
    return (
        "I'm not able to answer that question yet "
        "using the available IoT dataset. "
        "Try asking about record counts, unique assets, "
        "average health score, recorded failures, "
        "or maintenance due within 7 days."
    )
