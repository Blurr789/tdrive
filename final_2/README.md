# Beijing NightSense

Beijing NightSense 是一个基于北京 T-Drive 出租车 GPS 轨迹的夜间出租车活动与城市活力监测系统。项目将原始轨迹点切分为轨迹活动段，并以 H3 活动网格作为空间分析单元，完成夜间活动聚合、活力评分、异常检测、POI 功能画像、可信度分析和高德地图前端展示。

当前主线聚焦北京城市夜间出租车活动监测，不再保留旧版城市案例配置。

## 核心功能

- 将 T-Drive 原始 GPS 轨迹转换为活动段。
- 筛选夜间时段 `20:00-03:00` 的出租车活动。
- 使用 H3 resolution 7 构建北京活动网格。
- 生成 Night Vitality Score，用于表达活动网格夜间活力水平。
- 基于 median/MAD 识别异常夜间活动。
- 使用高德逆地理编码补充区县、街道、商圈、POI 和 AOI 信息。
- 构建 POI 多样性、交通枢纽修正、评分方法对比和短时预测结果。
- 通过 Flask API 向前端提供统计结果、地图图层、异常事件、网格画像和报告内容。
- 通过 Vue + 高德地图展示北京夜间活力地图、异常活动、网格画像和可信度分析。

## 目录结构

```text
backend/                       Flask 后端 API
configs/beijing_tdrive.yaml    北京 T-Drive 主配置
../data/raw/tdrive/            T-Drive 原始轨迹数据
../data/processed/beijing_tdrive/ 活动段转换结果
frontend/                      Vue + 高德地图前端
outputs/beijing_tdrive/        北京主线分析输出
reports/                       最终报告、图件和报告生成脚本
scripts/data/                  数据转换与高德地名增强脚本
scripts/reports/               最终报告与图件辅助脚本
src/nightsense/                核心数据处理、评分、解释与评估模块
```

## 安装依赖

项目使用本地虚拟环境 `.venv`，不需要 Anaconda。

```powershell
cd D:\uns_2\final_2
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

前端依赖：

```powershell
cd D:\uns_2\final_2\frontend
npm.cmd install
```

## 数据处理

如需从 T-Drive 原始轨迹重新生成活动段：

```powershell
cd D:\uns_2\final_2
.\.venv\Scripts\Activate.ps1
python scripts\data\convert_tdrive_to_trips.py --input ..\data\raw\tdrive --output ..\data\processed\beijing_tdrive\activity_segments_gcj02.csv --recursive
```

运行北京主线数据管道：

```powershell
cd D:\uns_2\final_2
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="src"
python scripts\run_config.py configs\beijing_tdrive.yaml
```

如需重新生成高德逆地理编码地名表：

```powershell
cd D:\uns_2\final_2
.\.venv\Scripts\Activate.ps1
python scripts\data\enrich_beijing_grid_names.py --sleep 0.18
```

## 启动项目

后端：

```powershell
cd D:\uns_2\final_2
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="src"
$env:NIGHTSENSE_OUTPUT_DIR="outputs\beijing_tdrive"
python backend\app.py
```

前端：

```powershell
cd D:\uns_2\final_2\frontend
npm.cmd run dev
```

默认访问地址：

```text
后端：http://127.0.0.1:5000
前端：http://127.0.0.1:5173
```

高德地图 Key 配置在 `frontend/.env.local`：

```env
VITE_AMAP_KEY=你的高德Web JSAPI Key
VITE_AMAP_SECURITY_JSCODE=你的安全密钥
```

## 主要输出

北京主线输出目录：

```text
outputs/beijing_tdrive/
```

常用结果文件：

- `pipeline_summary.json`：管道运行摘要。
- `hourly_activity.csv`：按活动网格和小时聚合的夜间活动量。
- `region_scores.csv`：活动网格活力评分与类型。
- `h3_region_scores.csv`：H3 活动网格评分。
- `h3_region_scores_geojson.json`：前端地图使用的 H3 图层。
- `grid_name_lookup.csv`：高德逆地理编码地名增强结果。
- `poi_features.csv`：POI 功能画像特征。
- `anomalies_attributed.csv`：带归因信息的异常活动记录。
- `score_method_comparison.csv`：人工权重、熵权法和 PCA 评分对比。
- `forecast_metrics.csv`：短时预测模型指标。
- `report.md`：自动生成的分析摘要。

## 最终报告

最终 Word 报告和图件位于：

```text
reports/
```

报告生成脚本：

```powershell
cd D:\uns_2\final_2
.\.venv\Scripts\Activate.ps1
python scripts\reports\generate_beijing_final_report.py
```

图件辅助脚本：

```powershell
python scripts\reports\draw_remaining_figures.py
```

## 方法边界

- T-Drive 轨迹活动段不等同于真实乘客订单。
- 活动起点和活动终点来自轨迹活动段首尾点，是出租车活动位置的近似表达。
- 夜间出租车活动是城市夜间活力的代理变量，不能完整代表步行、地铁、网约车或消费行为。
- 高德逆地理编码提供的是网格中心点附近的 POI/AOI 和地名信息，不等同于完整空间普查。
