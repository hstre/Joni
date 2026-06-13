"""Frugal execution - always the cheapest tier that still does the job.

This is the DESi idea applied to cost: route each task to the cheapest capable tier,
and *measure* adequacy rather than assume it. A task carries

  * a deterministic producer (tier 0, free) - rules, no model;
  * an adequacy predicate - the DESi measurement of "is this enough?";
  * optionally, escalation tiers - a ladder of models, cheapest first.

The executor tries tier 0; if DESi judges it adequate, it stops at zero cost. Only when
the free answer is measured inadequate does it climb the ladder, and only as far as the
budget (budget.py) allows. Which tier sufficed is recorded - that is how Joni "measures
what reichs".

By default the ladder is empty: nearly all autonomous work is structural and the
deterministic tier suffices, so Joni runs at €0. The model ladder (OpenRouter cheapest
-> DeepSeek) is wired only when keys are present, and used only on escalation.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass

from .budget import Budget


@dataclass
class ModelTierSpec:
    name: str
    cost_eur: float
    complete: Callable[[str, str], str]   # (system, user) -> text


@dataclass
class FrugalResult:
    output: str
    tier: str
    cost_eur: float
    escalations: int
    adequate: bool


class FrugalExecutor:
    def __init__(self, ladder: list[ModelTierSpec], budget: Budget, *, runs_per_week: int):
        self.ladder = ladder
        self.budget = budget
        self.runs_per_week = runs_per_week

    def run(
        self,
        *,
        deterministic: Callable[[], str],
        adequate: Callable[[str], bool],
        system: str = "",
        user: str = "",
    ) -> FrugalResult:
        # Tier 0: free, deterministic. Most tasks end here.
        out = deterministic()
        if adequate(out):
            return FrugalResult(out, "deterministic", 0.0, 0, True)

        # Escalate up the model ladder, cheapest first, within budget.
        escalations = 0
        for spec in self.ladder:
            if not self.budget.can_spend(spec.cost_eur, runs_per_week=self.runs_per_week):
                break
            escalations += 1
            try:
                out = spec.complete(system, user)
            except Exception:  # noqa: BLE001 - a failing tier is just skipped
                continue
            self.budget.charge(spec.cost_eur)
            if adequate(out):
                return FrugalResult(out, spec.name, spec.cost_eur, escalations, True)

        # Nothing adequate within budget: fall back to the free output, flagged.
        return FrugalResult(deterministic(), "deterministic", 0.0, escalations, False)


def build_ladder() -> list[ModelTierSpec]:
    """Cheapest-first model ladder, wired only if keys are present.

    OpenRouter gives access to very cheap models; DeepSeek is the stronger fallback.
    Costs are rough per-call EUR estimates used purely for budgeting/pacing.
    """
    ladder: list[ModelTierSpec] = []
    openrouter = os.getenv("OPENROUTER_API_KEY")
    deepseek = os.getenv("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY2")

    if openrouter:
        for model, cost in (
            ("meta-llama/llama-3.2-3b-instruct", 0.0005),
            ("google/gemini-flash-1.5", 0.001),
        ):
            ladder.append(ModelTierSpec(
                name=f"openrouter:{model}", cost_eur=cost,
                complete=_openai_complete(
                    "https://openrouter.ai/api/v1", openrouter, model),
            ))
    if deepseek:
        ladder.append(ModelTierSpec(
            name="deepseek-chat", cost_eur=0.002,
            complete=_openai_complete("https://api.deepseek.com", deepseek, "deepseek-chat"),
        ))
    return ladder


def _openai_complete(base_url: str, api_key: str, model: str) -> Callable[[str, str], str]:
    def complete(system: str, user: str) -> str:  # pragma: no cover - needs network+key
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model, temperature=0.2,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
        )
        return resp.choices[0].message.content or ""

    return complete
