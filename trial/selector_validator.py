from bs4 import BeautifulSoup


def validate_selector(soup_or_html, selector, min_matches=1):
    if isinstance(soup_or_html, str):
        soup = BeautifulSoup(soup_or_html, "html.parser")
    else:
        soup = soup_or_html

    try:
        return len(soup.select(selector))
    except Exception:
        return 0


def score_selectors(soup, selectors: dict) -> dict:
    scores = {}
    checks = {
        "event_container": lambda sel: validate_selector(soup, sel, min_matches=1),
        "team_selector": lambda sel: validate_selector(soup, sel, min_matches=2),
        "score_selector": lambda sel: validate_selector(soup, sel, min_matches=1),
        "market_group": lambda sel: validate_selector(soup, sel, min_matches=0),
        "market_title": lambda sel: validate_selector(soup, sel, min_matches=0),
        "outcome_button": lambda sel: validate_selector(soup, sel, min_matches=0),
        "outcome_label": lambda sel: validate_selector(soup, sel, min_matches=0),
        "outcome_price": lambda sel: validate_selector(soup, sel, min_matches=0),
    }

    total_possible = 0
    total_hits = 0

    for key, checker in checks.items():
        sel = selectors.get(key, "")
        hits = checker(sel) if sel else 0
        scores[key] = hits
        total_hits += min(hits, 10)
        total_possible += 10

    confidence = round(total_hits / max(total_possible, 1), 2) if total_possible else 0.0
    return {"confidence": confidence, "hits": scores}
