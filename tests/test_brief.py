import pytest

from equity_harness.brief import (
    BriefError,
    collect_brief,
    parse_budget_usd,
    parse_country,
    parse_exchange,
    parse_portfolio_count,
    parse_research_count,
)


def test_rejects_empty_country_and_exchange():
    with pytest.raises(BriefError):
        parse_country("  ")
    with pytest.raises(BriefError):
        parse_exchange("")


def test_accepts_name_or_code():
    assert parse_country("IN") == "IN"
    assert parse_country("India") == "India"
    assert parse_exchange("NSE") == "NSE"


def test_research_and_portfolio_bounds():
    assert parse_research_count("5", max_research=12) == 5
    with pytest.raises(BriefError):
        parse_research_count("0", max_research=12)
    with pytest.raises(BriefError):
        parse_research_count("13", max_research=12)
    assert parse_portfolio_count("3", research_count=5) == 3
    with pytest.raises(BriefError):
        parse_portfolio_count("6", research_count=5)


def test_budget_usd_positive():
    assert parse_budget_usd("$1,000.50") == 1000.50
    with pytest.raises(BriefError):
        parse_budget_usd("0")
    with pytest.raises(BriefError):
        parse_budget_usd("-5")


def test_collect_brief_reasks_then_succeeds():
    answers = iter(
        [
            "",
            "India",
            "NSE",
            "20",
            "4",
            "6",
            "3",
            "10000",
        ]
    )
    brief = collect_brief(max_research=12, input_fn=lambda _: next(answers))
    assert brief.country == "India"
    assert brief.exchange == "NSE"
    assert brief.research_count == 4
    assert brief.portfolio_count == 3
    assert brief.budget_usd == 10000.0
