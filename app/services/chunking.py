def chunk_sections(sections: list[dict], chunk_size: int = 700, overlap: int = 120) -> list[str]:
    parts = []
    for section in sections:
        heading = str(section.get("heading") or "").strip()
        content = str(section.get("content") or "").strip()
        if not content:
            continue
        if heading:
            parts.append(f"{heading}\n{content}")
        else:
            parts.append(content)
    text = "\n\n".join(parts)
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks
