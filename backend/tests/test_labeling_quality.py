from __future__ import annotations

import json
from pathlib import Path

from app.services.labeling_service import (
    _has_repeated_digit_run,
    _has_repeated_letter_run,
    _quality_blockers_for_text,
    _quality_tokens,
)


FIXTURES = Path(__file__).resolve().parent / "fixtures"
LABELLED = Path(__file__).resolve().parents[2] / "labelled_questions.json"


def _load_ipa_document() -> str:
    data = json.loads(LABELLED.read_text(encoding="utf-8"))
    return next(
        entry["ozelge_metni"]
        for entry in data
        if "IPA II ÇERÇEVE ANLAŞMASI" in entry["ozelge_metni"]
    )


def test_legal_answer_with_form_dot_placeholders_is_allowed() -> None:
    document = _load_ipa_document()
    answer = document[document.index("GELİR VERGİSİ YÖNÜNDEN DEĞERLENDİRME") :]
    source_tokens = _quality_tokens(document)

    assert "............" in answer
    assert _has_repeated_letter_run(answer) is False

    blockers = _quality_blockers_for_text(
        "Cevap",
        answer,
        set(source_tokens),
        40,
        0.40,
        source_tokens=source_tokens,
    )
    assert blockers == []


def test_invoice_numbers_with_zero_padding_do_not_trigger_digit_spam() -> None:
    document = _load_ipa_document()
    answer = (
        document[document.index("GELİR VERGİSİ YÖNÜNDEN DEĞERLENDİRME") :]
        + " Bülent YARAR'ın (22.04.2020 tarih ve ONR2020000000001 sayılı ile "
        "15.05.2020 tarih ve ONR2020000000002 sayılı) eski Birlik Yüklenicisi adına "
        "KDV'siz fatura düzenlendiği değerlendirilmektedir."
    )
    source_tokens = _quality_tokens(document)

    assert _has_repeated_digit_run(answer) is False
    assert _has_repeated_digit_run("11111111") is True

    blockers = _quality_blockers_for_text(
        "Cevap",
        answer,
        set(source_tokens),
        40,
        0.40,
        source_tokens=source_tokens,
    )
    assert not any("rastgele" in blocker for blocker in blockers)


def test_keyboard_spam_is_blocked() -> None:
    document = _load_ipa_document()
    source_tokens = _quality_tokens(document)
    spam = "asdfghjkl qwertyui zxcvbnm " * 8

    blockers = _quality_blockers_for_text(
        "Cevap",
        spam,
        set(source_tokens),
        40,
        0.40,
        source_tokens=source_tokens,
    )
    assert any("rastgele" in blocker for blocker in blockers)


def test_repeated_phrase_paste_is_blocked() -> None:
    document = _load_ipa_document()
    answer = document[document.index("GELİR VERGİSİ YÖNÜNDEN DEĞERLENDİRME") :]
    source_tokens = _quality_tokens(document)
    spam = answer[:900] * 3

    blockers = _quality_blockers_for_text(
        "Cevap",
        spam,
        set(source_tokens),
        40,
        0.40,
        source_tokens=source_tokens,
    )
    assert any("cümle parçalarının tekrar eden kopyası" in blocker for blocker in blockers)
