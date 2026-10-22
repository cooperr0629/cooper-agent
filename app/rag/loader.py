"""把文件读成纯文本。解析是脏活，这一层只负责"拿到文字"，不做切分。"""

from pathlib import Path

from pypdf import PdfReader

SUPPORTED = {".md", ".markdown", ".txt", ".pdf"}


def load_pdf(path: Path) -> str:
    """逐页抽取文字，页之间用换行隔开。

    注意：pypdf 只能处理文本型 PDF。扫描件（图片）抽出来是空的，
    那种要 OCR，等真遇到了再换 pymupdf4llm / MinerU。
    """
    reader = PdfReader(path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load(path: str | Path) -> str:
    """按后缀分派。不认识的格式直接报错，不要静默返回空字符串。"""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED:
        raise ValueError(f"不支持的文件类型 {suffix}，目前支持 {sorted(SUPPORTED)}")
    if suffix == ".pdf":
        return load_pdf(path)
    return load_text(path)
