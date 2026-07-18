from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split


FORECAST_FEATURE_COLUMNS = [
    "hour",
    "day_of_week",
    "is_weekend",
    "previous_hour_activity",
    "same_hour_last_week",
    "rolling_mean_3h",
]


def forecast_features(activity: pd.DataFrame) -> pd.DataFrame:
    data = activity.copy()
    data["spatial_unit"] = data["spatial_unit"].astype(str)
    data = data.sort_values(["spatial_unit", "night_date", "hour"]).reset_index(drop=True)
    grouped = data.groupby("spatial_unit")["activity_count"]
    data["previous_hour_activity"] = grouped.shift(1)
    data["rolling_mean_3h"] = grouped.shift(1).rolling(3, min_periods=1).mean().reset_index(level=0, drop=True)
    data["same_hour_last_week"] = data.groupby(["spatial_unit", "hour"])["activity_count"].shift(7)
    return data.dropna(subset=["previous_hour_activity"]).fillna(0)


def build_forecast_outputs(output_dir: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    output = Path(output_dir)
    path = output / "hourly_activity.csv"
    if not path.exists():
        return pd.DataFrame(), pd.DataFrame()
    data = forecast_features(pd.read_csv(path))
    data["is_weekend"] = data["is_weekend"].astype(int)
    x = data[FORECAST_FEATURE_COLUMNS].astype(float)
    y = data["activity_count"].astype(float)

    if len(data) < 20:
        return pd.DataFrame(), pd.DataFrame()

    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.25, random_state=42)
    baseline_pred = x_test["previous_hour_activity"].to_numpy()
    model = RandomForestRegressor(n_estimators=80, max_depth=12, random_state=42, n_jobs=-1)
    model.fit(x_train, y_train)
    rf_pred = model.predict(x_test)

    def metrics(name: str, pred: np.ndarray) -> dict[str, float | str]:
        mae = mean_absolute_error(y_test, pred)
        rmse = mean_squared_error(y_test, pred) ** 0.5
        mape = (np.abs((y_test.to_numpy() - pred) / np.maximum(y_test.to_numpy(), 1))).mean() * 100
        return {"model": name, "mae": round(float(mae), 3), "rmse": round(float(rmse), 3), "mape": round(float(mape), 3)}

    metrics_df = pd.DataFrame([metrics("previous_hour_baseline", baseline_pred), metrics("random_forest", rf_pred)])
    metrics_df.to_csv(output / "forecast_metrics.csv", index=False)

    top_units = data.groupby("spatial_unit")["activity_count"].sum().sort_values(ascending=False).head(20).index
    predictions = []
    for spatial_unit in top_units:
        region = data[data["spatial_unit"] == spatial_unit].sort_values(["night_date", "hour"])
        last = region.iloc[-1]
        next_hour = (int(last["hour"]) + 1) % 24
        row = pd.DataFrame(
            [
                {
                    "hour": next_hour,
                    "day_of_week": int(last["day_of_week"]),
                    "is_weekend": int(last["is_weekend"]),
                    "previous_hour_activity": float(last["activity_count"]),
                    "same_hour_last_week": float(last.get("same_hour_last_week", 0) or 0),
                    "rolling_mean_3h": float(region.tail(3)["activity_count"].mean()),
                }
            ]
        )
        predictions.append(
            {
                "spatial_unit": spatial_unit,
                "forecast_hour": next_hour,
                "baseline_forecast": round(float(row["previous_hour_activity"].iloc[0]), 2),
                "rf_forecast": round(float(model.predict(row[FORECAST_FEATURE_COLUMNS])[0]), 2),
            }
        )

    forecast_df = pd.DataFrame(predictions)
    forecast_df.to_csv(output / "region_forecasts.csv", index=False)
    return metrics_df, forecast_df

