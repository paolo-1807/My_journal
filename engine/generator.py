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

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env", override=True)

from tools.finance_api import get_portfolio_report
from tools.news_fetcher import main as fetch_world_in_brief
from tools.translator import translate_to_italian
from agents.finance_expert import run_morning_agent
from agents.chief_editor import run_chief_editor

USE_OPENAI_AGENT = os.getenv("USE_OPENAI_AGENT", "0") == "1"
OPENAI_DISABLED_MESSAGE = "open_api disattivata"


def genera_pag_0(contenuto_the_world_in_brief, contenuto_portfolio_review):
    """
    Genera l'HTML della pagina index usando `templates/index.html`.
    """

    try:
        env = Environment(loader=FileSystemLoader("templates"))
        template = env.get_template("index.html")

        summary_world, summary_portfolio = run_chief_editor(
            contenuto_portfolio_review=contenuto_portfolio_review,
            contenuto_the_world_in_brief=contenuto_the_world_in_brief,
            verbose=False,
        )

        html_output = template.render(
            id_giornale="{{ID_GIORNALE}}",
            data_generazione="{{DATA_GENERAZIONE}}",
            summary_the_world_in_brief=summary_world,
            summary_portfolio_review=summary_portfolio,
        )
        return html_output
    except Exception:
        return ""

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
            id_giornale="{{ID_GIORNALE}}",
            data_generazione="{{DATA_GENERAZIONE}}",
            contenuto_the_world_in_brief=contenuto_html,
        )
        return {
            "html": html_output,
            "contenuto_the_world_in_brief": contenuto,
        }
    except Exception as e:
        return {
            "html": "",
            "contenuto_the_world_in_brief": "Contenuto non disponibile.",
        }

#pagina Portfolio Review
def genera_pag_2():
    """
    Genera `output/portfolio_review.html` usando il template attuale.
    Renderizza una riga per ogni investimento presente nel report.
    """
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
            contenuto_portfolio_review = OPENAI_DISABLED_MESSAGE

        html_output = template.render(
            id_giornale="{{ID_GIORNALE}}",
            data_generazione="{{DATA_GENERAZIONE}}",
            lista_investimenti=lista_investimenti,
            contenuto_portfolio_review=contenuto_portfolio_review,
        )
        return {
            "html": html_output,
            "contenuto_portfolio_review": contenuto_portfolio_review,
        }
    except Exception as e:
        return {
            "html": "",
            "contenuto_portfolio_review": OPENAI_DISABLED_MESSAGE,
        }


if __name__ == "__main__":
    pass