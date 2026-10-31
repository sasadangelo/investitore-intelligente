# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Parametrised unit tests for BondCalculatorService on BOTs.

These cases were written for the former BotCalculatorService and now run against the
unified calculator: they are the parity check required by docs/roadmap-btp.md (Fase 8).

Each JSON file in test/unit/fixtures/ whose name starts with
"bot_calculator_case_" describes one complete test scenario:

  {
    "description": "human-readable label",
    "bond":        { ...fields for BondDTO... },
    "transaction": { ...fields for BondTransactionDTO... },
    "expected":    {
      "quantity": ...,
      "purchase":      { dry_amount, commission, fixed_commission,
                         unit_discount, discount_tax, total_paid },
      "capital_gain":  { theoretical_purchase_price, theoretical_sale_price,
                         load_price, unload_price, unit_gain_loss,
                         total_gain_loss, tds_reduction,
                         capital_gain_tax, remaining_loss }
                       | null,
      "sale":          { dry_amount, commission, fixed_commission,
                         discount_tax, total_received },
      "stamp_duty":    { holding_periods, estimated_duty },
      "summary":       { gross_gain, net_gain_before_duty, net_gain,
                         simple_gross_yield, compound_gross_yield,
                         simple_net_yield_before_duty,
                         compound_net_yield_before_duty,
                         simple_net_yield, compound_net_yield }
    }
  }

To add a new test scenario just drop another JSON file in the fixtures/
directory — no Python changes needed.
"""

import json
from datetime import date
from pathlib import Path

import pytest

from intelligent_investor.dtos.bond import BondDTO
from intelligent_investor.dtos.bond_transaction import BondTransactionDTO
from intelligent_investor.services.bond_calculator_service import BondCalculatorService

# ---------------------------------------------------------------------------
# Fixtures directory
# ---------------------------------------------------------------------------

_FIXTURES_DIR = Path(__file__).parent / "fixtures"

# ---------------------------------------------------------------------------
# Tolerances
# ---------------------------------------------------------------------------

_ABS_EURO = 1e-2      # ± 0.01 € — matches the 2-decimal precision of the UI
_ABS_PRICE = 1e-4     # ± 0.0001 for per-unit prices
_ABS_YIELD = 1e-2     # ± 0.01 percentage points (yields stored as %, e.g. 3.396)


# ---------------------------------------------------------------------------
# Parametrisation: collect all JSON fixture files at import time
# ---------------------------------------------------------------------------

def _load_cases() -> list[tuple[str, dict]]:
    """Return [(test_id, case_dict), ...] for every fixture file."""
    cases = []
    for path in sorted(_FIXTURES_DIR.glob("bot_calculator_case_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        test_id = path.stem          # e.g. "bot_calculator_case_001"
        cases.append((test_id, data))
    return cases


_CASES = _load_cases()


# ---------------------------------------------------------------------------
# Helper: build DTOs from the raw JSON dicts
# ---------------------------------------------------------------------------

def _make_bond(raw: dict) -> BondDTO:
    return BondDTO(
        name=raw["name"],
        isin=raw["isin"],
        bond_type=raw["bond_type"],
        issue_date=date.fromisoformat(raw["issue_date"]),
        maturity_date=date.fromisoformat(raw["maturity_date"]),
        issue_price=raw["issue_price"],
        redemption_price=raw.get("redemption_price", 100.0),
        tax_rate=raw.get("tax_rate", 12.5),
    )


def _make_transaction(raw: dict) -> BondTransactionDTO:
    return BondTransactionDTO.from_flat(
        bond_id=raw.get("bond_id", 0),
        purchase_venue=raw["purchase_venue"],
        purchase_date=date.fromisoformat(raw["purchase_date"]),
        purchase_price=raw["purchase_price"],
        face_value=raw["face_value"],
        buy_commission_pct=raw.get("buy_commission_pct", 0.0),
        buy_commission_min=raw.get("buy_commission_min", 0.0),
        buy_commission_max=raw.get("buy_commission_max"),          # None = no cap
        buy_commission_fixed=raw.get("buy_commission_fixed", 0.0),
        sale_date=date.fromisoformat(raw["sale_date"]) if raw.get("sale_date") else None,
        sale_price=raw.get("sale_price"),
        sell_commission_pct=raw.get("sell_commission_pct", 0.0),
        sell_commission_min=raw.get("sell_commission_min", 0.0),
        sell_commission_max=raw.get("sell_commission_max"),
        sell_commission_fixed=raw.get("sell_commission_fixed", 0.0),
        stamp_duty_period=raw.get("stamp_duty_period", "quarterly"),
        portfolio_losses=raw.get("portfolio_losses", 0.0),
    )


# ---------------------------------------------------------------------------
# Parametrised test
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("test_id,case", _CASES, ids=[c[0] for c in _CASES])
def test_bot_calculator(test_id: str, case: dict) -> None:
    """
    Run BondCalculatorService.calculate() for the given case and assert
    every expected field within tolerance.
    """
    bond = _make_bond(case["bond"])
    transaction = _make_transaction(case["transaction"])
    expected = case["expected"]

    result = BondCalculatorService().calculate(transaction, bond)

    # -- quantity ------------------------------------------------------------
    assert result.quantity == pytest.approx(expected["quantity"], abs=_ABS_EURO), \
        f"[{test_id}] quantity"

    # -- purchase ------------------------------------------------------------
    exp_p = expected["purchase"]
    assert result.purchase.dry_amount == pytest.approx(exp_p["dry_amount"], abs=_ABS_EURO), \
        f"[{test_id}] purchase.dry_amount"
    assert result.purchase.commission == pytest.approx(exp_p["commission"], abs=_ABS_EURO), \
        f"[{test_id}] purchase.commission"
    assert result.purchase.fixed_commission == pytest.approx(exp_p["fixed_commission"], abs=_ABS_EURO), \
        f"[{test_id}] purchase.fixed_commission"
    assert result.purchase.unit_discount == pytest.approx(exp_p["unit_discount"], abs=_ABS_PRICE), \
        f"[{test_id}] purchase.unit_discount"
    assert result.purchase.discount_tax == pytest.approx(exp_p["discount_tax"], abs=_ABS_EURO), \
        f"[{test_id}] purchase.discount_tax"
    assert result.purchase.total_paid == pytest.approx(exp_p["total_paid"], abs=_ABS_EURO), \
        f"[{test_id}] purchase.total_paid"

    # -- capital_gain --------------------------------------------------------
    # Present for every purchase, auction included (cells K26/K38 do not look at the venue)
    exp_cg = expected["capital_gain"]
    assert result.capital_gain.theoretical_purchase_price == pytest.approx(
        exp_cg["theoretical_purchase_price"], abs=_ABS_PRICE
    ), f"[{test_id}] capital_gain.theoretical_purchase_price"
    assert result.capital_gain.theoretical_sale_price == pytest.approx(
        exp_cg["theoretical_sale_price"], abs=_ABS_PRICE
    ), f"[{test_id}] capital_gain.theoretical_sale_price"
    assert result.capital_gain.load_price == pytest.approx(
        exp_cg["load_price"], abs=_ABS_PRICE
    ), f"[{test_id}] capital_gain.load_price"
    assert result.capital_gain.unload_price == pytest.approx(
        exp_cg["unload_price"], abs=_ABS_PRICE
    ), f"[{test_id}] capital_gain.unload_price"
    assert result.capital_gain.unit_gain_loss == pytest.approx(
        exp_cg["unit_gain_loss"], abs=_ABS_PRICE
    ), f"[{test_id}] capital_gain.unit_gain_loss"
    assert result.capital_gain.total_gain_loss == pytest.approx(
        exp_cg["total_gain_loss"], abs=_ABS_EURO
    ), f"[{test_id}] capital_gain.total_gain_loss"
    assert result.capital_gain.tds_reduction == pytest.approx(
        exp_cg["tds_reduction"], abs=_ABS_EURO
    ), f"[{test_id}] capital_gain.tds_reduction"
    assert result.capital_gain.capital_gain_tax == pytest.approx(
        exp_cg["capital_gain_tax"], abs=_ABS_EURO
    ), f"[{test_id}] capital_gain.capital_gain_tax"
    assert result.capital_gain.remaining_loss == pytest.approx(
        exp_cg["remaining_loss"], abs=_ABS_EURO
    ), f"[{test_id}] capital_gain.remaining_loss"

    # -- sale ----------------------------------------------------------------
    exp_s = expected["sale"]
    assert result.sale.dry_amount == pytest.approx(exp_s["dry_amount"], abs=_ABS_EURO), \
        f"[{test_id}] sale.dry_amount"
    assert result.sale.commission == pytest.approx(exp_s["commission"], abs=_ABS_EURO), \
        f"[{test_id}] sale.commission"
    assert result.sale.fixed_commission == pytest.approx(exp_s["fixed_commission"], abs=_ABS_EURO), \
        f"[{test_id}] sale.fixed_commission"
    assert result.sale.discount_tax == pytest.approx(exp_s["discount_tax"], abs=_ABS_EURO), \
        f"[{test_id}] sale.discount_tax"
    assert result.sale.total_received == pytest.approx(exp_s["total_received"], abs=_ABS_EURO), \
        f"[{test_id}] sale.total_received"

    # -- stamp_duty ----------------------------------------------------------
    exp_sd = expected["stamp_duty"]
    assert result.stamp_duty.holding_periods == exp_sd["holding_periods"], \
        f"[{test_id}] stamp_duty.holding_periods"
    assert result.stamp_duty.estimated_duty == pytest.approx(exp_sd["estimated_duty"], abs=_ABS_EURO), \
        f"[{test_id}] stamp_duty.estimated_duty"

    # -- summary -------------------------------------------------------------
    exp_su = expected["summary"]
    assert result.summary.gross_gain == pytest.approx(exp_su["gross_gain"], abs=_ABS_EURO), \
        f"[{test_id}] summary.gross_gain"
    assert result.summary.net_gain_before_duty == pytest.approx(exp_su["net_gain_before_duty"], abs=_ABS_EURO), \
        f"[{test_id}] summary.net_gain_before_duty"
    assert result.summary.net_gain == pytest.approx(exp_su["net_gain"], abs=_ABS_EURO), \
        f"[{test_id}] summary.net_gain"
    assert result.summary.simple_gross_yield == pytest.approx(
        exp_su["simple_gross_yield"], abs=_ABS_YIELD
    ), f"[{test_id}] summary.simple_gross_yield"
    assert result.summary.compound_gross_yield == pytest.approx(
        exp_su["compound_gross_yield"], abs=_ABS_YIELD
    ), f"[{test_id}] summary.compound_gross_yield"
    assert result.summary.simple_net_yield_before_duty == pytest.approx(
        exp_su["simple_net_yield_before_duty"], abs=_ABS_YIELD
    ), f"[{test_id}] summary.simple_net_yield_before_duty"
    assert result.summary.compound_net_yield_before_duty == pytest.approx(
        exp_su["compound_net_yield_before_duty"], abs=_ABS_YIELD
    ), f"[{test_id}] summary.compound_net_yield_before_duty"
    assert result.summary.simple_net_yield == pytest.approx(
        exp_su["simple_net_yield"], abs=_ABS_YIELD
    ), f"[{test_id}] summary.simple_net_yield"
    assert result.summary.compound_net_yield == pytest.approx(
        exp_su["compound_net_yield"], abs=_ABS_YIELD
    ), f"[{test_id}] summary.compound_net_yield"


# ---------------------------------------------------------------------------
# Fase 9 — zainetto and maturity commissions (not covered by the JSON cases,
# which all have an empty zainetto and no sale commission at maturity)
# ---------------------------------------------------------------------------

_BOT = BondDTO(
    name="BOT Zc Gn26 A EUR",
    isin="IT0000000009",
    bond_type="BOT",
    issue_date=date(2025, 6, 13),
    maturity_date=date(2026, 6, 12),
    issue_price=97.5,
)


def _bot_held_to_maturity(portfolio_losses: float = 0.0, **sell_commissions: float) -> BondTransactionDTO:
    # Bought below the theoretical price (~98.75 on 2025-12-12): capital gain at maturity
    return BondTransactionDTO.from_flat(
        bond_id=0,
        purchase_venue="mot",
        purchase_date=date(2025, 12, 12),
        purchase_price=98.0,
        face_value=10000.0,
        portfolio_losses=portfolio_losses,
        **sell_commissions,
    )


@pytest.mark.parametrize("portfolio_losses", [0.0, 10.0, 1000.0])
def test_bot_zainetto_reduces_capital_gain_tax(portfolio_losses: float) -> None:
    """Reference spreadsheet K49–K53: the zainetto offsets the gain reduced to 48.08%
    (12.5% / 26%); only what is left is taxed, brought back to the full gain."""
    cg = BondCalculatorService().calculate(_bot_held_to_maturity(portfolio_losses), _BOT).capital_gain
    assert cg is not None and cg.total_gain_loss > 0

    factor = 12.5 / 26
    reduced_gain = cg.total_gain_loss * factor
    assert cg.tds_reduction == pytest.approx(reduced_gain)
    assert cg.capital_gain_tax == pytest.approx(max(0.0, reduced_gain - portfolio_losses) / factor * 0.125)
    assert cg.remaining_loss == pytest.approx(max(0.0, portfolio_losses - reduced_gain))


def test_bot_no_sale_commission_at_maturity() -> None:
    """Reference spreadsheet K36: redemption at maturity is not a sale, so sale
    commissions passed with the transaction are ignored."""
    plain = BondCalculatorService().calculate(_bot_held_to_maturity(), _BOT)
    with_commissions = BondCalculatorService().calculate(
        _bot_held_to_maturity(sell_commission_pct=0.19, sell_commission_min=2.95, sell_commission_fixed=1.5), _BOT
    )
    assert with_commissions.sale.commission == 0.0
    assert with_commissions.sale.fixed_commission == 0.0
    assert with_commissions.sale.total_received == plain.sale.total_received
