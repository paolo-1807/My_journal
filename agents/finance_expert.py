"""
morning_agent.py
================
Agent AI per il report mattutino degli investimenti.
Usa OpenAI GPT-4o per analizzare i dati estratti da investment_tool.py
e produrre un briefing narrativo in tre sezioni.

Dipendenze:
    pip install openai yfinance pandas numpy

Utilizzo:
    python morning_agent.py

Variabili d'ambiente richieste:
    OPENAI_API_KEY=sk-...
    (oppure inseriscila direttamente in config.py)
"""

import os
import json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

from tools.finance_api import get_portfolio_report
from config import I_MIEI_INVESTIMENTI

load_dotenv()
# ─────────────────────────────────────────────
# CONFIGURAZIONE
# ─────────────────────────────────────────────

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  
MODEL          = "gpt-4o"
LINGUA         = "italiano"
NOME_UTENTE    = "Paolo"  

client = OpenAI(api_key=OPENAI_API_KEY)


# ─────────────────────────────────────────────
# TOOLS DEFINITION (OpenAI function calling)
# ─────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_portfolio_report",
            "description": (
                "Recupera dati finanziari aggiornati per una lista di asset dal portafoglio "
                "dell'utente. Ritorna per ciascun asset: prezzo, delta daily, delta vs PMC, "
                "RSI, posizione nel range 30gg, benchmark comparison e ultime notizie."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "assets": {
                        "type": "array",
                        "description": "Lista degli asset da analizzare",
                        "items": {
                            "type": "object",
                            "properties": {
                                "ticker": {"type": "string", "description": "Simbolo Yahoo Finance"},
                                "pmc":    {"type": "number",  "description": "Prezzo medio di carico"},
                            },
                            "required": ["ticker"],
                        },
                    }
                },
                "required": ["assets"],
            },
        },
    }
]


# ─────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────

SYSTEM_PROMPT = f"""
Sei l'analista finanziario di {NOME_UTENTE}. Scrivi in {LINGUA}, prima persona plurale, stile "The Economist": analitico, asciutto, senza bullet point.
STRUTTURA TESTO UNICO (Max 150 parole):
Protagonista: Narra l'asset con la variazione più critica. Spiega il "perché" integrando le news, evitando la ripetizione dei prezzi grezzi.
Salute (RSI/Range): Valuta ipercomprato (>70) o ipervenduto (<30) basandoti su RSI e range 30gg. Se neutrale, sii sintetico.
Contesto & Benchmark: Confronta il portafoglio ai mercati globali. Usa i titoli macro (BCE/Inflazione) per definire il sentiment. Chiudi con una sintesi fulminea.
VINCOLI:
Prosa fluente, NO liste, NO disclaimer legali.
Usa metafore finanziarie vivide.
Lunghezza massima totale: simile a 2 paragrafi standard.
Se i dati mancano, non inventare.
"""

# ─────────────────────────────────────────────
# ESECUZIONE DEL TOOL (function calling handler)
# ─────────────────────────────────────────────

def _execute_tool(tool_name: str, arguments: dict) -> str:
    """Esegue il tool richiesto dall'agent e ritorna il risultato come JSON string."""
    if tool_name == "get_portfolio_report":
        result = get_portfolio_report(arguments["assets"])
        return json.dumps(result, ensure_ascii=False, indent=2)
    return json.dumps({"errore": f"Tool '{tool_name}' non riconosciuto."})


# ─────────────────────────────────────────────
# AGENT LOOP
# ─────────────────────────────────────────────

def run_morning_agent(verbose: bool = False) -> str:
    """
    Esegue il loop dell'agent:
    1. Invia il prompt iniziale a GPT-4o
    2. Se l'agent chiama get_portfolio_report, esegue il tool e reinvia i dati
    3. Riceve il report narrativo finale
    4. Ritorna il testo del report

    Args:
        verbose: se True, stampa i passaggi intermedi del loop
    Returns:
        Il report mattutino come stringa Markdown
    """

    data_oggi = datetime.now().strftime("%A %d %B %Y, ore %H:%M")

    # Messaggio iniziale: l'agent sa già quali asset analizzare
    user_message = (
        f"Buongiorno. Oggi è {data_oggi}. "
        f"Recupera i dati aggiornati per il mio portafoglio e scrivi il report mattutino. "
        f"Il portafoglio è: {json.dumps(I_MIEI_INVESTIMENTI, ensure_ascii=False)}"
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_message},
    ]

    if verbose:
        print(f"[Agent] Avvio — {data_oggi}")

    # ── Loop agentico ─────────────────────────
    max_iterations = 5  # guardrail anti-loop infinito
    for iteration in range(max_iterations):

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        msg = response.choices[0].message

        # Caso 1: l'agent vuole chiamare un tool
        if msg.tool_calls:
            messages.append(msg)  # aggiungi il messaggio dell'assistant con tool_calls

            for tool_call in msg.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)

                if verbose:
                    print(f"[Agent] Chiama tool: {fn_name}({list(fn_args.keys())})")

                tool_result = _execute_tool(fn_name, fn_args)

                if verbose:
                    print(f"[Agent] Tool completato — {len(tool_result)} caratteri ricevuti")

                messages.append({
                    "role":         "tool",
                    "tool_call_id": tool_call.id,
                    "content":      tool_result,
                })

            # continua il loop per ottenere la risposta finale
            continue

        # Caso 2: l'agent ha prodotto il report finale
        if msg.content:
            if verbose:
                print(f"[Agent] Report generato ({len(msg.content)} caratteri)")
            return msg.content

        # Caso 3: risposta vuota (non dovrebbe accadere)
        return "[Errore] L'agent non ha prodotto output."

    return "[Errore] Numero massimo di iterazioni raggiunto senza output finale."


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

    # Salva il report su file (opzionale)
    output_dir = "reports"
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/report_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# Report Investimenti — {datetime.now().strftime('%d %B %Y')}\n\n")
        f.write(report)
    print(f"\n✅ Report salvato in: {filename}")