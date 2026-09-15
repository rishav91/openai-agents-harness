from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable

PromptFn = Callable[[str], str]


class BriefError(ValueError):
    pass


@dataclass(frozen=True)
class Brief:
    country: str
    exchange: str
    research_count: int
    portfolio_count: int
    budget_usd: float

    def to_dict(self) -> dict:
        return asdict(self)


def _clean(text: str) -> str:
    return text.strip()


def parse_country(raw: str) -> str:
    value = _clean(raw)
    if not value:
        raise BriefError("Country is required. Use a full name or ISO 3166-1 alpha-2 code.")
    return value


def parse_exchange(raw: str) -> str:
    value = _clean(raw)
    if not value:
        raise BriefError(
            "Exchange is required. Use an official name or code. "
            "It is not inferred from country."
        )
    return value


def parse_research_count(raw: str, max_research: int) -> int:
    value = _clean(raw)
    try:
        n = int(value)
    except ValueError as exc:
        raise BriefError("Research count must be an integer.") from exc
    if n < 1 or n > max_research:
        raise BriefError(f"Research count must be an integer from 1 to {max_research}.")
    return n


def parse_portfolio_count(raw: str, research_count: int) -> int:
    value = _clean(raw)
    try:
        n = int(value)
    except ValueError as exc:
        raise BriefError("Portfolio count must be an integer.") from exc
    if n < 1 or n > research_count:
        raise BriefError(
            f"Portfolio count must be an integer from 1 to research count ({research_count})."
        )
    return n


def parse_budget_usd(raw: str) -> float:
    value = _clean(raw).replace("$", "").replace(",", "")
    try:
        amount = float(value)
    except ValueError as exc:
        raise BriefError("Budget must be a positive USD amount.") from exc
    if amount <= 0:
        raise BriefError("Budget must be a positive USD amount.")
    return round(amount, 2)


def _ask(prompt: str, parser, input_fn: PromptFn):
    while True:
        try:
            return parser(input_fn(prompt))
        except BriefError as exc:
            print(f"  {exc}")


def collect_brief(
    max_research: int,
    input_fn: PromptFn = input,
) -> Brief:
    print(
        "Complete this brief. Research will not start until every field is valid.\n"
        "COST_BOUND_USD is taken from the environment, not from you.\n"
    )
    country = _ask("Country (full name or ISO code): ", parse_country, input_fn)
    exchange = _ask(
        "Stock exchange (official name or code, not inferred from country): ",
        parse_exchange,
        input_fn,
    )
    research_count = _ask(
        f"Research count (how many tickers get a subagent, 1–{max_research}): ",
        lambda raw: parse_research_count(raw, max_research),
        input_fn,
    )
    portfolio_count = _ask(
        "Portfolio count (how many names to fund; must be ≤ research count): ",
        lambda raw: parse_portfolio_count(raw, research_count),
        input_fn,
    )
    budget_usd = _ask("One-time investment budget (USD): ", parse_budget_usd, input_fn)
    return Brief(
        country=country,
        exchange=exchange,
        research_count=research_count,
        portfolio_count=portfolio_count,
        budget_usd=budget_usd,
    )
