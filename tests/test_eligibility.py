from app.models import Offer
from app.services.pricing import Location, available_in


def offer(**kw) -> Offer:
    return Offer(**{"commodity": "power", "supplier": "enel.it", "name": "X", "price_type": "fixed", "price": 0.1, **kw})


HOME = Location(resident=True, power_kw=3.0, supplier="Enel Energia")


def test_power_and_consumption_ranges():
    assert available_in(offer(power_min=1.5, power_max=6), HOME)
    assert not available_in(offer(power_min=4.5), HOME) and not available_in(offer(power_max=2), HOME)
    assert not available_in(offer(consumption_max=1000), HOME, annual=2500) and available_in(offer(consumption_max=1000), HOME)
    assert available_in(offer(power_min=10), Location(power_kw=None))  # potenza sconosciuta: nessuna esclusione


def test_residency():
    assert available_in(offer(residency="resident"), HOME) and not available_in(offer(residency="non_resident"), HOME)
    assert available_in(offer(residency="non_resident"), Location(resident=False))


def test_new_customers_only_excludes_own_supplier():
    only_new = offer(conditions="Offerta riservata ai nuovi clienti.")
    assert not available_in(only_new, HOME)  # stesso fornitore («enel.it» = «Enel Energia»)
    assert available_in(offer(supplier="altro.it", conditions="Solo nuovi clienti"), HOME)
    assert available_in(only_new, Location())  # fornitore attuale sconosciuto


def test_activation_cases_from_the_official_codes():
    assert available_in(offer(valid_for="always"), HOME) and available_in(offer(valid_for="switch,transfer"), Location(supplier="Altro"))
    assert not available_in(offer(valid_for="first,transfer"), HOME)  # non vale per chi cambia fornitore
    assert not available_in(offer(valid_for="switch"), HOME)  # solo cambiando fornitore, ma il fornitore è lo stesso
    assert available_in(offer(valid_for="switch", supplier="altro.it"), HOME)
