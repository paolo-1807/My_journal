import os
from datetime import datetime

# 1. Dati che vogliamo inserire 
dati = {
    "id_giornale": "001",
    "data_generazione": datetime.now().strftime("%d/%m/%Y"),
    "contenuto_sezione_1": "Mettere testo fatto da agent/finance_expert"
}

# 2. Crea la cartella Output se non esiste
if not os.path.exists('Output'):
    os.makedirs('Output')

# 3. Leggi il file Template (il tuo html attuale)
with open("templates/template_1.html", "r", encoding="utf-8") as f:
    template = f.read()

# 4. Sostituisci i segnaposto (Metodo semplice senza librerie esterne)
# Nota: Per progetti complessi useremo Jinja2, ma per ora facciamo così:
html_finale = template
for chiave, valore in dati.items():
    html_finale = html_finale.replace("{{ " + chiave + " }}", valore)

# 5. Salva il file finale nella cartella Output
nome_file = f"Output/giornale_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
with open(nome_file, "w", encoding="utf-8") as f:
    f.write(html_finale)

print(f"File generato con successo: {nome_file}")