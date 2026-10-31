# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Unit tests for the transaction DTOs: TransactionDTO and its Buy/Sell subclasses,
AccountDTO and the BondTransactionDTO container (with its from_flat constructor).
"""
from datetime import date

import pytest
from pydantic import ValidationError

from intelligent_investor.dtos.bond_transaction import (
    AccountDTO,
    BondTransactionDTO,
    BuyTransactionDTO,
    SellTransactionDTO,
    TransactionDTO,
)
from intelligent_investor.services.bond_calculator_service import trade_commission

BUY_DATE = date(2026, 10, 29)


def _buy(venue: str = "mot", face_value: float = 10000.0) -> BuyTransactionDTO:
    return BuyTransactionDTO(venue=venue, date=BUY_DATE, price=99.0, face_value=face_value, commission_pct=0.10)


def test_buy_and_sell_are_transactions() -> None:
    sell = SellTransactionDTO(date=date(2027, 1, 1), price=100.0)
    assert isinstance(_buy(), TransactionDTO)
    assert isinstance(sell, TransactionDTO)


@pytest.mark.parametrize(
    "trade,expected_base",
    [
        (_buy("asta"), 10000.0),  # at auction: the nominal lot (cell A26)
        (_buy("mot"), 9900.0),  # on the MOT: the clean amount
        # sale: always the clean amount (cell A44)
        (SellTransactionDTO(date=date(2027, 1, 1), price=99.0, commission_pct=0.10), 9900.0),
    ],
    ids=["buy-asta", "buy-mot", "sell"],
)
def test_commission_base_depends_on_the_kind_of_trade(trade: TransactionDTO, expected_base: float) -> None:
    dry_amount = 9900.0
    assert trade.commission_base(dry_amount) == expected_base
    assert trade_commission(trade, dry_amount) == pytest.approx(expected_base * 0.10 / 100)


def test_buy_face_value_must_be_a_positive_multiple_of_100() -> None:
    with pytest.raises(ValidationError):
        _buy(face_value=150.0)


def test_price_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        SellTransactionDTO(date=date(2027, 1, 1), price=0.0)


def test_container_held_to_maturity_by_default() -> None:
    tx = BondTransactionDTO(bond_id=1, buy=_buy())
    assert tx.holds_to_maturity
    assert tx.quantity == 100
    assert tx.account == AccountDTO()


def test_sale_must_follow_the_purchase() -> None:
    with pytest.raises(ValidationError):
        BondTransactionDTO(bond_id=1, buy=_buy(), sell=SellTransactionDTO(date=BUY_DATE, price=100.0))


def test_from_flat_builds_the_nested_transaction() -> None:
    tx = BondTransactionDTO.from_flat(
        bond_id=7,
        purchase_venue="asta",
        purchase_date=BUY_DATE,
        purchase_price=99.0,
        face_value=5000.0,
        buy_commission_pct=0.15,
        sale_date=date(2027, 6, 1),
        sale_price=100.5,
        sell_commission_min=3.0,
        sell_commission_fixed=3.5,
        portfolio_losses=12.0,
        coupon_fee=2.0,
    )

    assert (tx.buy.venue, tx.buy.date, tx.buy.price, tx.buy.face_value, tx.buy.commission_pct) == (
        "asta", BUY_DATE, 99.0, 5000.0, 0.15
    )
    assert tx.sell is not None
    assert (tx.sell.date, tx.sell.price, tx.sell.commission_min, tx.sell.commission_fixed) == (
        date(2027, 6, 1), 100.5, 3.0, 3.5
    )
    assert tx.account == AccountDTO(portfolio_losses=12.0, coupon_fee=2.0)


def test_from_flat_needs_both_sale_date_and_price() -> None:
    with pytest.raises(ValueError):
        BondTransactionDTO.from_flat(
            bond_id=1, purchase_venue="mot", purchase_date=BUY_DATE, purchase_price=99.0, face_value=100.0,
            sale_date=date(2027, 1, 1),
        )
