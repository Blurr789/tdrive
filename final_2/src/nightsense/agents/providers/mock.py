from __future__ import annotations

from nightsense.agents.schemas import AgentDict


class MockAnomalyProvider:
    provider = "mock"
    model = "mock-anomaly-agent"

    def explain(self, context: AgentDict) -> AgentDict:
        event = context.get("event", {})
        profile = context.get("region_profile", {})
        region_type = str(profile.get("region_type") or "unknown")
        zone = event.get("display_name") or event.get("zone") or event.get("spatial_unit")
        hour = event.get("hour")
        activity = event.get("activity_count")
        baseline = event.get("baseline_median")
        causes = []
        evidence = []

        if "nightlife" in region_type:
            causes.append("可能与夜生活消费或集中返程需求有关。")
            evidence.append("该区域类型被识别为 nightlife_core，且异常发生在夜间时段。")
        if profile.get("is_transport_hub"):
            causes.append("可能与交通枢纽到发客流有关。")
            evidence.append("该区域具有交通枢纽特征，长距离出行或换乘活动可能抬高需求。")
        if not causes:
            causes.append("可能是局部短时需求激增。")
            evidence.append("活动量明显偏离同区域同小时历史基线。")

        evidence.append(f"异常小时活动量为 {activity}，历史基线中位数为 {baseline}。")

        return {
            "provider": self.provider,
            "model": self.model,
            "summary": f"{zone} 在 {hour}:00 的异常更可能来自{causes[0].replace('可能与', '').replace('可能是', '')}",
            "likely_causes": causes,
            "evidence": evidence,
            "confidence": "medium",
            "recommended_checks": [
                "查看该区域前后小时是否同步升高。",
                "比较相邻区域是否出现类似异常。",
            ],
            "limitations": "该解释仅基于项目内历史出行数据和区域特征，不能确认具体真实事件。",
        }

