from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
import os

# Font setup for Japanese support
# Assuming a font exists or using a default. 
# For Windows, we can often rely on system fonts, but ReportLab needs TTF path.
# We'll try to use MSGothic or similar if available, or fallback.
FONT_PATH = "C:\\Windows\\Fonts\\msgothic.ttc"

def register_font():
    try:
        pdfmetrics.registerFont(TTFont('Gothic', FONT_PATH))
        return 'Gothic'
    except (IOError, OSError, Exception) as e:
        # Fallback to Helvetica if Japanese font not available
        import logging
        logging.debug(f"Japanese font not available: {type(e).__name__}")
        return 'Helvetica'

def generate_pdf_report(report_data: dict, output_path: str):
    """
    Generates a PDF report from the DiagnosisReport model (dict).
    """
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    font_name = register_font()
    
    def draw_header(title):
        c.setFont(font_name, 16)
        c.drawString(50, height - 50, title)
        c.line(50, height - 60, width - 50, height - 60)
    
    # Page 1: Overview & Hypothesis
    draw_header("Diagnosis Report / 診断レポート")
    
    y = height - 100
    c.setFont(font_name, 12)
    
    # Hypothesis
    c.drawString(50, y, "【暫定仮説】")
    y -= 20
    for h in report_data.get('hypothesis', []):
        c.drawString(70, y, f"- {h}")
        y -= 15
        if y < 100:
            c.showPage()
            y = height - 50
    
    y -= 20
    c.drawString(50, y, "【MECE論点】")
    y -= 20
    for issue in report_data.get('mece_issues', []):
        c.drawString(70, y, f"- {issue}")
        y -= 15

    # Actions
    y -= 20
    c.drawString(50, y, "【推奨アクション】")
    y -= 20
    for action in report_data.get('actions', []):
        # action is dict?
        if isinstance(action, dict):
             txt = f"{action.get('kpi', '')}: {action.get('todo', '')}"
        else:
             txt = str(action)
        c.drawString(70, y, f"- {txt}")
        y -= 15
        
    c.showPage()
    c.save()
