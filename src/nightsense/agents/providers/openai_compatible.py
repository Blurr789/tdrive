from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from nightsense.agents.schemas import AgentDict


class OpenAICompatibleAnomalyProvider:
    provider = "deepseek"

    def __init__(
        self,
        api_key: str,
        model: str,
        api_base: str = "https://api.deepseek.com",
        timeout: int = 45,
    ):
        self.api_key = api_key
        self.model = model
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout

    @property
    def endpoint(self) -> str:
        if self.api_base.endswith("/chat/completions"):
            return self.api_base
        return f"{self.api_base}/chat/completions"

    def explain(self, context: AgentDict) -> AgentDict:
        messages = [
            {
                "role": "system",
                "content": (
                    "你是城市夜间出行异常分析 Agent。只能基于用户提供的项目数据进行分析，"
                    "不得编造新闻、天气、演唱会、事故或任何外部事实。"
                    "请输出严格 JSON，字段包括 summary, likely_causes, evidence, confidence, "
                    "recommended_checks, limitations。"
                ),
            },
            {
                "role": "user",
                "content": (
                    "请解释以下夜间出行异常事件。要求：中文；给出可能原因、数据证据和建议核查项；"
                    "如果数据不足，请说明不确定。\n\n"
                    f"{json.dumps(context, ensure_ascii=False)}"
                ),
            },
        ]
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        request = Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"LLM request failed: {exc.code} {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"LLM request failed: {exc.reason}") from exc

        content = data["choices"][0]["message"]["content"]
        result = self._parse_json_content(content)
        result["provider"] = self.provider
        result["model"] = self.model
        return result

    def _parse_json_content(self, content: str) -> AgentDict:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                return json.loads(content[start : end + 1])
            raise


def provider_from_env():
    provider = os.environ.get("LLM_PROVIDER", "mock").lower()
    if provider not in {"deepseek", "openai-compatible", "openai_compatible"}:
        from nightsense.agents.providers.mock import MockAnomalyProvider

        return MockAnomalyProvider()

    api_key = os.environ.get("LLM_API_KEY", "")
    if not api_key:
        raise RuntimeError("LLM_API_KEY is required when LLM_PROVIDER=deepseek")
    model = os.environ.get("LLM_MODEL", "deepseek-v4")
    api_base = os.environ.get("LLM_API_BASE", "https://api.deepseek.com")
    return OpenAICompatibleAnomalyProvider(api_key=api_key, model=model, api_base=api_base)

