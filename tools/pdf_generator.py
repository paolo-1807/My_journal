import os
from fpdf import FPDF
from datetime import datetime

class DailyJournalPDF(FPDF):
    def header(self):
        # Header elegante
        self.set_font('helvetica', 'B', 22)
        self.set_text_color(33, 37, 41) # Grigio quasi nero
        self.cell(0, 15, 'IL GIORNALE DI PAOLO', ln=True, align='C')
        
        self.set_font('helvetica', 'I', 10)
        self.set_text_color(108, 117, 125) # Grigio secondario
        data_oggi = datetime.now().strftime("%A %d %B %Y")
        self.cell(0, 5, f'Edizione di {data_oggi}', ln=True, align='C')
        
        self.ln(8)
        self.set_draw_color(44, 62, 80)
        self.set_line_width(0.5)
        self.line(10, 38, 200, 38) # Linea di separazione
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(150)
        self.cell(0, 10, f'Pagina {self.page_no()}', align='C')

def create_journal_pdf(testo_investimenti):
    """
    Crea il PDF e lo salva automaticamente nella cartella 'reports'
    con un nome file basato sulla data attuale.
    """
    # 1. Gestione Cartella e Nome File
    output_dir = "reports"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"Giornale_Paolo_{timestamp}.pdf"
    full_path = os.path.join(output_dir, filename)

    # 2. Inizializzazione PDF
    pdf = DailyJournalPDF()
    pdf.add_page()
    
    # 3. Pulizia testo (rimuove caratteri non supportati dai font standard come le emoji)
    # encode/decode serve a "filtrare" il testo per evitare il crash latin-1
    testo_pulito = testo_investimenti.encode('latin-1', 'ignore').decode('latin-1')
    
    # 4. Sezione Investimenti
    pdf.set_font('helvetica', 'B', 16)
    pdf.set_text_color(44, 62, 80) # Blu petrolio
    pdf.cell(0, 10, 'I Miei Investimenti', ln=True)
    pdf.ln(3)
    
    # Corpo del testo
    pdf.set_font('times', '', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 7, testo_pulito, align='J')
    
    # 5. Salvataggio
    pdf.output(full_path)
    return full_path

if __name__ == "__main__":
    # Test rapido
    test_text = "Esempio di testo per la sezione investimenti senza emoji."
    path = create_journal_pdf(test_text)
    print(f"PDF creato con successo in: {path}")