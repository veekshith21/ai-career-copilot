"""Resume file parsing: extract raw text from PDF, DOCX, and TXT."""
from __future__ import annotations
import re
from pathlib import Path
import structlog

logger = structlog.get_logger()


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file using pdfplumber."""
    import pdfplumber
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=2, y_tolerance=2)
            if text:
                text_parts.append(text)
    return "\n\n".join(text_parts)


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from a DOCX file."""
    from docx import Document
    doc = Document(file_path)
    paragraphs = []
    for para in doc.paragraphs:
        if para.text.strip():
            paragraphs.append(para.text.strip())
    # Also extract from tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    paragraphs.append(cell.text.strip())
    return "\n".join(paragraphs)


def extract_text_from_file(file_path: str) -> str:
    """Auto-detect file type and extract text."""
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        raw = extract_text_from_pdf(file_path)
    elif suffix in (".docx", ".doc"):
        raw = extract_text_from_docx(file_path)
    elif suffix == ".txt":
        raw = path.read_text(encoding="utf-8", errors="replace")
    else:
        raise ValueError(f"Unsupported file format: {suffix}")
    return clean_text(raw)


def clean_text(text: str) -> str:
    """Normalize whitespace and remove noise."""
    # Replace multiple spaces with single space
    text = re.sub(r" {2,}", " ", text)
    # Replace 3+ newlines with double newline
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove non-printable characters (except newlines)
    text = re.sub(r"[^\x20-\x7E\n]", " ", text)
    return text.strip()


def validate_resume_text(text: str) -> tuple[bool, str]:
    """Check if extracted text looks like a valid resume."""
    if len(text) < 200:
        return False, "Extracted text is too short. Please upload a full resume."
    # Check for some expected sections
    lower = text.lower()
    has_contact = any(kw in lower for kw in ["email", "@", "phone", "linkedin"])
    has_experience = any(kw in lower for kw in ["experience", "work", "employment", "position"])
    has_skills = any(kw in lower for kw in ["skill", "technolog", "language", "framework"])
    if not has_contact:
        return False, "Could not find contact information. Ensure the resume includes email or phone."
    if not (has_experience or has_skills):
        return False, "Resume appears incomplete. Please upload a full resume with experience and skills sections."
    return True, "Valid resume"
