from __future__ import annotations

from typing import Protocol

from nightsense.agents.schemas import AgentDict


class AnomalyExplanationProvider(Protocol):
    def explain(self, context: AgentDict) -> AgentDict:
        ...

