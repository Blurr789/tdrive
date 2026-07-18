from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def generate_report(output_dir: str | Path, title: str = "北京夜间出租车活动与城市活力监测报告") -> Path:
    output = Path(output_dir)
    summary = read_json(output / "pipeline_summary.json")
    explanations = read_json(output / "region_explanations.json")

    scores_path = output / "region_scores_phase2.csv"
    if not scores_path.exists():
        scores_path = output / "region_scores.csv"
    scores = pd.read_csv(scores_path) if scores_path.exists() else pd.DataFrame()
    anomalies_path = output / "anomalies_attributed.csv"
    if not anomalies_path.exists():
        anomalies_path = output / "anomalies.csv"
    anomalies = pd.read_csv(anomalies_path) if anomalies_path.exists() else pd.DataFrame()
    score_methods = pd.read_csv(output / "score_method_comparison.csv") if (output / "score_method_comparison.csv").exists() else pd.DataFrame()
    forecast_metrics = pd.read_csv(output / "forecast_metrics.csv") if (output / "forecast_metrics.csv").exists() else pd.DataFrame()

    lines = [
        f"# {title}",
        "",
        "## 数据规模",
        "",
        f"- 输入行数：{summary.get('input_rows', 0):,}",
        f"- 清洗后行数：{summary.get('clean_rows', 0):,}",
        f"- 夜间活动记录数：{summary.get('night_rows', 0):,}",
        f"- 参与分析活动网格数：{summary.get('region_count', 0):,}",
        f"- 异常夜间活动数：{summary.get('anomaly_count', 0):,}",
        "",
        "## Top 10 夜间活动网格",
        "",
        "| 排名 | 活动网格 | 所属区域 | 活力分数 | 网格类型 |",
        "| --- | --- | --- | ---: | --- |",
    ]

    for index, row in scores.head(10).iterrows():
        spatial_unit = str(row["spatial_unit"])
        explanation = explanations.get(spatial_unit, {})
        zone = explanation.get("zone") or f"活动网格 {spatial_unit}"
        borough = explanation.get("borough") or ""
        region_type = explanation.get("region_type_label") or row.get("region_type", "")
        lines.append(
            f"| {index + 1} | {zone} | {borough} | {float(row.get('night_vitality_score', 0)):.2f} | {region_type} |"
        )

    lines.extend(["", "## 代表网格解释", ""])
    for row in scores.head(5).itertuples():
        explanation = explanations.get(str(row.spatial_unit), {})
        if not explanation:
            continue
        lines.append(f"### {explanation.get('zone') or f'活动网格 {row.spatial_unit}'}")
        lines.append("")
        lines.append(explanation.get("summary", ""))
        lines.append("")
        for reason in explanation.get("reasons", []):
            lines.append(f"- {reason}")
        lines.append("")

    lines.extend(["## 异常活动样例", ""])
    if anomalies.empty:
        lines.append("当前未检测到异常活动。")
    else:
        lines.append("| 活动网格 | 日期 | 小时 | 活动量 | 异常分数 | 可能原因 |")
        lines.append("| --- | --- | ---: | ---: | ---: | --- |")
        for _, row in anomalies.head(10).iterrows():
            lines.append(
                f"| {row.get('spatial_unit')} | {row.get('night_date')} | {row.get('hour')} | "
                f"{row.get('activity_count')} | {float(row.get('z_score', 0)):.2f} | {row.get('possible_reason', '')} |"
            )

    if not score_methods.empty:
        lines.extend(["", "## 评分方法对比", ""])
        lines.append("| 活动网格 | 人工权重 | 熵权法 | PCA | 分数差异 |")
        lines.append("| --- | ---: | ---: | ---: | ---: |")
        for _, row in score_methods.head(10).iterrows():
            unit_name = row.get("zone") or row.get("Zone") or f"活动网格 {row.get('spatial_unit')}"
            lines.append(
                f"| {unit_name} | "
                f"{float(row.get('manual_score', 0)):.2f} | {float(row.get('entropy_score', 0)):.2f} | "
                f"{float(row.get('pca_score', 0)):.2f} | {float(row.get('score_spread', 0)):.2f} |"
            )

    if not forecast_metrics.empty:
        lines.extend(["", "## 活动量预测模型评价", ""])
        lines.append("| 模型 | MAE | RMSE | MAPE |")
        lines.append("| --- | ---: | ---: | ---: |")
        for _, row in forecast_metrics.iterrows():
            lines.append(
                f"| {row.get('model')} | {float(row.get('mae', 0)):.2f} | "
                f"{float(row.get('rmse', 0)):.2f} | {float(row.get('mape', 0)):.2f}% |"
            )

    lines.extend(
        [
            "",
            "## 方法说明",
            "",
            "本项目以夜间出租车活动记录为核心，将城市划分为空间活动网格，并提取活动起点数、活动终点数、深夜活动占比、周末增幅、短距离活动比例、活动持续性等特征。随后通过鲁棒归一化与加权计算得到 Night Vitality Score，并使用聚类算法识别网格类型。对于北京 T-Drive 迁移版本，系统基于轨迹活动段生成 H3 活动网格图层，并在高德地图上展示夜间活力评分和异常活动。异常检测部分使用同网格同小时的 median/MAD 作为鲁棒基线，以降低极端值对判断的影响。",
        ]
    )

    target = output / "report.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    return target
