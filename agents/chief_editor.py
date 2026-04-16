"""
chief_editor.py
================
Legge due contenuti del giornale e produce due riassunti (in italiano, prosa unica)
da inserire nei placeholder di `templates/index.html`.

Vincoli:
- massimo 100 parole per ciascun riassunto
- prosa senza bullet point / elenchi
- niente traduzione fatta da OpenAI: il testo sorgente viene trattato come già italiano
"""

from __future__ import annotations

import json
import os
import re
from typing import Tuple

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

USE_OPENAI_AGENT = os.getenv("USE_OPENAI_AGENT", "0") == "1"
MODEL = os.getenv("CHIEF_EDITOR_MODEL", "gpt-4o")


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _strip_bullets(text: str) -> str:
    """
    Rimuove eventuali caratteri/linee tipici da bullet.
    Non è una traduzione: è solo pulizia per rispettare il formato richiesto.
    """
    if not text:
        return text
    # Pulisce prefissi tipo "- " / "* " / "• " a inizio stringa.
    text = re.sub(r"^(?:(?:\d+[\.\)]|[-•*])\s*)+", "", text).strip()
    # Se model avesse inserito più righe con bullet, le ricolliamo in prosa.
    text = re.sub(r"\s+(?:(?:\d+[\.\)]|[-•*])\s*)", " ", text).strip()
    return text


def _truncate_to_words(text: str, max_words: int) -> str:
    text = _normalize_whitespace(text)
    if not text:
        return text
    words = text.split()
    if len(words) <= max_words:
        return text
    truncated = " ".join(words[:max_words]).strip()
    # Chiude la frase (se non termina già con punteggiatura).
    if truncated and truncated[-1] not in ".!?":
        truncated += "."
    return truncated


def _clean_summary(text: str, max_words: int = 100) -> str:
    text = text or ""
    text = _strip_bullets(text)
    text = _truncate_to_words(text, max_words=max_words)
    return text


def _extract_json_object(text: str) -> dict | None:
    """
    Prova a estrarre un JSON da una risposta che potrebbe includere rumore.
    """
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # fallback: cerca la prima e ultima graffa
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def run_chief_editor(
    contenuto_portfolio_review: str,
    contenuto_the_world_in_brief: str,
    verbose: bool = False,
) -> Tuple[str, str]:
    """
    Returns:
        (summary_the_world_in_brief, summary_portfolio_review)
    """

    world_src = (contenuto_the_world_in_brief or "").strip()
    portfolio_src = (contenuto_portfolio_review or "").strip()

    # Fallback locale: nessuna chiamata OpenAI.
    if not USE_OPENAI_AGENT:
        if verbose:
            print("[chief_editor] USE_OPENAI_AGENT disattivato: fallback locale.")
        return (
            _clean_summary(world_src, max_words=100),
            _clean_summary(portfolio_src, max_words=100),
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        if verbose:
            print("[chief_editor] OPENAI_API_KEY mancante: fallback locale.")
        return (
            _clean_summary(world_src, max_words=100),
            _clean_summary(portfolio_src, max_words=100),
        )

    client = OpenAI(api_key=api_key)

    system_prompt = (
        "Sei un editor professionale. "
        "Devi scrivere due riassunti in italiano, in prosa, senza bullet point, "
        "e senza liste. Massimo 100 parole per ogni riassunto. "
        "Non tradurre: il testo sorgente che ricevi è già in italiano. "
        "Usa solo informazioni presenti nei contenuti forniti, senza inventare dati."
    )

    user_message = (
        "Riceverai due sezioni. Scrivi due riassunti distinti.\n\n"
        "SEZIONE_THE_WORLD_IN_BRIEF:\n"
        f"{world_src}\n\n"
        "SEZIONE_PORTFOLIO_REVIEW:\n"
        f"{portfolio_src}\n\n"
        "Rispondi ESCLUSIVAMENTE con un oggetto JSON nel formato:\n"
        "{\n"
        '  "summary_the_world_in_brief": "...",\n'
        '  "summary_portfolio_review": "..." \n'
        "}\n\n"
        "Vincoli sui valori stringa:\n"
        "- un solo paragrafo (senza newline)\n"
        "- nessun bullet point, nessun elenco\n"
        "- massimo 100 parole ciascuno"
    )

    if verbose:
        print(f"[chief_editor] Chiamata a OpenAI model={MODEL} ...")

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.3,
        max_tokens=450,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )

    raw = response.choices[0].message.content or ""
    data = _extract_json_object(raw) or {}

    world_summary = data.get("summary_the_world_in_brief") or ""
    portfolio_summary = data.get("summary_portfolio_review") or ""

    # Ultima sicurezza sul formato richiesto.
    world_summary = _clean_summary(world_summary, max_words=100)
    portfolio_summary = _clean_summary(portfolio_summary, max_words=100)

    if verbose:
        print("[chief_editor] Riassunti generati.")

    return world_summary, portfolio_summary

