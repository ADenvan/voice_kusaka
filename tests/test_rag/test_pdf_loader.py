import os
import tempfile

import pytest
from langchain_core.documents import Document

from src.rag.pdf_loader import PDFDocumentLoader


def test_has_pdf_files_empty_dir() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        assert PDFDocumentLoader.has_pdf_files(tmpdir) is False


def test_has_pdf_files_nonexistent_dir() -> None:
    assert PDFDocumentLoader.has_pdf_files("/nonexistent/path") is False


def test_has_pdf_files_with_pdf() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "test.pdf")
        with open(pdf_path, "w") as f:
            f.write("fake pdf")
        assert PDFDocumentLoader.has_pdf_files(tmpdir) is True


def test_split_documents() -> None:
    loader = PDFDocumentLoader(chunk_size=10, chunk_overlap=0)
    docs = [Document(page_content="a" * 100, metadata={"source": "test.pdf"})]
    chunks = loader.split_documents(docs)
    assert len(chunks) > 1
    assert all(isinstance(c, Document) for c in chunks)


def test_load_from_directory_no_pdfs() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = PDFDocumentLoader()
        docs = loader.load_from_directory(tmpdir)
        assert docs == []


def test_process_directory_no_pdfs() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = PDFDocumentLoader()
        docs = loader.process_directory(tmpdir)
        assert docs == []
