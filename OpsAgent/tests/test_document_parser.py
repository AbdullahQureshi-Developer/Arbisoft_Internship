import io
import pytest
from pypdf import PdfWriter
from docx import Document
from src.skills.document_parser import parse_document


def test_parse_pdf_document():
    # Create sample PDF in memory
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    page = writer.pages[0]
    
    # Simple PDF with known text
    buf = io.BytesIO()
    writer.write(buf)
    pdf_bytes = buf.getvalue()

    # Note: blank page returns string, let's test parser execution
    res = parse_document(file_bytes=pdf_bytes, filename="spec.pdf")
    assert isinstance(res, str)


def test_parse_docx_document():
    # Create sample DOCX in memory
    doc = Document()
    doc.add_heading("Project Status Update", level=1)
    doc.add_paragraph("Deadline: 2026-08-15 14:00. Notable update: Scope expanded.")
    
    buf = io.BytesIO()
    doc.save(buf)
    docx_bytes = buf.getvalue()

    res = parse_document(file_bytes=docx_bytes, filename="status.docx")
    assert "Project Status Update" in res
    assert "Deadline: 2026-08-15 14:00" in res
    assert "Scope expanded" in res
