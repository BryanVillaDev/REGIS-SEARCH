import pytest

from app.services.name_matching import (
    candidate_tokens,
    confidence_label,
    match_state,
    parse_name_line,
    parse_name_rows,
    score_tokens,
    select_anchor_tokens,
    sorted_query_string,
    tokenize,
)


def test_tokenize_strips_accents_and_uppercases():
    assert tokenize("José  Peña ") == ["JOSE", "PENA"]


def test_parse_one_column_full_name():
    query = parse_name_line("PEREZ GOMEZ JUAN CARLOS")
    assert query.tokens == ["PEREZ", "GOMEZ", "JUAN", "CARLOS"]
    assert query.apellidos == ["PEREZ", "GOMEZ"]
    assert query.nombres == ["JUAN", "CARLOS"]


def test_parse_two_columns_apellidos_then_nombres():
    query = parse_name_line("PEREZ GOMEZ, JUAN CARLOS")
    assert query.apellidos == ["PEREZ", "GOMEZ"]
    assert query.nombres == ["JUAN", "CARLOS"]
    assert set(query.tokens) == {"PEREZ", "GOMEZ", "JUAN", "CARLOS"}


def test_parse_four_columns():
    query = parse_name_line("PEREZ|GOMEZ|JUAN|CARLOS")
    assert query.apellidos == ["PEREZ", "GOMEZ"]
    assert query.nombres == ["JUAN", "CARLOS"]


def test_parse_tab_separated_columns():
    query = parse_name_line("PEREZ\tGOMEZ\tJUAN\tCARLOS")
    assert query.tokens == ["PEREZ", "GOMEZ", "JUAN", "CARLOS"]


def test_parse_rows_dedupes_by_token_set_and_counts():
    rows, input_count = parse_name_rows(
        "PEREZ GOMEZ JUAN\nGOMEZ PEREZ JUAN\n\nMARIA LOPEZ"
    )
    # "PEREZ GOMEZ JUAN" y "GOMEZ PEREZ JUAN" tienen el mismo conjunto de tokens.
    assert len(rows) == 2
    assert input_count == 3


def test_parse_rows_requires_valid_input():
    with pytest.raises(ValueError):
        parse_name_rows("   \n  ,  \n")


def test_score_is_order_independent():
    target = candidate_tokens("PEREZ", "GOMEZ", "JUAN", "CARLOS")
    forward = score_tokens(["PEREZ", "GOMEZ", "JUAN", "CARLOS"], target)
    shuffled = score_tokens(["JUAN", "CARLOS", "PEREZ", "GOMEZ"], target)
    assert forward == shuffled == 100


def test_score_tolerates_typos():
    target = candidate_tokens("PEREZ", "GOMEZ", "JUAN", None)
    typo = score_tokens(["PERES", "GOMES", "JUAN"], target)
    assert typo >= 80


def test_score_ranks_closer_candidate_higher():
    query = ["PEREZ", "GOMEZ", "JUAN"]
    close = score_tokens(query, candidate_tokens("PEREZ", "GOMEZ", "JUAN", None))
    far = score_tokens(query, candidate_tokens("RAMIREZ", "DIAZ", "PEDRO", None))
    assert close > far


def test_score_penalizes_missing_and_extra_tokens():
    target = candidate_tokens("PEREZ", "GOMEZ", "JUAN", "CARLOS")
    partial = score_tokens(["PEREZ"], target)
    full = score_tokens(["PEREZ", "GOMEZ", "JUAN", "CARLOS"], target)
    assert partial < full == 100


def test_select_anchor_tokens_skips_particles_and_short_tokens():
    anchors = select_anchor_tokens(["DE", "LA", "PEREZ", "JO", "GOMEZ"])
    assert "DE" not in anchors
    assert "LA" not in anchors
    assert "JO" not in anchors
    assert set(anchors) == {"PEREZ", "GOMEZ"}


def test_sorted_query_string_is_order_independent():
    a = sorted_query_string(tokenize("JAIRO ALEXANDER VILLALOBOS GOMEZ"))
    b = sorted_query_string(tokenize("VILLALOBOS GOMEZ JAIRO ALEXANDER"))
    assert a == b == "ALEXANDER GOMEZ JAIRO VILLALOBOS"


def test_confidence_and_state_thresholds():
    assert confidence_label(95) == "alta"
    assert confidence_label(88) == "media"
    assert confidence_label(82) == "baja"
    assert confidence_label(60) == "muy baja"
    assert match_state(None) == "sin_coincidencia"
    assert match_state(95) == "encontrado"
    assert match_state(83) == "revisar"
    assert match_state(50) == "sin_coincidencia"
