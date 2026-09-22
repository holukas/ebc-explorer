"""Find reference PDFs in the Zotero export under refs/EBC/files/<id>/."""

from ebc_explorer.paths import REFS_EBC


def find_refs(author, year=None):
    """PDF paths whose file name starts with `author` (case-insensitive), optionally of `year`.

    Zotero names files "<Author> [et al.|and X] - <Year> - <Title>.pdf".
    """
    author = author.lower()
    hits = []
    for pdf in sorted((REFS_EBC / "files").glob("*/*.pdf")):
        name = pdf.name.lower()
        if name.startswith(author) and (year is None or f" - {year} - " in name):
            hits.append(pdf)
    return hits


def pdf_text(path):
    """Plain text of a PDF (needs pypdf: `uv run --with pypdf ...` or `uv add pypdf`)."""
    import pypdf

    reader = pypdf.PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)
