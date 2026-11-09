from app.models import Offer
from app.services.offer_filter import OfferFilter


def offer(**kw) -> Offer:
    return Offer(**{"commodity": "power", "supplier": "Acme", "name": "Casa", "price_type": "fixed", **kw})


def test_filters_combine():
    plain, penalty, bonus, idx = offer(), offer(exit_terms="Onere"), offer(bonus_terms="Bonus 30 €"), offer(price_type="indexed")
    f = OfferFilter.from_args({"no_exit": "1", "type": "fixed"})
    assert [f.keep(o) for o in (plain, penalty, bonus, idx)] == [True, False, True, False]
    assert [OfferFilter.from_args({"bonus": "1"}).keep(o) for o in (plain, bonus)] == [False, True]
    assert OfferFilter.from_args({"q": " ACME "}).keep(plain) and not OfferFilter.from_args({"q": "zzz"}).keep(plain)
    assert OfferFilter.from_args({"type": "boh"}).price_type is None  # valore sconosciuto: nessun filtro


def test_bundle_bonus_on_one_half_is_enough_but_exit_charges_exclude():
    power, gas = offer(bonus_terms="Bonus"), offer(commodity="gas")
    assert OfferFilter(bonus=True).keep_bundle(power, gas)
    assert not OfferFilter(bonus=True).keep_bundle(offer(), gas)
    assert not OfferFilter(no_exit=True).keep_bundle(power, offer(commodity="gas", exit_terms="Onere"))
