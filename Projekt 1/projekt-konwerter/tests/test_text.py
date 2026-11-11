"""Testy konwerterów TXT <-> DOCX (Grupa B)."""

from pathlib import Path

import docx
import pytest

from konwerter.converters.text import docx_to_txt, txt_to_docx
from konwerter.errors import InvalidInputError

DANE = Path(__file__).resolve().parent.parent / "dane_testowe"


def paragraphs(path: Path) -> list[str]:
    return [p.text for p in docx.Document(str(path)).paragraphs]


def test_txt_to_docx_linia_to_akapit(tmp_path):
    out = tmp_path / "n.docx"
    txt_to_docx(DANE / "notatka.txt", out)
    akapity = paragraphs(out)

    linie = (DANE / "notatka.txt").read_text(encoding="utf-8").splitlines()
    assert akapity == linie                       # liczba i kolejność akapitów zgodna z liniami
    assert akapity[1] == ""                       # pusta linia zachowana
    assert "Zażółć gęślą jaźń" in akapity[2]      # polskie znaki
    assert akapity[3] == "Termin oddania:\tLab 5"  # tabulator zachowany


def test_txt_ze_znakami_sterujacymi(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("przed\x00po\x0cstronie\n", encoding="utf-8")
    out = tmp_path / "a.docx"
    txt_to_docx(src, out)
    assert paragraphs(out) == ["przedpostronie"]


def test_txt_nie_utf8(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("Łódź", encoding="cp1250")
    with pytest.raises(InvalidInputError, match="UTF-8"):
        txt_to_docx(src, tmp_path / "a.docx")


def test_docx_to_txt_akapity_i_tabela_w_kolejnosci(tmp_path):
    out = tmp_path / "s.txt"
    docx_to_txt(DANE / "sprawozdanie.docx", out)
    linie = out.read_text(encoding="utf-8").splitlines()

    assert linie[0] == "Sprawozdanie z laboratorium"
    assert "ąćęłńóśźż" in linie[2]
    assert linie[3] == "Kierunek\tNarzędzie\tStatus"   # tabela po akapitach, komórki rozdzielone tabem
    assert linie[4] == "CSV → JSON\tcsv/json\tdziała"
    assert linie[-1] == "Akapit po tabeli – koniec dokumentu."


def test_uszkodzony_docx(tmp_path):
    with pytest.raises(InvalidInputError, match="uszkodzony"):
        docx_to_txt(DANE / "uszkodzony.docx", tmp_path / "x.txt")


def test_round_trip_txt_docx_txt(tmp_path):
    d = tmp_path / "n.docx"
    t = tmp_path / "n.txt"
    txt_to_docx(DANE / "notatka.txt", d)
    docx_to_txt(d, t)
    assert t.read_text(encoding="utf-8") == (DANE / "notatka.txt").read_text(encoding="utf-8")
