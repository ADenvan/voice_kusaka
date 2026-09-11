import logging
import os

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

logger = logging.getLogger("voice_ai.rag.pdf_loader")


class PDFDocumentLoader:
    """Loader and chunker for PDF documents."""

    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 200) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def load_from_directory(self, directory: str) -> list[Document]:
        """Load all PDF files from a directory recursively."""
        documents: list[Document] = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(".pdf"):
                    file_path = os.path.join(root, file)
                    logger.debug("Loading PDF: %s", file_path)
                    try:
                        reader = PdfReader(file_path)
                        for page_num, page in enumerate(reader.pages):
                            text = page.extract_text()
                            if text:
                                doc = Document(
                                    page_content=text,
                                    metadata={"source": file_path, "page": page_num},
                                )
                                documents.append(doc)
                    except Exception as e:
                        logger.warning("Failed to load PDF %s: %s", file_path, e)
        logger.info("Loaded %d pages from %s", len(documents), directory)
        return documents

    def split_documents(self, documents: list[Document]) -> list[Document]:
        """Split documents into chunks."""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
        )
        chunks = text_splitter.split_documents(documents)
        logger.info("Split into %d chunks (chunk_size=%d)", len(chunks), self._chunk_size)
        return chunks

    def process_directory(self, directory: str) -> list[Document]:
        """Full pipeline: load PDFs and split into chunks."""
        docs = self.load_from_directory(directory)
        if not docs:
            logger.warning("No PDF documents found in %s", directory)
            return []
        return self.split_documents(docs)

    @staticmethod
    def has_pdf_files(directory: str) -> bool:
        """Check if directory contains any PDF files."""
        if not os.path.exists(directory):
            return False
        for _, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(".pdf"):
                    return True
        return False
