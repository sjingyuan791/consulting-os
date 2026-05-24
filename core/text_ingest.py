import io
import PyPDF2
# import docx  # python-docx needs to be installed
from typing import List

# Chunking Configuration
CHUNK_SIZE = 4000  # Characters (approx)
OVERLAP = 200

def extract_text_from_file(file_obj, file_type: str) -> str:
    """Reads file object and returns full text string."""
    text = ""
    try:
        match file_type:
            case "pdf":
                reader = PyPDF2.PdfReader(file_obj)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            case "docx":
                import docx
                doc = docx.Document(file_obj)
                for para in doc.paragraphs:
                    text += para.text + "\n"
            case "txt" | "md":
                text = file_obj.read().decode("utf-8", errors="ignore")
            case _:
                return ""
    except Exception as e:
        return f"[Error extraction: {str(e)}]"
        
    return text

def chunk_text(text: str) -> List[str]:
    """Splits text into chunks with overlap."""
    if not text:
        return []
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end]
        chunks.append(chunk)
        start += (CHUNK_SIZE - OVERLAP)
        
    return chunks
