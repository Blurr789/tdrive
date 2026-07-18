from __future__ import annotations

import pandas as pd


def hourly_activity(night_trips: pd.DataFrame) -> pd.DataFrame:
    pickups = (
        night_trips.groupby(["pickup_unit", "night_date", "hour", "day_of_week", "is_weekend"])
        .size()
        .rename("pickup_count")
        .reset_index()
        .rename(columns={"pickup_unit": "spatial_unit"})
    )
    dropoffs = (
        night_trips.groupby(["dropoff_unit", "night_date", "hour"])
        .size()
        .rename("dropoff_count")
        .reset_index()
        .rename(columns={"dropoff_unit": "spatial_unit"})
    )
    activity = pickups.merge(dropoffs, on=["spatial_unit", "night_date", "hour"], how="outer")
    activity["pickup_count"] = activity["pickup_count"].fillna(0).astype(int)
    activity["dropoff_count"] = activity["dropoff_count"].fillna(0).astype(int)
    activity["activity_count"] = activity["pickup_count"] + activity["dropoff_count"]
    activity["day_of_week"] = pd.to_datetime(activity["night_date"]).dt.dayofweek.astype("Int64")
    activity["is_weekend"] = activity["day_of_week"].isin([4, 5, 6])
    return activity.sort_values(["night_date", "hour", "spatial_unit"]).reset_index(drop=True)


def build_region_features(night_trips: pd.DataFrame, activity: pd.DataFrame) -> pd.DataFrame:
    pickup_features = (
        night_trips.groupby("pickup_unit")
        .agg(
            pickup_count=("trip_id", "count"),
            avg_distance=("distance", "mean"),
            avg_duration_min=("duration_min", "mean"),
            avg_price=("price", "mean"),
            short_trip_ratio=("distance", lambda series: (series <= 2).mean()),
            late_pickup_ratio=("hour", lambda series: series.isin([0, 1, 2]).mean()),
            weekend_pickup_ratio=("is_weekend", "mean"),
        )
        .reset_index()
        .rename(columns={"pickup_unit": "spatial_unit"})
    )

    dropoff_features = (
        night_trips.groupby("dropoff_unit")
        .size()
        .rename("dropoff_count")
        .reset_index()
        .rename(columns={"dropoff_unit": "spatial_unit"})
    )

    persistence = (
        activity[activity["activity_count"] > 0]
        .groupby("spatial_unit")
        .agg(
            active_night_hours=("activity_count", "count"),
            active_nights=("night_date", "nunique"),
            max_hourly_activity=("activity_count", "max"),
        )
        .reset_index()
    )

    weekend_activity = (
        activity.groupby(["spatial_unit", "is_weekend"])["activity_count"]
        .mean()
        .unstack(fill_value=0)
        .reindex(columns=[False, True], fill_value=0)
        .reset_index()
    )
    weekend_activity.columns = ["spatial_unit", "weekday_avg_activity", "weekend_avg_activity"]

    features = pickup_features.merge(dropoff_features, on="spatial_unit", how="outer")
    features = features.merge(persistence, on="spatial_unit", how="left")
    features = features.merge(weekend_activity, on="spatial_unit", how="left")

    numeric_columns = [column for column in features.columns if column != "spatial_unit"]
    features[numeric_columns] = features[numeric_columns].fillna(0)
    features["total_activity"] = features["pickup_count"] + features["dropoff_count"]
    features["inflow_outflow_balance"] = (
        (features["dropoff_count"] - features["pickup_count"])
        / features["total_activity"].replace(0, pd.NA)
    ).fillna(0)
    features["activity_persistence"] = features["active_night_hours"] / features["active_night_hours"].max()
    features["weekend_boost"] = (
        (features["weekend_avg_activity"] + 1) / (features["weekday_avg_activity"] + 1)
    )
    return features.sort_values("total_activity", ascending=False).reset_index(drop=True)
