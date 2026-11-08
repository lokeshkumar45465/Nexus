"""Turn chart requests into chart specs using the real dataset numbers."""
import re

import pandas as pd

INTENT = re.compile(
    r"\b(chart|graph|plot|visuali[sz]e|visuali[sz]ation|diagram|histogram|"
    r"pie|bar|trend|distribution|scatter)\b",
    re.I,
)
FENCE = re.compile(r"```chart\n.*?```", re.S)

# topic -> (column, label)
NUMERIC = {
    "health": ("ai_health_index_score", "Average health score"),
    "temperature": ("bearing_temp_c", "Average bearing temperature (°C)"),
    "vibration": ("vibration_rms_mm_s", "Average vibration (mm/s)"),
}

HELP = (
    "I can chart records by equipment type, health score, bearing temperature, "
    "vibration, recorded failures, maintenance due and sensor alerts. Try: "
    "“bar chart of average health score by equipment type”, "
    "“pie chart of failures by equipment type”, "
    "“line chart of vibration over time”, “histogram of health scores” or "
    "“scatter of vibration vs temperature”."
)


def strip_charts(text):
    """Remove chart blocks so the language model never sees the JSON."""
    return FENCE.sub("[chart shown to the user]", text)


def wants_chart(question):
    return bool(INTENT.search(question))


def _flag(series):
    return series.astype(str).str.strip().str.casefold().isin(["yes", "true", "1"])


def _topic(q):
    for key, pattern in (
        ("temperature", r"temp|bearing"),
        ("vibration", r"vibrat"),
        ("health", r"health"),
        ("alerts", r"alert"),
        ("failures", r"fail"),
        ("maintenance", r"maint|\bpm\b"),
    ):
        if re.search(pattern, q):
            return key
    if re.search(r"record|asset|equipment|type|count|fleet|device|machine", q):
        return "records"
    return None


def _values(df, topic):
    """Return (values, aggregation, label) for a topic."""
    if topic in NUMERIC:
        column, label = NUMERIC[topic]
        return pd.to_numeric(df[column], errors="coerce"), "mean", label
    if topic == "alerts":
        values = pd.to_numeric(df["num_sensor_alerts_last_7d"], errors="coerce")
        return values.fillna(0), "sum", "Sensor alerts (last 7 days)"
    if topic == "failures":
        return _flag(df["unscheduled_failure_within_7d"]).astype(int), "sum", "Recorded failures"
    if topic == "maintenance":
        return _flag(df["scheduled_pm_due_within_7d"]).astype(int), "sum", "Maintenance due within 7 days"
    return pd.Series(1, index=df.index), "sum", "Records"


def _describe(title, labels, data):
    hi = max(range(len(data)), key=lambda i: data[i])
    lo = min(range(len(data)), key=lambda i: data[i])
    return f"{title}. Highest: {labels[hi]} ({data[hi]}). Lowest: {labels[lo]} ({data[lo]})."


def _no_chart(text):
    return {"text": text, "chart": None}


def build_chart(question, df):
    """Return None if no chart was requested, otherwise {"text", "chart"}."""
    q = question.lower()

    if not wants_chart(q):
        return None

    if df is None or df.empty:
        return _no_chart("There is no dataset loaded to chart.")

    topic = _topic(q)

    if re.search(r"pie|donut|doughnut", q):
        kind = "pie"
    elif re.search(r"\bline\b|trend|over time|timeline", q):
        kind = "line"
    else:
        kind = "bar"

    # Scatter: vibration against temperature
    if (
        re.search(r"scatter|correlation|\bvs\b|versus", q)
        and "vibrat" in q
        and re.search(r"temp|bearing", q)
    ):
        points = (
            df[["vibration_rms_mm_s", "bearing_temp_c"]]
            .apply(pd.to_numeric, errors="coerce")
            .dropna()
            .head(300)
        )
        data = [
            {"x": round(float(x), 2), "y": round(float(y), 2)}
            for x, y in points.itertuples(index=False)
        ]
        spec = {
            "type": "scatter",
            "title": "Vibration vs bearing temperature",
            "labels": [],
            "datasets": [{"label": "Records", "data": data}],
            "xLabel": "Vibration (mm/s)",
            "yLabel": "Bearing temperature (°C)",
        }
        return {
            "text": f"Scatter plot of {len(data)} records comparing vibration with bearing temperature.",
            "chart": spec,
        }

    if topic is None:
        return _no_chart(HELP)

    # Histogram: distribution of a numeric measurement
    if re.search(r"histogram|distribution", q) and topic in NUMERIC:
        column, label = NUMERIC[topic]
        axis = label.replace("Average ", "").capitalize()
        series = pd.to_numeric(df[column], errors="coerce").dropna()

        if series.empty:
            return _no_chart(f"There are no numeric values for {axis.lower()} to chart.")

        counts = pd.cut(series, bins=10).value_counts(sort=False)
        labels = [f"{iv.left:.1f}–{iv.right:.1f}" for iv in counts.index]
        data = [int(v) for v in counts.values]
        spec = {
            "type": "bar",
            "title": f"Distribution of {axis.lower()}",
            "labels": labels,
            "datasets": [{"label": "Records", "data": data}],
            "xLabel": axis,
            "yLabel": "Records",
        }
        return {"text": f"Distribution of {axis.lower()} across {len(series):,} records.", "chart": spec}

    values, agg, label = _values(df, topic)

    if kind == "line":
        dates = pd.to_datetime(df["observation_date"], errors="coerce")
        valid = dates.notna()

        if not valid.any():
            return _no_chart("The dataset has no valid observation dates, so I can’t draw a trend.")

        span = (dates[valid].max() - dates[valid].min()).days
        monthly = span > 90
        key = dates[valid].dt.to_period("M" if monthly else "D").astype(str)
        grouped = values[valid].groupby(key).agg(agg).dropna().tail(60)
        title = f"{label} over time"
        x_label = "Month" if monthly else "Date"
    else:
        key = (
            df["asset_type"].astype(str).str.strip()
            .replace({"": "Unknown", "nan": "Unknown"})
        )
        grouped = values.groupby(key).agg(agg).dropna().sort_values(ascending=False).head(15)
        title = f"{label} by equipment type"
        x_label = "Equipment type"

    if grouped.empty:
        return _no_chart("There is not enough data to draw that chart.")

    labels = [str(i) for i in grouped.index]
    data = [
        int(v) if float(v).is_integer() else round(float(v), 2)
        for v in grouped.values
    ]
    spec = {
        "type": kind,
        "title": title,
        "labels": labels,
        "datasets": [{"label": label, "data": data}],
        "xLabel": x_label,
        "yLabel": label,
    }
    return {"text": _describe(title, labels, data), "chart": spec}