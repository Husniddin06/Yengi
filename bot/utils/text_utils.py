import re
from html import escape

MAX_MESSAGE_LEN = 4000

def split_message(text: str, limit: int = MAX_MESSAGE_LEN):
    chunks = []
    while len(text) > limit:
        cut = text.rfind('\n', 0, limit)
        if cut == -1:
            cut = text.rfind(' ', 0, limit)
        if cut == -1 or cut < limit // 2:
            cut = limit
        chunks.append(text[:cut])
        text = text[cut:].lstrip()
    if text:
        chunks.append(text)
    return chunks

_md_code_block_re = re.compile(r'```(?:[a-zA-Z0-9_+\-]*)\n?(.*?)```', flags=re.DOTALL)
_md_inline_code_re = re.compile(r'`([^`\n]+)`')
_md_bold_re = re.compile(r'\*\*(.+?)\*\*', flags=re.DOTALL)
_md_italic_re = re.compile(r'(?<!\*)\*(?!\*)([^*\n]+?)(?<!\*)\*(?!\*)')

def markdown_to_html(text: str) -> str:
    text = escape(text)
    text = _md_code_block_re.sub(lambda m: f"<pre>{m.group(1)}</pre>", text)
    text = _md_inline_code_re.sub(lambda m: f"<code>{m.group(1)}</code>", text)
    text = _md_bold_re.sub(lambda m: f"<b>{m.group(1)}</b>", text)
    text = _md_italic_re.sub(lambda m: f"<i>{m.group(1)}</i>", text)
    return text
