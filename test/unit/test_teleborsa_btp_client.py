# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Unit tests for TeleborsaBtpClient.

Network calls are mocked so tests are pure, fast, and offline. Coverage focuses
on the fixed-rate filtering logic (the novel part of this client): plain parse
helpers, the nominal-rate resolution priority chain, and the end-to-end
fetch() row filtering (inflation-linked, step-coupon and zero-coupon BTPs must
never reach the "data" event).
"""

from datetime import date
from unittest.mock import MagicMock, patch

from intelligent_investor.clients import teleborsa_btp_client as mod
from intelligent_investor.clients.teleborsa_btp_client import TeleborsaBtpClient

# ------------------------------------------------------------------
# Parse helpers
# ------------------------------------------------------------------


def test_parse_price_handles_comma_and_percent() -> None:
    assert mod._parse_price("109,08") == 109.08
    assert mod._parse_price("2,1%") == 2.1
    assert mod._parse_price("not-a-number") is None


def test_parse_date_dd_mm_yyyy() -> None:
    assert mod._parse_date("01/08/2034") == date(2034, 8, 1)
    assert mod._parse_date("garbage") is None


# ------------------------------------------------------------------
# Name-based exclusion (inflation-linked BTPs mislabeled "Tasso Fisso")
# ------------------------------------------------------------------


def test_excludes_btpi_inflation_linked_by_prefix() -> None:
    assert mod._is_excluded_by_name("Btpi-15St35 2,35") is True


def test_excludes_btp_italia_by_substring() -> None:
    assert mod._is_excluded_by_name("Btp Italia Gn30 Eur") is True


def test_does_not_exclude_plain_fixed_rate_names() -> None:
    assert mod._is_excluded_by_name("Btp Fx 2.1% Aug27 Eur") is False
    assert mod._is_excluded_by_name("Btp-1Ag34 5") is False
    assert mod._is_excluded_by_name("Btp Green Fx 4.05% Oct37 Eur") is False


# ------------------------------------------------------------------
# Nominal rate parsed from the bond name (legacy / percent naming)
# ------------------------------------------------------------------


def test_parse_rate_from_name_percent_style() -> None:
    assert mod._parse_rate_from_name("Btp Fx 2.1% Aug27 Eur") == 2.1
    assert mod._parse_rate_from_name("Btpgreen 1,5%Ap45eur") == 1.5


def test_parse_rate_from_name_legacy_style_no_percent() -> None:
    assert mod._parse_rate_from_name("Btp-1Ag34 5") == 5.0
    assert mod._parse_rate_from_name("Btp-1Fb33 5,75") == 5.75


# ------------------------------------------------------------------
# Coupon frequency mapping
# ------------------------------------------------------------------


def test_parse_coupon_frequency_known_labels() -> None:
    assert mod._parse_coupon_frequency("Semestrale") == 2
    assert mod._parse_coupon_frequency("Annuale") == 1
    assert mod._parse_coupon_frequency("Trimestrale") == 4


def test_parse_coupon_frequency_unknown_or_missing_defaults_to_semiannual() -> None:
    assert mod._parse_coupon_frequency(None) == 2
    assert mod._parse_coupon_frequency("???") == 2


# ------------------------------------------------------------------
# Nominal rate resolution priority chain
# ------------------------------------------------------------------


def test_resolve_nominal_rate_prefers_cedola_annuale() -> None:
    detail = {"annual_rate": 2.1, "current_coupon": 999.0, "coupon_frequency": 2}
    assert mod._resolve_nominal_rate("Btp Fx 2.1% Aug27 Eur", detail) == 2.1


def test_resolve_nominal_rate_falls_back_to_cedola_in_corso_times_frequency() -> None:
    detail = {"current_coupon": 2.50, "coupon_frequency": 2}
    assert mod._resolve_nominal_rate("Btp-1Ag34 5", detail) == 5.0


def test_resolve_nominal_rate_falls_back_to_name_when_fields_missing() -> None:
    detail: dict = {}
    assert mod._resolve_nominal_rate("Btp Tf 0% Ag26 Eur", detail) == 0.0


# ------------------------------------------------------------------
# fetch(): end-to-end row filtering
# ------------------------------------------------------------------

_LIST_HTML = """
<table>
  <tr><th>Titolo</th></tr>
  <tr><td><a href="/obbligazioni-titoli-di-stato/btp-fx">Btp Fx 2.1% Aug27 Eur</a></td></tr>
  <tr><td><a href="/obbligazioni-titoli-di-stato/btpi-15">Btpi-15St35 2,35</a></td></tr>
  <tr><td><a href="/obbligazioni-titoli-di-stato/btp-valore">Btp Valore Gn27 Eur</a></td></tr>
  <tr><td><a href="/obbligazioni-titoli-di-stato/btp-italia">Btp Italia Gn30 Eur</a></td></tr>
</table>
"""


def _detail_html(
    name: str, isin: str, price: str, tipo_bond: str, extra_items: str = "", issue_price: str = "99,99"
) -> str:
    return f"""
    <div class="scheda-panel--header--title">{name}|ISIN: {isin} - Mercato: Milano - Tit. di Stato</div>
    <div class="scheda-panel--header--data--price">{price}</div>
    <div class="scheda-panel--header--data--change">+0,06%</div>
    <div class="scheda-panel--body--data--item">Cedola annuale|2,10%</div>
    <div class="scheda-panel--body--data--item">Frequenza cedola|Semestrale</div>
    <div class="scheda-panel--body--data--item">Scadenza|26/08/2027</div>
    <div class="scheda-panel--body--data--item">Data emissione|26/06/2025</div>
    <div class="scheda-panel--body--data--item">Prezzo emissione|{issue_price}</div>
    <div class="scheda-panel--body--data--item">Prezzo rimborso|100</div>
    <div class="scheda-panel--body--data--item">Tipo bond|{tipo_bond}</div>
    {extra_items}
    """


def _mock_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    resp.raise_for_status.return_value = None
    return resp


def test_fetch_yields_only_fixed_rate_data_events() -> None:
    fx_detail = _detail_html("Btp Fx 2.1% Aug27 Eur", "IT0005657330", "100,50", "Tasso Fisso")
    valore_detail = _detail_html("Btp Valore Gn27 Eur", "IT0005547408", "100,90", "Step Coupon")
    # Btp Italia is (incorrectly) labelled "Tasso Fisso" by Teleborsa but must
    # still be excluded via the name-based filter.
    italia_detail = _detail_html("Btp Italia Gn30 Eur", "IT0005497000", "100,10", "Tasso Fisso")

    responses_by_url = {
        mod._LIST_URL: _mock_response(_LIST_HTML),
        "https://www.teleborsa.it/obbligazioni-titoli-di-stato/btp-fx": _mock_response(fx_detail),
        "https://www.teleborsa.it/obbligazioni-titoli-di-stato/btp-valore": _mock_response(valore_detail),
        "https://www.teleborsa.it/obbligazioni-titoli-di-stato/btp-italia": _mock_response(italia_detail),
    }

    def _fake_get(url: str, headers=None, timeout=None):
        return responses_by_url[url]

    with patch.object(mod.requests, "get", side_effect=_fake_get) as mock_get:
        events = list(TeleborsaBtpClient().fetch())

    data_events = [e for e in events if e["type"] == "data"]
    assert len(data_events) == 1
    bond_dto, quote_dto = data_events[0]["payload"]
    assert bond_dto.isin == "IT0005657330"
    assert bond_dto.bond_type == "BTP"
    assert bond_dto.nominal_rate == 2.1
    assert bond_dto.coupon_frequency == 2
    assert quote_dto.last_price == 100.50

    # Btpi-15... must be filtered out by name before any detail request is made.
    requested_urls = [call.args[0] if call.args else call.kwargs["url"] for call in mock_get.call_args_list]
    assert not any("btpi-15" in u for u in requested_urls)

    assert events[-1]["type"] == "done"
    assert "1 BTP recuperati" in events[-1]["message"]


def test_fetch_falls_back_to_par_when_issue_price_is_missing() -> None:
    """Teleborsa reports 'Prezzo emissione: n.d.' for some reopened issues (e.g.
    IT0004889033): the quote must not be dropped just because of that — it falls
    back to the redemption price (par), which BondSyncService discards anyway
    for a bond already on file."""
    list_html = """
    <table>
      <tr><th>Titolo</th></tr>
      <tr><td><a href="/obbligazioni-titoli-di-stato/btp-tf-st28">Btp Tf 4,75% St28 Eur</a></td></tr>
    </table>
    """
    detail = _detail_html("Btp Tf 4,75% St28 Eur", "IT0004889033", "103,60", "Tasso Fisso", issue_price="n.d.")

    responses_by_url = {
        mod._LIST_URL: _mock_response(list_html),
        "https://www.teleborsa.it/obbligazioni-titoli-di-stato/btp-tf-st28": _mock_response(detail),
    }

    def _fake_get(url: str, headers=None, timeout=None):
        return responses_by_url[url]

    with patch.object(mod.requests, "get", side_effect=_fake_get):
        events = list(TeleborsaBtpClient().fetch())

    data_events = [e for e in events if e["type"] == "data"]
    assert len(data_events) == 1
    bond_dto, quote_dto = data_events[0]["payload"]
    assert bond_dto.isin == "IT0004889033"
    assert bond_dto.issue_price == bond_dto.redemption_price == 100.0
    assert quote_dto.last_price == 103.60
