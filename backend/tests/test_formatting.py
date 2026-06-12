from app.services.formatting import location_code, make_full_name, normalize_name, parse_cedulas


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
