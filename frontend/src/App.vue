<template>
  <main class="shell">
    <aside class="sidebar">
      <p class="eyebrow">北京夜间出租车活动</p>
      <h1>城市活力监测</h1>
      <p v-if="apiStatus" class="api-status">{{ apiStatus }}</p>

      <nav class="view-tabs" aria-label="分析视图">
        <button
          v-for="view in viewOptions"
          :key="view.value"
          :class="{ active: activeView === view.value }"
          type="button"
          @click="activeView = view.value"
        >
          {{ view.label }}
        </button>
      </nav>

      <section class="metrics">
        <article>
          <span>活动网格</span>
          <strong>{{ summary.region_count ?? regions.length }}</strong>
        </article>
        <article>
          <span>异常活动</span>
          <strong>{{ summary.anomaly_count ?? anomalies.length }}</strong>
        </article>
        <article>
          <span>最高分</span>
          <strong>{{ topScore }}</strong>
        </article>
      </section>

      <section v-if="activeView === 'anomalies'" class="sidebar-agent-panel">
        <template v-if="selectedAnomaly">
          <div class="section-title compact">
            <h2>选中异常活动</h2>
            <span>{{ selectedAnomaly.hour }}:00</span>
          </div>
          <article class="selected-anomaly-card">
            <strong>{{ anomalyDisplayName(selectedAnomaly) }}</strong>
            <span>{{ selectedAnomaly.night_date }} · {{ numberText(selectedAnomaly.activity_count) }} 条活动记录</span>
            <div class="selected-anomaly-stats">
              <span>历史基线</span><b>{{ numberText(selectedAnomaly.baseline_median) }}</b>
              <span>异常强度</span><b>{{ anomalyStrength(selectedAnomaly) }}</b>
              <span>活动起点 / 终点</span><b>{{ numberText(selectedAnomaly.pickup_count) }} / {{ numberText(selectedAnomaly.dropoff_count) }}</b>
            </div>
          </article>

          <button
            class="ai-button sidebar-ai-button"
            type="button"
            :disabled="isAnomalyLoading(selectedAnomaly)"
            @click="analyzeAnomaly(selectedAnomaly, Boolean(anomalyAgentResult(selectedAnomaly)))"
          >
            {{ isAnomalyLoading(selectedAnomaly) ? '分析中...' : anomalyAgentResult(selectedAnomaly) ? '重新分析' : 'AI 分析' }}
          </button>

          <p v-if="anomalyAgentError(selectedAnomaly)" class="agent-error">{{ anomalyAgentError(selectedAnomaly) }}</p>

          <section v-if="anomalyAgentResult(selectedAnomaly)" class="sidebar-agent-result">
            <h3>AI 分析</h3>
            <p>{{ agentSummary(anomalyAgentResult(selectedAnomaly)) }}</p>
            <div v-if="agentItems(anomalyAgentResult(selectedAnomaly), 'likely_causes').length">
              <span>可能原因</span>
              <ul>
                <li v-for="(cause, index) in agentItems(anomalyAgentResult(selectedAnomaly), 'likely_causes')" :key="`cause-${index}`">{{ cause }}</li>
              </ul>
            </div>
            <div v-if="agentItems(anomalyAgentResult(selectedAnomaly), 'evidence').length">
              <span>数据证据</span>
              <ul>
                <li v-for="(evidence, index) in agentItems(anomalyAgentResult(selectedAnomaly), 'evidence')" :key="`evidence-${index}`">{{ evidence }}</li>
              </ul>
            </div>
            <div v-if="agentItems(anomalyAgentResult(selectedAnomaly), 'recommended_checks').length">
              <span>建议核查</span>
              <ul>
                <li v-for="(check, index) in agentItems(anomalyAgentResult(selectedAnomaly), 'recommended_checks')" :key="`check-${index}`">{{ check }}</li>
              </ul>
            </div>
          </section>
        </template>
        <p v-else class="sidebar-agent-empty">选中一条异常活动后，可在这里生成 AI 分析。</p>
      </section>

      <template v-if="activeView === 'map'">
        <section class="insight-summary">
          <h2>当前结论</h2>
          <p>{{ mapInsight }}</p>
        </section>

        <section class="time-control">
          <div class="section-title">
            <h2>夜间时段</h2>
            <span>{{ selectedHourLabel }}</span>
          </div>
          <input v-model.number="selectedHourIndex" type="range" min="0" :max="hourOptions.length - 1" @input="refreshMap" />
          <div class="tick-row">
            <span v-for="option in hourOptions" :key="option.value">{{ option.label }}</span>
          </div>
        </section>

        <section class="map-display">
          <div class="section-title">
            <h2>地图显示</h2>
            <span>{{ showLabels ? '核心标记开启' : '核心标记隐藏' }}</span>
          </div>
          <button class="toggle-button" type="button" :class="{ active: showLabels }" @click="toggleMapLabels">
            {{ showLabels ? '隐藏核心标记' : '显示核心标记' }}
          </button>
        </section>

        <section class="map-search">
          <div class="section-title">
          <h2>搜索活动网格</h2>
            <span>{{ searchMatches.length }} 条结果</span>
          </div>
          <input v-model="regionQuery" type="search" placeholder="搜索活动网格、H3 编号或北京区域" />
          <div v-if="regionQuery" class="search-results">
            <button
              v-for="region in searchMatches.slice(0, 6)"
              :key="region.spatial_unit"
              type="button"
              @click="focusRegion(region.spatial_unit)"
            >
              <span>{{ labelRegion(region) }}</span>
              <b>{{ Number(region.night_vitality_score || 0).toFixed(1) }}</b>
            </button>
          </div>
        </section>

        <section>
          <h2>活动活力 Top 5</h2>
          <div class="region-list">
            <button
              v-for="region in topRegions"
              :key="region.spatial_unit"
              class="region-row"
              type="button"
              @click="focusRegion(region.spatial_unit)"
            >
              <span>
                <b>{{ labelRegion(region) }}</b>
                <small>{{ translateRegionType(region.region_type) }}</small>
              </span>
              <strong>{{ Number(region.night_vitality_score).toFixed(1) }}</strong>
            </button>
          </div>
        </section>

        <section>
          <h2>整夜走势</h2>
          <div class="hourly-strip">
            <article v-for="row in hourly" :key="row.hour">
              <span>{{ row.hour }}:00</span>
              <div><i :style="{ height: `${barHeight(row.activity_count)}%` }"></i></div>
              <b>{{ numberText(row.activity_count) }}</b>
            </article>
          </div>
        </section>
      </template>
    </aside>

    <section class="map-panel">
      <div v-show="activeView === 'map'" id="map"></div>
      <div v-if="activeView === 'map' && mapStatus" class="map-status">{{ mapStatus }}</div>
      <div v-if="activeView === 'map'" class="legend">
        <div class="legend-title">{{ legendTitle }}</div>
        <div class="legend-gradient" aria-hidden="true"></div>
        <div class="legend-scale"><span>低活动</span><span>中等</span><span>高活动 / 异常集中</span></div>
      </div>

      <aside v-if="activeView === 'map' && selectedRegion" class="detail-drawer">
        <button class="close-button" type="button" @click="clearSelectedRegion">关闭</button>
        <p class="eyebrow">{{ selectedRegion.borough || '北京活动网格' }}</p>
        <h2>{{ labelRegion(selectedRegion) }}</h2>
        <div class="drawer-score">
          <strong>{{ Number(selectedRegion.night_vitality_score || 0).toFixed(1) }}</strong>
          <span>{{ translateRegionType(selectedRegion.region_type) }}</span>
        </div>

        <section v-if="selectedRegion.explanation?.summary">
          <h3>网格画像</h3>
          <p>{{ selectedRegion.explanation.summary }}</p>
          <ul>
            <li v-for="reason in selectedRegion.explanation.reasons" :key="reason">{{ reason }}</li>
          </ul>
        </section>

        <section>
          <h3>快速判断</h3>
          <div class="explain-stack">
            <article>
              <span>为什么活跃</span>
              <p>{{ vitalityReason(selectedRegion) }}</p>
            </article>
            <article>
              <span>重点关注</span>
              <p>{{ watchPoint(selectedRegion) }}</p>
            </article>
            <article>
              <span>活动特征</span>
              <p>{{ comparisonText(selectedRegion) }}</p>
            </article>
          </div>
        </section>

        <section>
          <h3>关键指标</h3>
          <div class="detail-grid">
            <span>活动起点数</span><b>{{ numberText(selectedRegion.pickup_count) }}</b>
            <span>活动终点数</span><b>{{ numberText(selectedRegion.dropoff_count) }}</b>
            <span>深夜活动占比</span><b>{{ ratioText(selectedRegion.late_pickup_ratio) }}</b>
            <span>周末增幅</span><b>{{ Number(selectedRegion.weekend_boost || 0).toFixed(2) }}</b>
            <span>POI 多样性</span><b>{{ ratioText(selectedRegion.poi_diversity) }}</b>
            <span>交通枢纽修正</span><b>{{ Number(selectedRegion.hub_penalty || 0).toFixed(1) }}</b>
          </div>
        </section>

        <section>
          <h3>网格小时曲线</h3>
          <div class="mini-bars">
            <div
              v-for="row in selectedRegion.hourly_activity || []"
              :key="row.hour"
              class="mini-bar"
              :style="{ height: `${detailBarHeight(row.activity_count)}%` }"
              :title="`${row.hour}:00 ${row.activity_count}`"
            ></div>
          </div>
        </section>
      </aside>

      <section v-if="activeView === 'anomalies'" class="analysis-view">
        <div class="view-header">
          <p class="eyebrow">异常追踪</p>
          <h2>夜间出租车活动异常</h2>
          <span>查看活动量突然升高或结构异常的网格，并定位可能原因。</span>
        </div>
        <div class="event-grid">
          <article
            v-for="item in anomalies.slice(0, 24)"
            :key="anomalyKey(item)"
            class="event-card"
            :class="{ expanded: isAnomalyExpanded(item) }"
            role="button"
            tabindex="0"
            @click="toggleAnomaly(item)"
            @keydown.enter="toggleAnomaly(item)"
          >
            <div class="event-card-head">
              <strong>{{ item.night_date }} {{ item.hour }}:00</strong>
              <span>{{ anomalyDisplayName(item) }} · {{ numberText(item.activity_count) }} 条活动记录</span>
            </div>
            <p>{{ item.possible_reason || '夜间出租车活动出现明显波动，可结合活动结构和交通情况查看。' }}</p>

            <div v-if="isAnomalyExpanded(item)" class="event-detail" @click.stop>
              <div class="event-detail-grid">
                <span>历史基线</span><b>{{ numberText(item.baseline_median) }}</b>
                <span>异常强度</span><b>{{ anomalyStrength(item) }}</b>
                <span>活动起点 / 终点</span><b>{{ numberText(item.pickup_count) }} / {{ numberText(item.dropoff_count) }}</b>
              </div>
            </div>
          </article>
        </div>
      </section>

      <section v-if="activeView === 'profile'" class="analysis-view">
        <div class="view-header">
          <p class="eyebrow">网格库</p>
          <h2>活动网格画像</h2>
          <span>浏览全部活动网格，按活力、类型和行政区快速定位值得关注的夜间空间。</span>
        </div>

        <div class="library-toolbar">
          <input v-model="profileQuery" type="search" placeholder="搜索活动网格、行政区或 H3 编号" />
          <select v-model="profileTypeFilter">
            <option value="all">全部类型</option>
            <option v-for="type in profileTypes" :key="type" :value="type">{{ translateRegionType(type) }}</option>
          </select>
          <select v-model="profileBoroughFilter">
            <option value="all">全部行政区</option>
            <option v-for="borough in profileBoroughs" :key="borough" :value="borough">{{ borough }}</option>
          </select>
          <select v-model="profileSort">
            <option value="score">按活力排序</option>
            <option value="activity">按活动量排序</option>
            <option value="poi">按 POI 排序</option>
            <option value="weekend">按周末增幅排序</option>
          </select>
        </div>

        <div class="library-layout">
          <div class="rank-table">
            <div class="rank-row head">
              <span>排名</span><span>活动网格</span><span>类型</span><span>活力</span><span>POI</span><span>枢纽修正</span>
            </div>
            <button
              v-for="(region, index) in filteredProfileRegions"
              :key="region.spatial_unit"
              :class="{ active: String(selectedRegion?.spatial_unit) === String(region.spatial_unit) }"
              class="rank-row profile-row"
              type="button"
              @click="openRegionProfile(region.spatial_unit)"
            >
              <b>{{ index + 1 }}</b>
              <span>{{ labelRegion(region) }}</span>
              <span>{{ translateRegionType(region.region_type) }}</span>
              <strong>{{ Number(region.night_vitality_score || 0).toFixed(1) }}</strong>
              <span>{{ ratioText(region.poi_diversity) }}</span>
              <span>{{ Number(region.hub_penalty || 0).toFixed(1) }}</span>
            </button>
          </div>

          <aside class="profile-detail">
            <template v-if="selectedRegion">
              <p class="eyebrow">{{ selectedRegion.borough || '北京活动网格' }}</p>
              <h3>{{ labelRegion(selectedRegion) }}</h3>
              <div class="drawer-score compact-score">
                <strong>{{ Number(selectedRegion.night_vitality_score || 0).toFixed(1) }}</strong>
                <span>{{ translateRegionType(selectedRegion.region_type) }}</span>
              </div>
              <div class="explain-stack">
                <article>
                  <span>为什么活跃</span>
                  <p>{{ vitalityReason(selectedRegion) }}</p>
                </article>
                <article>
                  <span>重点关注</span>
                  <p>{{ watchPoint(selectedRegion) }}</p>
                </article>
                <article>
                  <span>活动特征</span>
                  <p>{{ comparisonText(selectedRegion) }}</p>
                </article>
              </div>
              <div class="detail-grid">
                <span>活动总量</span><b>{{ numberText(selectedRegion.total_activity) }}</b>
                <span>深夜活动占比</span><b>{{ ratioText(selectedRegion.late_pickup_ratio) }}</b>
                <span>周末增幅</span><b>{{ Number(selectedRegion.weekend_boost || 0).toFixed(2) }}</b>
                <span>POI 多样性</span><b>{{ ratioText(selectedRegion.poi_diversity) }}</b>
              </div>
            </template>
            <template v-else>
              <p class="eyebrow">网格详情</p>
              <h3>选择一个活动网格</h3>
              <p class="muted">点击左侧列表中的活动网格，查看它的活力来源和运营关注点。</p>
            </template>
          </aside>
          </div>
      </section>

      <section v-if="activeView === 'methods'" class="analysis-view report-view">
        <div class="view-header">
          <p class="eyebrow">可信度</p>
          <h2>结果可信度</h2>
          <span>用简洁指标说明结果是否稳定，详细模型参数收进高级信息。</span>
        </div>

        <div class="method-summary">
          <article v-for="metric in forecastMetrics" :key="metric.model">
            <span>{{ modelLabel(metric.model) }}</span>
            <strong>{{ Number(metric.mae || 0).toFixed(1) }}</strong>
            <small>平均误差越低，短时判断越稳</small>
          </article>
        </div>

        <details class="advanced-panel">
          <summary>高级信息</summary>
          <h3 class="subsection-title">评分一致性</h3>
          <div class="rank-table">
            <div class="rank-row head method">
              <span>活动网格</span><span>业务评分</span><span>数据权重</span><span>综合提取</span><span>差异</span>
            </div>
            <div v-for="row in scoreMethods.slice(0, 12)" :key="row.spatial_unit" class="rank-row method">
              <span>{{ labelRegion(row) }}</span>
              <strong>{{ Number(row.manual_score || 0).toFixed(1) }}</strong>
              <strong>{{ Number(row.entropy_score || 0).toFixed(1) }}</strong>
              <strong>{{ Number(row.pca_score || 0).toFixed(1) }}</strong>
              <span>{{ Number(row.score_spread || 0).toFixed(1) }}</span>
            </div>
          </div>
        </details>

        <h3 class="subsection-title">下一小时预测</h3>
        <div class="forecast-grid">
          <article v-for="row in forecasts" :key="row.spatial_unit" class="forecast-card">
            <span>{{ labelRegion(row) }}</span>
            <strong>{{ Number(row.rf_forecast || 0).toFixed(0) }}</strong>
            <small>{{ row.forecast_hour }}:00 预测活动量 · 参考值 {{ Number(row.baseline_forecast || 0).toFixed(0) }}</small>
          </article>
        </div>

        <h3 class="subsection-title">分析摘要</h3>
        <pre>{{ reportContent }}</pre>
      </section>
    </section>
  </main>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, shallowRef, watch } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:5000'
const AMAP_KEY = import.meta.env.VITE_AMAP_KEY || ''
const AMAP_SECURITY_JSCODE = import.meta.env.VITE_AMAP_SECURITY_JSCODE || ''

const summary = ref({})
const regions = ref([])
const hourly = ref([])
const anomalies = ref([])
const scoreMethods = ref([])
const forecastMetrics = ref([])
const forecasts = ref([])
const reportContent = ref('')
const activeView = ref('map')
const overlays = ref([])
const labelMarkers = ref([])
const baseTileLayer = ref(null)
const trafficLayer = ref(null)
const map = ref(null)
const activeInfoWindow = ref(null)
const selectedOverlay = shallowRef(null)
const selectedSpatialUnit = ref('')
const amapReady = ref(false)
const mapStatus = ref('')
const apiStatus = ref('')
const selectedRegion = ref(null)
const currentGeojson = ref(null)
const selectedHourIndex = ref(0)
const regionQuery = ref('')
const profileQuery = ref('')
const profileTypeFilter = ref('all')
const profileBoroughFilter = ref('all')
const profileSort = ref('score')
const showTraffic = ref(false)
const showLabels = ref(true)
const expandedAnomalyKey = ref('')
const anomalyAgentResults = ref({})
const anomalyAgentLoading = ref({})
const anomalyAgentErrors = ref({})

const viewOptions = [
  { label: '活动地图', value: 'map' },
  { label: '异常活动', value: 'anomalies' },
  { label: '网格画像', value: 'profile' },
  { label: '可信度', value: 'methods' },
]

const hourOptions = [
  { label: '综合', value: 'all' },
  { label: '20', value: 20 },
  { label: '21', value: 21 },
  { label: '22', value: 22 },
  { label: '23', value: 23 },
  { label: '0', value: 0 },
  { label: '1', value: 1 },
  { label: '2', value: 2 },
]

const selectedHour = computed(() => hourOptions[selectedHourIndex.value])
const legendTitle = computed(() => selectedHour.value.value === 'all' ? '夜间活动活力图例' : `${selectedHour.value.label}:00 小时活动量图例`)
const selectedHourLabel = computed(() => selectedHour.value.value === 'all' ? '综合评分' : `${selectedHour.value.label}:00`)
const topRegions = computed(() => regions.value.slice(0, 5))
const topScore = computed(() => Math.max(0, ...regions.value.map((row) => Number(row.night_vitality_score || 0))).toFixed(1))
const selectedAnomaly = computed(() => {
  return anomalies.value.find((item) => anomalyKey(item) === expandedAnomalyKey.value) || null
})
const mapInsight = computed(() => {
  if (!topRegions.value.length) return '数据加载后会显示当前夜间出租车活动的主要集中网格。'
  const names = topRegions.value.slice(0, 3).map(labelRegion).join('、')
  const coreCount = regions.value.filter((region) => Number(region.night_vitality_score || 0) >= 75).length
  const hourText = selectedHour.value.value === 'all' ? '综合夜间活动活力' : `${selectedHour.value.label}:00 的活动量`
  return `${hourText}主要集中在 ${names}，当前共有 ${coreCount} 个活动网格进入高活力梯队。`
})
const searchMatches = computed(() => {
  const query = regionQuery.value.trim().toLowerCase()
  if (!query) return []
  return regions.value.filter((region) => {
    const text = `${region.spatial_unit} ${region.display_name || ''} ${region.zone || region.Zone || ''} ${region.borough || region.Borough || ''} ${region.district || ''} ${region.township || ''}`.toLowerCase()
    return text.includes(query)
  })
})
const profileTypes = computed(() => {
  return [...new Set(regions.value.map((region) => region.region_type).filter(Boolean))]
})
const profileBoroughs = computed(() => {
  return [...new Set(regions.value.map((region) => region.borough || region.Borough).filter(Boolean))].sort()
})
const filteredProfileRegions = computed(() => {
  const query = profileQuery.value.trim().toLowerCase()
  const sortKey = {
    score: 'night_vitality_score',
    activity: 'total_activity',
    poi: 'poi_diversity',
    weekend: 'weekend_boost',
  }[profileSort.value]
  return regions.value
    .filter((region) => {
      const matchesQuery = !query || `${region.spatial_unit} ${region.display_name || ''} ${region.zone || region.Zone || ''} ${region.borough || region.Borough || ''} ${region.district || ''} ${region.township || ''}`.toLowerCase().includes(query)
      const matchesType = profileTypeFilter.value === 'all' || region.region_type === profileTypeFilter.value
      const matchesBorough = profileBoroughFilter.value === 'all' || (region.borough || region.Borough) === profileBoroughFilter.value
      return matchesQuery && matchesType && matchesBorough
    })
    .slice()
    .sort((a, b) => Number(b[sortKey] || 0) - Number(a[sortKey] || 0))
})

function clampRatio(value) {
  return Math.max(0, Math.min(1, Number(value || 0)))
}

function hexToRgb(hex) {
  const value = hex.replace('#', '')
  return {
    r: parseInt(value.slice(0, 2), 16),
    g: parseInt(value.slice(2, 4), 16),
    b: parseInt(value.slice(4, 6), 16),
  }
}

function rgbToHex({ r, g, b }) {
  return `#${[r, g, b].map((value) => Math.round(value).toString(16).padStart(2, '0')).join('')}`
}

function interpolateHex(start, end, amount) {
  const from = hexToRgb(start)
  const to = hexToRgb(end)
  return rgbToHex({
    r: from.r + (to.r - from.r) * amount,
    g: from.g + (to.g - from.g) * amount,
    b: from.b + (to.b - from.b) * amount,
  })
}

function colorFor(scoreRatio) {
  const ratio = clampRatio(scoreRatio)
  const stops = [
    [0, '#141923'],
    [0.18, '#3f1f12'],
    [0.38, '#92400e'],
    [0.58, '#ea8a1a'],
    [0.78, '#f97316'],
    [1, '#b91c1c'],
  ]
  for (let index = 1; index < stops.length; index += 1) {
    const [stop, color] = stops[index]
    const [previousStop, previousColor] = stops[index - 1]
    if (ratio <= stop) {
      return interpolateHex(previousColor, color, (ratio - previousStop) / (stop - previousStop))
    }
  }
  return stops[stops.length - 1][1]
}

function styleFeature(feature) {
  const ratio = clampRatio(feature.properties?.score_ratio)
  return {
    strokeColor: ratio >= 0.65 ? '#fed7aa' : ratio >= 0.32 ? '#fdba74' : '#64748b',
    strokeWeight: 0.3 + ratio * 0.65,
    strokeOpacity: 0.12 + ratio * 0.42,
    fillColor: colorFor(ratio),
    fillOpacity: 0.025 + ratio * 0.38,
  }
}

function selectedFeatureStyle(featureOrProperties = {}) {
  const properties = featureOrProperties.properties || featureOrProperties
  const ratio = clampRatio(properties?.score_ratio)
  return {
    strokeColor: '#fff7ed',
    strokeWeight: 2.4,
    strokeOpacity: 0.95,
    fillColor: ratio >= 0.68 ? '#dc2626' : '#fb923c',
    fillOpacity: Math.min(0.62, 0.34 + ratio * 0.24),
    zIndex: 220,
  }
}

function restoreOverlayStyle(overlay) {
  const properties = overlay?.getExtData?.()
  if (!properties || typeof overlay?.setOptions !== 'function') return
  overlay.setOptions({ ...styleFeature({ properties }), zIndex: 10 })
}

function isSelectedOverlay(overlay) {
  const spatialUnit = overlay?.getExtData?.()?.spatial_unit
  return selectedSpatialUnit.value && String(spatialUnit) === String(selectedSpatialUnit.value)
}

function highlightOverlay(overlay) {
  if (!overlay || typeof overlay?.setOptions !== 'function') return
  if (selectedOverlay.value && selectedOverlay.value !== overlay) restoreOverlayStyle(selectedOverlay.value)
  selectedOverlay.value = overlay
  selectedSpatialUnit.value = String(overlay.getExtData?.()?.spatial_unit || '')
  overlay.setOptions(selectedFeatureStyle(overlay.getExtData?.() || {}))
}

function highlightSpatialUnit(spatialUnit) {
  const overlay = overlays.value.find((item) => {
    return typeof item.getPath === 'function' && String(item.getExtData?.()?.spatial_unit) === String(spatialUnit)
  })
  if (overlay) highlightOverlay(overlay)
  return overlay
}

function clearSelectedRegion() {
  restoreOverlayStyle(selectedOverlay.value)
  selectedOverlay.value = null
  selectedSpatialUnit.value = ''
  selectedRegion.value = null
  closeInfoWindow()
}

function shouldRenderFeature(feature) {
  const ratio = Number(feature.properties?.score_ratio || 0)
  const zoom = Number(map.value?.getZoom?.() || 11)
  if (selectedHour.value.value !== 'all') return ratio >= 0.08 || zoom >= 12
  if (zoom < 10) return ratio >= 0.45
  if (zoom < 11) return ratio >= 0.25
  if (zoom < 12) return ratio >= 0.12
  return ratio > 0
}

function labelRegion(region) {
  return region.display_name || region.zone || region.Zone || `活动网格 ${region.spatial_unit}`
}

function translateRegionType(type) {
  const labels = {
    nightlife_core: '夜间活动核心区',
    transport_hub_like: '交通枢纽型网格',
    return_destination: '夜间到达热点',
    departure_hotspot: '夜间出发热点',
    mixed_evening_area: '混合夜间活动区',
    low_activity: '低活跃区',
    no_activity: '暂无活跃记录',
    insufficient_data: '数据不足',
  }
  return labels[type] || type
}

function numberText(value) {
  return Number(value || 0).toLocaleString('zh-CN')
}

function ratioText(value) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`
}

function barHeight(value) {
  const maxValue = Math.max(1, ...hourly.value.map((row) => Number(row.activity_count || 0)))
  return 12 + (Number(value || 0) / maxValue) * 88
}

function detailBarHeight(value) {
  const rows = selectedRegion.value?.hourly_activity || []
  const maxValue = Math.max(1, ...rows.map((row) => Number(row.activity_count || 0)))
  return 12 + (Number(value || 0) / maxValue) * 88
}

async function fetchJson(path) {
  let response
  try {
    response = await fetch(`${API_BASE}${path}`)
  } catch {
    throw new Error(`后端未连接：${API_BASE}`)
  }
  if (!response.ok) throw new Error(`请求失败: ${path}`)
  return response.json()
}

async function postJson(path, payload) {
  let response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  } catch {
    throw new Error(`后端未连接：${API_BASE}`)
  }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.error || `请求失败: ${path}`)
  return data
}

function anomalyKey(item) {
  return `${item.spatial_unit}-${item.night_date}-${item.hour}`
}

function anomalyDisplayName(item) {
  return item.display_name || item.zone || item.Zone || `活动网格 ${item.spatial_unit}`
}

function isAnomalyExpanded(item) {
  return expandedAnomalyKey.value === anomalyKey(item)
}

function toggleAnomaly(item) {
  const key = anomalyKey(item)
  expandedAnomalyKey.value = expandedAnomalyKey.value === key ? '' : key
}

function anomalyAgentResult(item) {
  return anomalyAgentResults.value[anomalyKey(item)]
}

function cleanAgentText(value) {
  if (value == null) return ''
  if (typeof value === 'string') return value.trim().replace(/^[-*•\d.、\s]+/, '').trim()
  if (typeof value === 'number') return String(value)
  return JSON.stringify(value)
}

function normalizeAgentItems(value) {
  if (Array.isArray(value)) return value.map(cleanAgentText).filter(Boolean)
  if (value == null) return []
  if (typeof value === 'string') {
    const text = value.trim()
    if (!text) return []
    if (text.startsWith('[') && text.endsWith(']')) {
      try {
        return normalizeAgentItems(JSON.parse(text))
      } catch {
        return [text]
      }
    }
    return text
      .split(/\r?\n|[；;]/)
      .map(cleanAgentText)
      .filter(Boolean)
  }
  if (typeof value === 'object') return Object.values(value).map(cleanAgentText).filter(Boolean)
  return [cleanAgentText(value)].filter(Boolean)
}

function agentItems(result, field) {
  return normalizeAgentItems(result?.[field])
}

function agentSummary(result) {
  const summary = normalizeAgentItems(result?.summary)
  return summary.join('；') || '暂无摘要。'
}

function isAnomalyLoading(item) {
  return Boolean(anomalyAgentLoading.value[anomalyKey(item)])
}

function anomalyAgentError(item) {
  return anomalyAgentErrors.value[anomalyKey(item)] || ''
}

function anomalyStrength(item) {
  const zScore = Number(item.z_score || 0)
  if (zScore >= 20) return '极高'
  if (zScore >= 10) return '高'
  if (zScore >= 5) return '中'
  return '低'
}

async function analyzeAnomaly(item, force = false) {
  const key = anomalyKey(item)
  anomalyAgentLoading.value = { ...anomalyAgentLoading.value, [key]: true }
  anomalyAgentErrors.value = { ...anomalyAgentErrors.value, [key]: '' }
  try {
    const result = await postJson('/api/ai/anomalies/explain', {
      spatial_unit: item.spatial_unit,
      night_date: item.night_date,
      hour: item.hour,
      force,
    })
    anomalyAgentResults.value = { ...anomalyAgentResults.value, [key]: result }
  } catch (error) {
    anomalyAgentErrors.value = { ...anomalyAgentErrors.value, [key]: error.message }
  } finally {
    anomalyAgentLoading.value = { ...anomalyAgentLoading.value, [key]: false }
  }
}

async function loadRegionDetail(spatialUnit) {
  selectedRegion.value = await fetchJson(`/api/regions/${spatialUnit}`)
}

async function openRegionProfile(spatialUnit) {
  await loadRegionDetail(spatialUnit)
}

async function focusRegion(spatialUnit) {
  if (!map.value || !amapReady.value) return
  const overlay = overlays.value.find((item) => String(item.getExtData()?.spatial_unit) === String(spatialUnit))
  if (overlay) {
    highlightOverlay(overlay)
    map.value.setFitView([overlay], false, [28, 28, 28, 28], 13)
    showInfoWindow(overlay.getExtData(), overlay.getBounds?.()?.getCenter?.())
  }
  await loadRegionDetail(spatialUnit)
}

function closeInfoWindow() {
  if (activeInfoWindow.value) {
    activeInfoWindow.value.close()
    activeInfoWindow.value = null
  }
}

function popupHtml(p) {
  const hourActivity = p.hour_activity_count ?? p.night_vitality_score
  return `
    <div class="amap-popup">
      <button class="popup-close" type="button" aria-label="关闭">×</button>
      <div class="popup-title">${p.display_name || p.zone || p.Zone || `活动网格 ${p.spatial_unit}`}</div>
      <div class="popup-line"><span>${selectedHour.value.value === 'all' ? '活力分数' : '小时活动量'}</span><b>${Number(hourActivity || 0).toFixed(1)}</b></div>
      <div class="popup-line"><span>网格类型</span><b>${translateRegionType(p.region_type || 'no_activity')}</b></div>
      <div class="popup-line"><span>POI 多样性</span><b>${((Number(p.poi_diversity || 0)) * 100).toFixed(1)}%</b></div>
      <div class="popup-line"><span>枢纽修正</span><b>${Number(p.hub_penalty || 0).toFixed(1)}</b></div>
      <div class="popup-line"><span>活动起点 / 终点</span><b>${p.pickup_count || p.hour_pickup_count || 0} / ${p.dropoff_count || p.hour_dropoff_count || 0}</b></div>
    </div>
  `
}

function modelLabel(model) {
  const labels = {
    previous_hour_baseline: '上一小时参考',
    random_forest: '短时预测模型',
  }
  return labels[model] || model
}

function vitalityReason(region) {
  const score = Number(region?.night_vitality_score || 0)
  const weekend = Number(region?.weekend_boost || 0)
  const poi = Number(region?.poi_diversity || 0)
  if (score >= 80 && poi >= 0.3) return '夜间出租车活动强度高，同时周边功能吸引力明显，是稳定的夜间活动核心。'
  if (score >= 70 && weekend >= 1.5) return '平日已有较好活动基础，周末需求继续放大，说明它更接近夜间到达或出发热点。'
  if (region?.is_transport_hub || Number(region?.hub_penalty || 0) >= 5) return '活动量受到交通枢纽带动，活跃更偏通勤、换乘或长距离出发。'
  if (score >= 50) return '有持续夜间出租车活动，但活力来源相对混合，需要结合时段和周边功能继续判断。'
  return '夜间出租车活动较弱，更适合作为对照网格或低活力背景观察。'
}

function watchPoint(region) {
  const late = Number(region?.late_pickup_ratio || 0)
  const balance = Number(region?.inflow_outflow_balance || 0)
  if (late >= 0.4) return '凌晨时段仍有明显出发需求，适合关注夜间交通供给和安全服务。'
  if (balance >= 0.2) return '活动终点更突出，适合关注人流承接、末端交通和夜间到达体验。'
  if (balance <= -0.2) return '活动起点更突出，适合关注散场、返程和运力调度。'
  return '出发和到达相对均衡，适合观察整夜节奏变化。'
}

function comparisonText(region) {
  const score = Number(region?.night_vitality_score || 0)
  const total = Number(region?.total_activity || 0)
  const rank = regions.value.findIndex((item) => String(item.spatial_unit) === String(region?.spatial_unit)) + 1
  const rankText = rank > 0 ? `当前排名第 ${rank}。` : ''
  if (score >= 75) return `${rankText} 活力水平处于头部梯队，活动总量约 ${numberText(total)} 条。`
  if (score >= 45) return `${rankText} 活力水平处于中段，更适合和相邻网格一起看趋势。`
  return `${rankText} 活力水平偏低，主要价值是帮助识别城市夜间活动的边界。`
}

function showInfoWindow(properties, position) {
  if (!window.AMap || !map.value || !position) return
  closeInfoWindow()
  const content = document.createElement('div')
  content.innerHTML = popupHtml(properties)
  content.querySelector('.popup-close')?.addEventListener('click', (event) => {
    event.stopPropagation()
    closeInfoWindow()
  })
  const info = new window.AMap.InfoWindow({
    content,
    isCustom: true,
    offset: new window.AMap.Pixel(18, 0),
    anchor: 'middle-left',
  })
  info.open(map.value, position)
  activeInfoWindow.value = info
}

function polygonPaths(geometry) {
  const type = geometry?.type
  const coordinates = geometry?.coordinates || []
  if (type === 'Polygon') return coordinates.map((ring) => ring.map(([lng, lat]) => [lng, lat]))
  if (type === 'MultiPolygon') return coordinates.flatMap((polygon) => polygon.map((ring) => ring.map(([lng, lat]) => [lng, lat])))
  return []
}

function featureCenter(geometry) {
  const positions = []
  for (const path of polygonPaths(geometry)) {
    for (const point of path) positions.push(point)
  }
  if (!positions.length) return null
  const lng = positions.reduce((sum, point) => sum + Number(point[0]), 0) / positions.length
  const lat = positions.reduce((sum, point) => sum + Number(point[1]), 0) / positions.length
  return [lng, lat]
}

function createMarker(feature) {
  const p = feature.properties || {}
  const center = featureCenter(feature.geometry)
  if (!center) return null
  const marker = new window.AMap.Marker({
    position: center,
    content: '<div class="insight-marker top"><b>CORE</b></div>',
    offset: new window.AMap.Pixel(-20, -20),
    extData: p,
    zIndex: 140,
  })
  marker.on('click', async () => {
    highlightSpatialUnit(p.spatial_unit)
    showInfoWindow(p, center)
    await loadRegionDetail(p.spatial_unit)
  })
  return marker
}

function clearLayerGroup(groupRef) {
  if (map.value && groupRef.value.length) map.value.remove(groupRef.value)
  groupRef.value = []
}

function clearOverlays() {
  selectedOverlay.value = null
  if (map.value && overlays.value.length) map.value.remove(overlays.value)
  overlays.value = []
  clearLayerGroup(labelMarkers)
}

function resizeMap() {
  requestAnimationFrame(() => {
    map.value?.resize?.()
  })
}

async function toggleMapLabels() {
  showLabels.value = !showLabels.value
  await refreshMap()
}

function renderGeojson(geojson) {
  if (!window.AMap || !map.value) return
  clearOverlays()
  const nextOverlays = []
  const nextLabels = []
  const markerCandidates = []
  for (const feature of geojson.features || []) {
    const paths = polygonPaths(feature.geometry)
    if (!paths.length) continue
    if (!shouldRenderFeature(feature)) continue
    const polygon = new window.AMap.Polygon({
      path: paths,
      bubble: false,
      cursor: 'pointer',
      ...styleFeature(feature),
      extData: feature.properties || {},
    })
    polygon.on('mouseover', () => {
      if (isSelectedOverlay(polygon)) return
      polygon.setOptions({ strokeWeight: 1.4, strokeOpacity: 0.72, fillOpacity: 0.42 })
    })
    polygon.on('mouseout', () => {
      if (isSelectedOverlay(polygon)) return
      polygon.setOptions(styleFeature(feature))
    })
    polygon.on('click', async (event) => {
      highlightOverlay(polygon)
      showInfoWindow(feature.properties || {}, polygon.getBounds?.()?.getCenter?.() || event.lnglat)
      await loadRegionDetail(feature.properties?.spatial_unit)
    })
    nextOverlays.push(polygon)
    if (showLabels.value) {
      const marker = createMarker(feature)
      if (marker) markerCandidates.push({ marker, score: Number(feature.properties?.score_ratio || 0) })
    }
  }
  markerCandidates
    .sort((a, b) => b.score - a.score)
    .slice(0, 10)
    .forEach(({ marker }) => nextOverlays.push(marker))
  overlays.value = nextOverlays
  labelMarkers.value = nextLabels
  if (nextOverlays.length) {
    map.value.add(nextOverlays)
    if (nextLabels.length) map.value.add(nextLabels.slice(0, 14))
    if (selectedSpatialUnit.value) {
      const selected = nextOverlays.find((item) => String(item.getExtData?.()?.spatial_unit) === String(selectedSpatialUnit.value))
      if (selected) highlightOverlay(selected)
    }
    resizeMap()
  }
}

async function refreshMap() {
  if (!map.value || !amapReady.value) return
  const hour = selectedHour.value.value
  const geojson = await fetchJson(`/api/geojson?hour=${hour}`)
  currentGeojson.value = geojson
  renderGeojson(geojson)
}

function loadAmapScript() {
  return new Promise((resolve, reject) => {
    if (window.AMap) {
      resolve(window.AMap)
      return
    }
    if (!AMAP_KEY) {
      reject(new Error('请在 frontend/.env.local 配置 VITE_AMAP_KEY 后加载高德地图。'))
      return
    }
    if (AMAP_SECURITY_JSCODE) {
      window._AMapSecurityConfig = { securityJsCode: AMAP_SECURITY_JSCODE }
    }
    const script = document.createElement('script')
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${AMAP_KEY}&plugin=AMap.Scale,AMap.ToolBar,AMap.ControlBar,AMap.HawkEye`
    script.async = true
    script.onload = () => resolve(window.AMap)
    script.onerror = () => reject(new Error('高德地图脚本加载失败，请检查网络、Key 和安全密钥。'))
    document.head.appendChild(script)
  })
}

async function initMap() {
  try {
    await loadAmapScript()
    amapReady.value = true
    map.value = new window.AMap.Map('map', {
      viewMode: '2D',
      zoom: 11,
      center: [116.4074, 39.9042],
      mapStyle: 'amap://styles/darkblue',
      features: ['bg', 'road', 'building', 'point'],
    })
    map.value.addControl(new window.AMap.Scale())
    map.value.addControl(new window.AMap.ToolBar({ position: 'RB' }))
    map.value.on('click', closeInfoWindow)
    if (window.AMap.ControlBar) map.value.addControl(new window.AMap.ControlBar({ position: { right: '18px', top: '88px' } }))
    if (window.AMap.HawkEye) map.value.addControl(new window.AMap.HawkEye({ isOpen: false }))
    baseTileLayer.value = new window.AMap.TileLayer()
    trafficLayer.value = new window.AMap.TileLayer.Traffic({ autoRefresh: true, interval: 180 })
    syncMapLayers()
    resizeMap()
  } catch (error) {
    mapStatus.value = error.message
  }
}

function syncMapLayers() {
  if (!map.value || !window.AMap) return
  const layers = []
  if (baseTileLayer.value) layers.push(baseTileLayer.value)
  if (showTraffic.value && trafficLayer.value) layers.push(trafficLayer.value)
  map.value.setLayers(layers)
  map.value.setMapStyle('amap://styles/darkblue')
}

onMounted(async () => {
  window.addEventListener('resize', resizeMap)
  await initMap()
  try {
    const [summaryData, regionData, hourlyData, anomalyData, scoreMethodData, forecastMetricData, forecastData, reportData] = await Promise.all([
      fetchJson('/api/summary'),
      fetchJson('/api/regions'),
      fetchJson('/api/hourly'),
      fetchJson('/api/anomalies'),
      fetchJson('/api/score-methods'),
      fetchJson('/api/forecast-metrics'),
      fetchJson('/api/forecasts'),
      fetchJson('/api/report'),
    ])
    apiStatus.value = ''
    summary.value = summaryData
    regions.value = regionData
    hourly.value = hourlyData
    anomalies.value = anomalyData
    scoreMethods.value = scoreMethodData
    forecastMetrics.value = forecastMetricData
    forecasts.value = forecastData
    reportContent.value = reportData.content || ''
    await refreshMap()
  } catch (error) {
    apiStatus.value = error.message
  }
})

watch(activeView, (view) => {
  if (view !== 'map') return
  resizeMap()
  if (currentGeojson.value) renderGeojson(currentGeojson.value)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeMap)
})
</script>
