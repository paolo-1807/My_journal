# tools/translator.py
import deepl
import os
from dotenv import load_dotenv

load_dotenv()

DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")
_translator_client = deepl.Translator(DEEPL_API_KEY) if DEEPL_API_KEY else None

def translate_to_italian(text: str) -> str:
    """
    Traduce un testo dall'inglese all'italiano usando l'API di DeepL.
    """
    if not text or text.strip() == "":
        return text

    if _translator_client is None:
        print("[WARN] Chiave API DeepL non configurata. Ritorno testo originale.")
        return text

    try:
        # "IT" per l'italiano generico
        result = _translator_client.translate_text(text, target_lang="IT")
        return result.text
    except Exception as e:
        print(f"Errore DeepL: {e}")
        return text  # Ritorna l'originale in caso di errore