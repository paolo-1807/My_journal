"""
economist_reader.py
-------------------
Legge la newsletter "The World in Brief" dell'Economist dalla Gmail,
estrae la sezione "Today's top stories" e la restituisce come testo
pulito, pronto per essere inserito in un file HTML.

Struttura reale della mail:
- La sezione inizia con un <h2> che contiene "Today's top stories"
- Ogni notizia è in un <td class="article-text"> con un <p> che inizia con ▸
- La sezione finisce quando appare "Figure of the day" o "Today's markets"

Requisiti:
    pip install google-auth google-auth-oauthlib google-api-python-client beautifulsoup4

Assicurati di avere token.json e credentials.json nella stessa cartella.
"""

import base64
import re
import time
import html

from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ── Configurazione ────────────────────────────────────────────────────────────

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
SENDER = "noreply@e.economist.com"
SUBJECT_KEYWORD = "The world in brief"
LOOKBACK_HOURS = 22

# ── Auth Gmail ────────────────────────────────────────────────────────────────

def get_gmail_service():
    """Restituisce un servizio Gmail autenticato usando token.json."""
    creds = None
    try:
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    except FileNotFoundError:
        pass

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


# ── Ricerca email ─────────────────────────────────────────────────────────────

def find_economist_email(service):
    """
    Cerca l'email dell'Economist arrivata nelle ultime LOOKBACK_HOURS ore.
    Restituisce il messaggio grezzo o None se non trovato.
    """
    cutoff_ts = int(time.time()) - (LOOKBACK_HOURS * 3600)
    query = f"from:{SENDER} subject:{SUBJECT_KEYWORD} after:{cutoff_ts}"
    print(f"[*] Query Gmail: {query}")

    result = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=5,
    ).execute()

    messages = result.get("messages", [])
    if not messages:
        print("[!] Nessuna email trovata nelle ultime 22 ore.")
        return None

    msg_id = messages[0]["id"]
    print(f"[*] Email trovata, id: {msg_id}")

    return service.users().messages().get(
        userId="me",
        id=msg_id,
        format="full",
    ).execute()


# ── Decodifica payload ────────────────────────────────────────────────────────

def decode_part(data: str) -> str:
    """Decodifica una stringa base64url in testo UTF-8."""
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")


def extract_html_body(message: dict) -> str | None:
    """Naviga il payload MIME e restituisce la parte text/html."""
    payload = message.get("payload", {})

    def _find_html(part):
        if part.get("mimeType", "") == "text/html":
            data = part.get("body", {}).get("data", "")
            if data:
                return decode_part(data)
        for sub in part.get("parts", []):
            result = _find_html(sub)
            if result:
                return result
        return None

    return _find_html(payload)


# ── Estrazione sezione "Today's top stories" ──────────────────────────────────

def extract_top_stories(html_body: str) -> list:
    """
    Estrae i bullet della sezione "Today's top stories" dalla mail dell'Economist.

    Strategia basata sulla struttura HTML reale:
    1. Trova il <h2> "Today's top stories"
    2. Raccoglie tutti i <td class="article-text"> successivi con bullet ▸
    3. Si ferma su "Figure of the day" / "Today's markets" / "The day ahead"

    Restituisce una lista di stringhe, una per ogni notizia.
    """
    soup = BeautifulSoup(html_body, "html.parser")

    # ── Step 1: trova il tag <h2> "Today's top stories" ──────────────────────
    start_tag = None
    for h2 in soup.find_all("h2"):
        text_lower = h2.get_text(strip=True).lower()
        if "today" in text_lower and "top stories" in text_lower:
            start_tag = h2
            break

    if start_tag is None:
        print("[!] Header 'Today's top stories' non trovato nell'HTML.")
        return []

    # ── Step 2: raccogliamo i td DOPO l'h2 usando indice nel sorgente ─────────
    STOP_MARKERS = {"figure of the day", "today's markets", "the day ahead"}

    html_str = str(soup)
    h2_pos = html_str.find(str(start_tag))

    bullets = []

    for td in soup.find_all("td", class_="article-text"):
        td_str = str(td)
        td_pos = html_str.find(td_str)

        if td_pos < h2_pos:
            continue

        p = td.find("p")
        if p is None:
            continue

        raw_text = p.get_text(separator=" ", strip=True)

        # Fine sezione
        if any(marker in raw_text.lower() for marker in STOP_MARKERS):
            break

        # Solo i bullet con ▸
        if "\u25b8" not in raw_text:  # ▸ = U+25B8
            continue

        clean = clean_bullet(raw_text)
        if clean:
            bullets.append(clean)

    return bullets


def clean_bullet(text: str) -> str:
    """
    Pulisce il testo di un singolo bullet:
    - Rimuove ▸
    - Decodifica entità HTML residue
    - Normalizza spazi
    """
    text = text.replace("\u25b8", "").strip()
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", " ", text)
    return text.strip()


# ── Formattazione output ──────────────────────────────────────────────────────

def format_as_text(bullets: list) -> str:
    """
    Testo pulito numerato, pronto per inserimento in HTML.
    """
    return "\n\n".join(f"{i}. {b}" for i, b in enumerate(bullets, 1))


# ── Entrypoint ────────────────────────────────────────────────────────────────

def main() -> str:
    service = get_gmail_service()
    message = find_economist_email(service)

    if message is None:
        return ""

    html_body = extract_html_body(message)
    if not html_body:
        print("[!] Impossibile estrarre il corpo HTML dell'email.")
        return ""

    bullets = extract_top_stories(html_body)

    if not bullets:
        print("[!] Nessun bullet trovato nella sezione 'Today's top stories'.")
        return ""

    result = format_as_text(bullets)

    print("\n" + "=" * 60)
    print("TODAY'S TOP STORIES")
    print("=" * 60)
    print(result)
    print("=" * 60)
    print(f"\n[OK] Estratti {len(bullets)} bullet.")

    return result


if __name__ == "__main__":
    result = main()
    if result:
        with open("top_stories.txt", "w", encoding="utf-8") as f:
            f.write(result)
        print("[OK] Salvato in 'top_stories.txt'")