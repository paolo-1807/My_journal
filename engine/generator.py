#engine/generator.py
import os
import sys
import io
from contextlib import redirect_stdout
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup, escape
from dotenv import load_dotenv

# Permette di eseguire il file sia come modulo (`python -m engine.generator`)
# sia direttamente (`python engine/generator.py`).
if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

load_dotenv()

from tools.finance_api import get_portfolio_report
from tools.news_fetcher import main as fetch_world_in_brief
from tools.translator import translate_to_italian
from agents.finance_expert import run_morning_agent
from agents.chief_editor import run_chief_editor

USE_OPENAI_AGENT = os.getenv("USE_OPENAI_AGENT", "0") == "1"


def genera_pag_0(info_giornale, contenuto_the_world_in_brief, contenuto_portfolio_review):
    """
    Genera `output/index.html` usando `templates/index.html`.
    """
    if info_giornale is None:
        info_giornale = {}

    try:
        env = Environment(loader=FileSystemLoader("templates"))
        template = env.get_template("index.html")

        summary_world, summary_portfolio = run_chief_editor(
            contenuto_portfolio_review=contenuto_portfolio_review,
            contenuto_the_world_in_brief=contenuto_the_world_in_brief,
            verbose=False,
        )

        html_output = template.render(
            id_giornale=info_giornale.get("id", "N/A"),
            data_generazione=info_giornale.get("data", "N/A"),
            summary_the_world_in_brief=summary_world,
            summary_portfolio_review=summary_portfolio,
        )

        os.makedirs("output", exist_ok=True)
        with open("output/index.html", "w", encoding="utf-8") as f:
            f.write(html_output)
        print("Pagina 0 (Index) generata con successo!")
    except Exception:
        pass

#Pagina The World in Brief
def genera_pag_1():
    try:
        env = Environment(loader=FileSystemLoader("templates"))
        template = env.get_template("the_world_in_brief.html")

        # Silenzia l'output verboso di news_fetcher nel terminale.
        with io.StringIO() as _buffer, redirect_stdout(_buffer):
            contenuto = fetch_world_in_brief()
        contenuto = contenuto or "Contenuto non disponibile."
        contenuto = translate_to_italian(contenuto)
        paragrafi = [riga.strip() for riga in contenuto.split("\n\n") if riga.strip()]
        contenuto_html = Markup("<br><br>".join(str(escape(par)) for par in paragrafi))

        html_output = template.render(
            id_giornale="N/A",
            data_generazione="N/A",
            contenuto_the_world_in_brief=contenuto_html,
        )

        os.makedirs("output", exist_ok=True)
        with open("output/the_world_in_brief.html", "w", encoding="utf-8") as f:
            f.write(html_output)
        print("Pagina 1 (The World in Brief) generata con successo!")
        return contenuto
    except Exception as e:
        return "Contenuto non disponibile."

#pagina Portfolio Review
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
        # Silenzia eventuali stampe verbose del report finanziario.
        with io.StringIO() as _buffer, redirect_stdout(_buffer):
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
        if USE_OPENAI_AGENT:
            try:
                contenuto_portfolio_review = run_morning_agent(verbose=False)
            except Exception:
                contenuto_portfolio_review = "Sezione analitica non disponibile."
        else:
            contenuto_portfolio_review = "Sezione analitica disattivata in locale."

        html_output = template.render(
            id_giornale=info_giornale.get("id", "N/A"),
            data_generazione=info_giornale.get("data", "N/A"),
            lista_investimenti=lista_investimenti,
            contenuto_portfolio_review=contenuto_portfolio_review,
        )

        os.makedirs("output", exist_ok=True)
        with open("output/portfolio_review.html", "w", encoding="utf-8") as f:
            f.write(html_output)
        print("Pagina 2 (Portfolio) generata con successo!")
        return contenuto_portfolio_review
    except Exception as e:
        return "Sezione analitica non disponibile."


if __name__ == "__main__":
    info_test = {
        "id": "TEST",
        "data": "2026-04-14",
    }
    contenuto_the_world_in_brief = genera_pag_1()
    contenuto_portfolio_review = genera_pag_2(info_test)
    genera_pag_0(
        info_giornale=info_test,
        contenuto_the_world_in_brief=contenuto_the_world_in_brief,
        contenuto_portfolio_review=contenuto_portfolio_review,
    )