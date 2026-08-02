import io
import logging
from pypdf import PdfReader
from docx import Document

from src.hooks.logging_hook import log_call

logger = logging.getLogger(__name__)


@log_call
def parse_document(file_bytes: bytes, filename: str) -> str:
    """
    Extracts raw text from PDF or DOCX file bytes.
    """
    ext = filename.lower().split(".")[-1]
    text_content = []

    if ext == "pdf":
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text_content.append(extracted)
        except Exception as e:
            logger.error(f"Error parsing PDF file '{filename}': {e}")
            raise ValueError(f"Failed to parse PDF document: {e}")

    elif ext in ["docx", "doc"]:
        try:
            doc = Document(io.BytesIO(file_bytes))
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text.strip())
        except Exception as e:
            logger.error(f"Error parsing DOCX file '{filename}': {e}")
            raise ValueError(f"Failed to parse DOCX document: {e}")
    else:
        raise ValueError(f"Unsupported document format '.{ext}'. Supported formats: .pdf, .docx")

    return "\n".join(text_content)
