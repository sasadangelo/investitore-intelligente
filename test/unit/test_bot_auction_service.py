# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from collections.abc import Generator
from datetime import date, timedelta
from typing import Literal

import pytest
import sqlalchemy as sa

from intelligent_investor.dtos.bot_auction import AuctionOfferingDTO, BotAuctionDTO
from intelligent_investor.models.bot_auction import AuctionOfferingDAO, BotAuctionDAO
from intelligent_investor.services import BotAuctionService

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _id(dto: BotAuctionDTO) -> int:
    """Assert and return a saved DTO's id as non-None int."""
    assert dto.id is not None
    return dto.id


def _make_auction(
    period: Literal["mid_month", "end_month"] = "mid_month",
    duration_type: Literal["annual", "semiannual", "tbd"] = "annual",
    settlement_date: date | None = None,
) -> BotAuctionDTO:
    today: date = date.today()
    settlement: date = settlement_date or today + timedelta(days=5)
    maturity: date | None = None if duration_type == "tbd" else settlement + timedelta(days=365)
    return BotAuctionDTO(
        period=period,
        duration_type=duration_type,
        announcement_date=settlement - timedelta(days=3),
        submission_deadline=settlement - timedelta(days=2),
        auction_date=settlement - timedelta(days=1),
        settlement_date=settlement,
        maturity_date=maturity,
    )


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture(scope="module")
def service() -> BotAuctionService:
    return BotAuctionService()


@pytest.fixture(autouse=True)
def clean_auctions(
    test_engine: sa.Engine,
    service: BotAuctionService,
) -> Generator[None, None, None]:
    """Wipe the auction tables before and after every test."""
    with test_engine.begin() as conn:
        _ = conn.execute(sa.delete(table=AuctionOfferingDAO))
        _ = conn.execute(sa.delete(table=BotAuctionDAO))
    yield
    with test_engine.begin() as conn:
        _ = conn.execute(sa.delete(table=AuctionOfferingDAO))
        _ = conn.execute(sa.delete(table=BotAuctionDAO))


# ------------------------------------------------------------------
# create
# ------------------------------------------------------------------


def test_create_returns_dto_with_id(service: BotAuctionService) -> None:
    auction: BotAuctionDTO = _make_auction()
    saved: BotAuctionDTO = service.create(auction)
    assert saved.id is not None
    assert saved.settlement_date == auction.settlement_date


# ------------------------------------------------------------------
# get_by_id
# ------------------------------------------------------------------


def test_get_by_id_found(service: BotAuctionService) -> None:
    saved: BotAuctionDTO = service.create(auction=_make_auction())
    fetched: BotAuctionDTO | None = service.get_by_id(auction_id=_id(dto=saved))
    assert fetched is not None
    assert fetched.settlement_date == saved.settlement_date


def test_get_by_id_not_found(service: BotAuctionService) -> None:
    assert service.get_by_id(auction_id=99999) is None


# ------------------------------------------------------------------
# list_all
# ------------------------------------------------------------------


def test_list_all_empty(service: BotAuctionService) -> None:
    assert service.list_all() == []


def test_list_all_returns_all_ordered_by_settlement_date(service: BotAuctionService) -> None:
    later: BotAuctionDTO = service.create(auction=_make_auction(settlement_date=date.today() + timedelta(days=20)))
    earlier: BotAuctionDTO = service.create(
        auction=_make_auction(period="end_month", settlement_date=date.today() + timedelta(days=10))
    )

    auctions: list[BotAuctionDTO] = service.list_all()

    assert [auction.id for auction in auctions] == [_id(dto=earlier), _id(dto=later)]


# ------------------------------------------------------------------
# update
# ------------------------------------------------------------------


def test_update_changes_fields(service: BotAuctionService) -> None:
    saved: BotAuctionDTO = service.create(auction=_make_auction())
    updated_dto: BotAuctionDTO = saved.model_copy(
        update={
            "duration_type": "semiannual",
            "maturity_date": saved.settlement_date + timedelta(days=182),
        }
    )

    result: BotAuctionDTO = service.update(auction=updated_dto)

    assert result.duration_type == "semiannual"
    assert result.maturity_date == saved.settlement_date + timedelta(days=182)


def test_update_without_id_raises(service: BotAuctionService) -> None:
    with pytest.raises(ValueError):
        service.update(auction=_make_auction())


def test_update_nonexistent_raises(service: BotAuctionService) -> None:
    auction: BotAuctionDTO = _make_auction().model_copy(update={"id": 99999})
    with pytest.raises(ValueError):
        service.update(auction)


# ------------------------------------------------------------------
# delete
# ------------------------------------------------------------------


def test_delete_existing_returns_true(service: BotAuctionService) -> None:
    saved: BotAuctionDTO = service.create(auction=_make_auction())
    assert service.delete(auction_id=_id(saved)) is True
    assert service.get_by_id(auction_id=_id(dto=saved)) is None


def test_delete_nonexistent_returns_false(service: BotAuctionService) -> None:
    assert service.delete(auction_id=99999) is False


# ------------------------------------------------------------------
# list_upcoming
# ------------------------------------------------------------------


def test_list_upcoming_returns_only_future_auctions_ordered(service: BotAuctionService) -> None:
    service.create(auction=_make_auction(settlement_date=date.today() - timedelta(days=1)))
    first: BotAuctionDTO = service.create(auction=_make_auction(settlement_date=date.today()))
    second: BotAuctionDTO = service.create(auction=_make_auction(settlement_date=date.today() + timedelta(days=7)))

    auctions: list[BotAuctionDTO] = service.list_upcoming()

    assert [auction.id for auction in auctions] == [_id(dto=first), _id(dto=second)]


# ------------------------------------------------------------------
# BTP auctions (sessions) and the bonds offered
# ------------------------------------------------------------------


def _btp_auction(session: Literal["medium_long", "short"] = "medium_long") -> BotAuctionDTO:
    return _make_auction(
        period="mid_month" if session == "medium_long" else "end_month", duration_type="tbd"
    ).model_copy(update={"session": session})


def test_existing_auctions_default_to_the_bot_session(service: BotAuctionService) -> None:
    assert service.create(_make_auction()).session == "bot"


def test_btp_auction_saved_with_its_session(service: BotAuctionService) -> None:
    saved = service.create(_btp_auction("short"))
    assert saved.session == "short"
    assert saved.period == "end_month"
    assert saved.maturity_date is None


@pytest.mark.parametrize(
    "session,update",
    [
        ("medium_long", {"duration_type": "annual"}),  # a BTP auction has no duration of its own
        ("short", {"period": "mid_month"}),  # BTP Short auctions are always at month end
    ],
)
def test_btp_auction_rejects_bot_only_values(session: Literal["medium_long", "short"], update: dict) -> None:
    data = _btp_auction(session).model_dump()
    data.update(update)
    if update.get("duration_type") == "annual":
        data["maturity_date"] = data["settlement_date"] + timedelta(days=365)
    with pytest.raises(ValueError):
        BotAuctionDTO(**data)


def test_offerings_added_listed_and_deleted(service: BotAuctionService) -> None:
    auction_id = _id(service.create(_btp_auction()))
    later = service.add_offering(
        AuctionOfferingDTO(
            auction_id=auction_id, isin=" it0005584849 ", name="BTP Lug29", maturity_date=date(2029, 7, 1)
        )
    )
    service.add_offering(AuctionOfferingDTO(auction_id=auction_id, isin="IT0005000001", name="BTP nuovo"))
    service.add_offering(
        AuctionOfferingDTO(
            auction_id=auction_id, isin="IT0005000002", name="BTP Feb28", maturity_date=date(2028, 2, 28)
        )
    )

    offerings = service.list_offerings([auction_id])[auction_id]

    assert later.isin == "IT0005584849"  # trimmed and upper-cased
    # By maturity, unknown maturity last
    assert [o.name for o in offerings] == ["BTP Feb28", "BTP Lug29", "BTP nuovo"]
    assert service.delete_offering(_id_offering(later)) is True
    assert len(service.list_offerings([auction_id])[auction_id]) == 2


def _id_offering(dto: AuctionOfferingDTO) -> int:
    assert dto.id is not None
    return dto.id


def test_deleting_an_auction_deletes_its_offerings(service: BotAuctionService) -> None:
    auction_id = _id(service.create(_btp_auction()))
    service.add_offering(AuctionOfferingDTO(auction_id=auction_id, isin="IT0005584849", name="BTP Lug29"))

    assert service.delete(auction_id) is True
    assert service.list_offerings([auction_id]) == {}


def test_offering_needs_a_12_character_isin() -> None:
    with pytest.raises(ValueError):
        AuctionOfferingDTO(auction_id=1, isin="IT00055", name="BTP")


def test_medium_long_auction_also_at_month_end(service: BotAuctionService) -> None:
    # MEF calendar 2026: medium-long auctions on 12/11 and again on 27/11
    saved = service.create(_btp_auction("medium_long").model_copy(update={"period": "end_month"}))
    assert (saved.session, saved.period) == ("medium_long", "end_month")
