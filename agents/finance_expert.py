# agents/finance_expert.py
"""
finance_expert.py
=================
Agent semplificato per il report mattutino degli investimenti.
Chiama direttamente get_portfolio_report() e passa i dati a GPT-4o
per produrre un briefing narrativo in prosa.

Dipendenze:
    pip install openai yfinance pandas numpy python-dotenv

Utilizzo:
    python finance_expert.py

Variabili d'ambiente richieste:
    OPENAI_API_KEY=sk-...
"""
import sys
import os
import json
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.finance_api import get_portfolio_report

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=True)

# ─────────────────────────────────────────────
# CONFIGURAZIONE
# ─────────────────────────────────────────────

MODEL       = "gpt-4o"
LINGUA      = "italiano"
NOME_UTENTE = "Paolo"
OPENAI_DISABLED_MESSAGE = "open_api disattivata"


# ─────────────────────────────────────────────
# PROMPT
# ─────────────────────────────────────────────

SYSTEM_PROMPT = f"""
Sei l'analista finanziario personale di {NOME_UTENTE}.
Scrivi in {LINGUA}, in prima persona plurale, con lo stile de "The Economist":
analitico, asciutto, senza bullet point, senza disclaimer legali.

Riceverai un JSON con i dati aggiornati del portafoglio. Producendo un testo unico
di massimo 200 parole, strutturato in due paragrafi:

1. PROTAGONISTA — Narra l'asset con la variazione più critica (positiva o negativa).
   Integra le notizie recenti per spiegare il "perché". Evita di ripetere i prezzi grezzi:
   usa variazioni percentuali e contesto.

2. CONTESTO & SALUTE — Commenta RSI e posizione nel range 30gg per segnalare
   zone di ipercomprato/ipervenduto. Confronta il portafoglio ai rispettivi benchmark.
   Chiudi con una sintesi fulminea sul sentiment complessivo.

Regole ferree:
- Prosa fluente, zero liste.
- Usa metafore finanziarie vivide ma non ridondanti.
- Se un dato è assente nel JSON, ignoralo senza inventare nulla.
- Non menzionare mai il formato JSON né il tuo funzionamento interno.
"""


# ─────────────────────────────────────────────
# FUNZIONE PRINCIPALE
# ─────────────────────────────────────────────

def run_morning_agent(verbose: bool = False) -> str:
    """
    Esegue il report mattutino in due passi:
      1. Recupera i dati tramite get_portfolio_report()
      2. Invia i dati a GPT-4o e restituisce il testo narrativo

    Args:
        verbose: se True, stampa i dettagli intermedi

    Returns:
        Il report mattutino come stringa di testo
    """
    use_openai_agent = os.getenv("USE_OPENAI_AGENT", "0") == "1"
    if not use_openai_agent:
        if verbose:
            print("[Agent] USE_OPENAI_AGENT disattivato: salto chiamata OpenAI.")
        return OPENAI_DISABLED_MESSAGE

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        if verbose:
            print("[Agent] OPENAI_API_KEY mancante: salto chiamata OpenAI.")
        return "Sezione analitica non disponibile."

    client = OpenAI(api_key=api_key)

    # ── Step 1: raccogli i dati dal tool ──────
    if verbose:
        print("[Agent] Recupero dati portafoglio...")

    portfolio_data = get_portfolio_report()

    if verbose:
        print(f"[Agent] Dati ricevuti per {len(portfolio_data)} asset.")

    # ── Step 2: costruisci il prompt utente ───
    data_oggi = datetime.now().strftime("%A %d %B %Y, ore %H:%M")

    user_message = (
        f"Buongiorno. Oggi è {data_oggi}.\n\n"
        f"Ecco i dati aggiornati del mio portafoglio:\n\n"
        f"{json.dumps(portfolio_data, ensure_ascii=False, indent=2)}\n\n"
        f"Scrivi il report mattutino."
    )

    # ── Step 3: chiama GPT-4o ─────────────────
    if verbose:
        print(f"[Agent] Invio dati a {MODEL}...")

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.5,       # un po' di vivacità stilistica, senza allucinazioni
        max_tokens=400,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
    )

    report = response.choices[0].message.content or "[Errore] Nessun output ricevuto."

    if verbose:
        print(f"[Agent] Report generato ({len(report)} caratteri).")

    return report


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":

    print("=" * 60)
    print("  📰  GIORNALE MATTUTINO — SEZIONE INVESTIMENTI")
    print("=" * 60)
    print()

    report = run_morning_agent(verbose=True)

    print()
    print("─" * 60)
    print(report)
    print("─" * 60)

  