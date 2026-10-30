"""把文件读成纯文本。解析是脏活，这一层只负责"拿到文字"，不做切分。"""

import string
from pathlib import Path

from pypdf import PdfReader

SUPPORTED = {".md", ".markdown", ".txt", ".pdf", ".rst"}


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


def _adornment_char(line: str) -> str | None:
    """整行是同一个标点重复（至少 4 个）就返回这个标点，否则 None。

    "=====  =====" 这种表格边框中间有空格，set 里会多出 " "，不算。
    """
    line = line.rstrip()
    if len(line) < 4 or len(set(line)) != 1:
        return None
    return line[0] if line[0] in string.punctuation else None


def rst_to_markdown_headings(text: str) -> str:
    """把 rst 标题改写成 Markdown 的 '#' 行，这样 chunk_by_heading 不用改。

    rst 的层级不看符号，看"在本文件里第一次出现的顺序"：
    第一种样式是 1 级，第二种是 2 级……而且"有上划线"和"只有下划线"算两种样式。
    """
    lines = text.splitlines()
    levels: dict[tuple[str, bool], int] = {}  # (符号, 有无上划线) → 层级
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        ch = _adornment_char(nxt)

        # 上划线已经在上一轮被当普通行放进 out 了
        has_overline = ch is not None and bool(out) and _adornment_char(out[-1]) == ch
        is_title = (
            ch is not None
            and line.strip() != ""  # 挡掉分隔线（transition）：它上面是空行
            # 挡掉缩进代码块里的假标题；但带上划线的标题允许缩进居中
            and (has_overline or not line[0].isspace())
            and len(line.rstrip()) <= len(nxt.rstrip())
        )
        if not is_title:
            out.append(line)
            i += 1
            continue

        if has_overline:  # 撤回上划线
            out.pop()

        style = (ch, has_overline)
        if style not in levels:
            levels[style] = len(levels) + 1
        out.append("#" * min(levels[style], 6) + " " + line.strip())
        i += 2  # 标题行 + 下划线
    return "\n".join(out)


def load_rst(path: Path) -> str:
    return rst_to_markdown_headings(load_text(path))


def load(path: str | Path) -> str:
    """按后缀分派。不认识的格式直接报错，不要静默返回空字符串。"""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED:
        raise ValueError(f"不支持的文件类型 {suffix}，目前支持 {sorted(SUPPORTED)}")
    if suffix == ".pdf":
        return load_pdf(path)
    if suffix == ".rst":
        return load_rst(path)
    return load_text(path)
