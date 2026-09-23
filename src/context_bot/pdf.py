from pathlib import Path

import pdfplumber


def extract_text(file_path: Path) -> str:
    """Extract text from all readable pages of a PDF document."""
    pages: list[str] = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=2, y_tolerance=2)
            if text:
                pages.append(text)
    return "\n".join(pages)
