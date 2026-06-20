from datetime import date

from app.services.formatting import (
    date_pin_combinations,
    location_code,
    make_full_name,
    normalize_name,
    parse_cedulas,
    parse_date,
)


def test_parse_cedulas_deduplicates_and_ignores_empty_values():
    cedulas, input_count = parse_cedulas(" 123, 456\n123; abc-789 ")

    assert cedulas == [123, 456, 789]
    assert input_count >= 4


def test_parse_cedulas_requires_valid_values():
    try:
        parse_cedulas("abc, ---")
    except ValueError as exc:
        assert "cedula valida" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_normalize_name_uppercases_and_collapses_spaces():
    assert normalize_name("  juan   perez ") == "JUAN PEREZ"


def test_make_full_name_skips_missing_parts():
    assert make_full_name("JUAN", None, "PEREZ") == "JUAN PEREZ"


def test_location_code_handles_compound_lug_ids():
    assert location_code(11001) == "11001"
    assert location_code(11001000) == "11001"


def test_date_pin_combinations_are_always_four_digits():
    combos = date_pin_combinations(date(1980, 4, 23))

    assert combos == {
        "anio": "1980",
        "dia_mes": "2304",
        "mes_dia": "0423",
        "dia_anio": "2380",
        "anio_dia": "8023",
        "mes_anio": "0480",
        "anio_mes": "8004",
    }
    assert all(len(value) == 4 and value.isdigit() for value in combos.values())


def test_date_pin_combinations_accepts_iso_strings():
    assert date_pin_combinations("1980-04-23") == date_pin_combinations(date(1980, 4, 23))


def test_date_pin_combinations_empty_for_invalid_input():
    assert date_pin_combinations(None) == {}
    assert date_pin_combinations("") == {}
    assert date_pin_combinations("no-date") == {}


def test_parse_date_handles_iso_and_passthrough():
    assert parse_date("1995-12-31") == date(1995, 12, 31)
    assert parse_date(date(1995, 12, 31)) == date(1995, 12, 31)
    assert parse_date(None) is None
