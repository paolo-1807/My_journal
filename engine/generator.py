#engine/generator.py
import os
import sys
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# Permette di eseguire il file sia come modulo (`python -m engine.generator`)
# sia direttamente (`python engine/generator.py`).
if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from tools.finance_api import get_portfolio_report
from agents.finance_expert import run_morning_agent



def genera_pag_0():
    pass


def genera_pag_1():
    pass


def genera_pag_2(info_giornale):
    """
    Genera `output/portfolio_review.html` usando il template attuale.
    Renderizza una riga per ogni investimento presente nel report.
    """

    if info_giornale is None:
        info_giornale = {}

    def _fmt_pct(value):
        if value is None:
            return "N/A"
        if isinstance(value, (int, float)):
            sign = "+" if value > 0 else ""
            return f"{sign}{value:.2f}%"
        return str(value)

    try:
        dati_grezzi = get_portfolio_report() or []
        lista_investimenti = []
        for asset in dati_grezzi:
            lista_investimenti.append(
                {
                    "nome": asset.get("nome") or asset.get("ticker") or "N/A",
                    "oggi": _fmt_pct((asset.get("delta_daily") or {}).get("variazione_pct")),
                    "assoluto": _fmt_pct((asset.get("delta_pmc") or {}).get("variazione_pct")),
                }
            )

        env = Environment(loader=FileSystemLoader("templates"))
        template = env.get_template("portfolio_review.html")
        try:
            contenuto_sezione_2 = run_morning_agent(verbose=False)
        except Exception as agent_error:
            contenuto_sezione_2 = f"Sezione analitica non disponibile: {agent_error}"

        html_output = template.render(
            id_giornale=info_giornale.get("id", "N/A"),
            data_generazione=info_giornale.get("data", "N/A"),
            lista_investimenti=lista_investimenti,
            contenuto_sezione_2=contenuto_sezione_2,
        )

        os.makedirs("output", exist_ok=True)
        with open("output/portfolio_review.html", "w", encoding="utf-8") as f:
            f.write(html_output)

        print("Pagina 2 (Portfolio) generata con successo!")
    except Exception as e:
        print(f"Errore durante la generazione della Pagina 2: {e}")


if __name__ == "__main__":
    info_test = {
        "id": "TEST",
        "data": "2026-04-14",
    }
    genera_pag_2(info_test)