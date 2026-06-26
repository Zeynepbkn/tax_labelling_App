from __future__ import annotations

import re

from bs4 import BeautifulSoup


PDF_BOILERPLATE_PATTERNS = [
    r"Bu belge, güvenli elektronik imza ile imzalanmıştır\.",
    r"Belge Doğrulama Kodu:.*",
    r"Belge Doğrulama Adresi:.*",
    r"KEP Adresi\s*:.*",
    r"e-Posta\s*:.*",
    r"İnternet Adresi\s*:.*",
    r"Telefon No\s*:.*",
    r"Faks No\s*:.*",
    r"\n\d+/\d+\n",  # sayfa numarası gibi
]


def clean_html_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n")
    return _normalize_whitespace(text)


def clean_pdf_text(text: str) -> str:
    t = text
    for p in PDF_BOILERPLATE_PATTERNS:
        t = re.sub(p, "", t, flags=re.IGNORECASE)
    return _normalize_whitespace(t)


def normalize_document_whitespace(text: str | None) -> str:
    if not text:
        return ""
    return _normalize_whitespace(text)


def choose_display_text(html_text: str | None, pdf_text: str | None) -> tuple[str, str]:
    """
    Dönüş: (display_text, display_source)
    display_source: htmlText | pdfText | normalized
    """
    if html_text and html_text.strip():
        cleaned = clean_html_text(html_text)
        # "anlamlı" heuristiği: çok kısa veya sadece whitespace değilse kabul et
        if len(cleaned.strip()) >= 200:
            return cleaned, "htmlText"

    if pdf_text and pdf_text.strip():
        cleaned = clean_pdf_text(pdf_text)
        return cleaned, "pdfText"

    return "", "normalized"


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    lines = [re.sub(r"[ \t\f\v]+", " ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


ANSWER_SPLIT_MARKERS = [
    "sorulmaktadır",
    "talep edilmektedir",
    "talep edildiği anlaşılmaktadır",
    "talep ettiğiniz anlaşılmaktadır",
    "talep edildiği anlaşılmıştır",
    "talep ettiğiniz anlaşılmıştır",
    "görüşü istenilmektedir",
    "görüş istenilmektedir",
    "görüşü sorulmaktadır",
    "sorulduğu anlaşılmaktadır",
    "talep edilmiştir",
    "anlaşılmaktadır",
]


def extract_expected_answer_prefix(document_text: str) -> str | None:
    """
    'görüş talep...' vb. ifadelerden sonra başlayan kısmı tahmini 'cevap başlangıcı' olarak döndürür.
    Tam doğruluk garantisi yok; kalite kontrol için heuristik.
    """
    lower = document_text.lower()
    best_idx = None
    best_marker = None
    for marker in ANSWER_SPLIT_MARKERS:
        idx = lower.rfind(marker)
        if idx != -1:
            end_idx = idx + len(marker)
            if best_idx is None or end_idx > best_idx:
                best_idx = end_idx
                best_marker = marker

    if best_idx is None:
        return None

    # marker sonrası noktadan/iki noktadan sonraki metni al
    tail = document_text[best_idx:]
    tail = re.sub(r"^[^A-Za-zÇĞİÖŞÜçğıöşü0-9]+", "", tail).strip()
    # Çok kısa ise anlamsız olabilir
    if len(tail) < 80:
        return None
    return tail[:500]  # prefix kıyas için yeter

