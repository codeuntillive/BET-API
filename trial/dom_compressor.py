from bs4 import BeautifulSoup
import json


def compress_dom(soup_or_html, max_tags=2000):
    if isinstance(soup_or_html, str):
        soup = BeautifulSoup(soup_or_html, "html.parser")
    else:
        soup = soup_or_html

    result = []
    for tag in soup.find_all(True):
        attrs = {}
        if tag.get("class"):
            try:
                attrs["class"] = list(tag.get("class"))
            except Exception:
                pass
        if tag.get("data-testid"):
            attrs["data-testid"] = tag.get("data-testid")
        if tag.get("data-slot"):
            attrs["data-slot"] = tag.get("data-slot")

        text = tag.get_text(strip=True)
        if text:
            text = text[:50]

        result.append({
            "tag": tag.name,
            "attrs": attrs,
            "text": text,
        })
        if len(result) >= max_tags:
            break

    return json.dumps(result, ensure_ascii=False)
