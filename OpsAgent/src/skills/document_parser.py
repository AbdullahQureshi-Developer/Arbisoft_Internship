import io
import logging
from typing import Optional
from markitdown import MarkItDown

from src.hooks.logging_hook import log_call

logger = logging.getLogger(__name__)

_markitdown_instance: Optional[MarkItDown] = None


def _get_markitdown() -> MarkItDown:
    global _markitdown_instance
    if _markitdown_instance is None:
        _markitdown_instance = MarkItDown()
    return _markitdown_instance


@log_call
def parse_document(file_bytes: bytes, filename: str) -> str:
    """
    Converts PDF, DOCX, and other document file bytes to clean Markdown text
    using Microsoft's MarkItDown library via convert_stream().
    """
    if not file_bytes:
        return ""

    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    file_ext = f".{ext}" if ext else ""

    try:
        md = _get_markitdown()
        stream = io.BytesIO(file_bytes)
        result = md.convert_stream(stream, file_extension=file_ext)
        if result and hasattr(result, "text_content"):
            return result.text_content
        elif result and hasattr(result, "content"):
            return str(result.content)
        return str(result)
    except Exception as e:
        logger.error(f"Error parsing document '{filename}' with MarkItDown: {e}")
        raise ValueError(f"Failed to parse document '{filename}': {e}")

