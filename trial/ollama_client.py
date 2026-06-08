import json
from ollama import chat


SELECTOR_SCHEMA = {
    "event_container": "string",
    "team_selector": "string",
    "score_selector": "string",
    "market_group": "string",
    "market_title": "string",
    "outcome_button": "string",
    "outcome_label": "string",
    "outcome_price": "string",
}


PASS_PROMPTS = {
    "containers": """You are an expert web scraping engineer.
Given compressed DOM JSON from a sportsbook page, identify ONLY the CSS selector(s) for the repeatable event / match container (the wrapper that holds one match and its markets). Favours data-testid, data-slot, then semantic class names. Discard nav, ads, scripts, footer, header. Return ONLY JSON: {"event_container": "..."}""",

    "teams": """You are an expert web scraping engineer.
Given compressed DOM JSON from a sportsbook page, identify the CSS selector that matches ALL team / participant names inside a match card. Do NOT include scores or prices. Return ONLY JSON: {"team_selector": "..."}""",

    "scores": """You are an expert web scraping engineer.
Given compressed DOM JSON from a sportsbook page, identify the CSS selector for the score element(s) that appear next to or inside the team name rows inside each match card. Return ONLY JSON: {"score_selector": "..."}""",

    "markets": """You are an expert web scraping engineer.
Given compressed DOM JSON from a sportsbook page, identify:
 - market_group: selector for a single market block (e.g. Match Odds / Total Runs) inside a match card
 - outcome_button: selector for a clickable odds row inside a market
 - outcome_label: selector for the bet label (e.g. Home / Away / OVER) inside the outcome button
 - outcome_price: selector for the price / odds number inside the outcome button
 Return ONLY JSON: {"market_group": "...", "outcome_button": "...", "outcome_label": "...", "outcome_price": "..."}""",

    "assemble": """You are an expert web scraping engineer.
Return a selector config with these keys: event_container, team_selector, score_selector, market_group, market_title, outcome_button, outcome_label, outcome_price.
Prefer: data-testid > data-slot > id > indexed class + tag. Keep selectors short and robust. Do NOT add new keys. Return ONLY JSON.""",
}


def _chat(model, user_content, timeout=120):
    messages = [{"role": "user", "content": user_content}]
    response = chat(model=model, messages=messages, options={"num_predict": 400})
    text = response["message"]["content"].strip()
    # strip code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    return json.loads(text)


def discover_selectors(dom_json, model="qwen3:8b", passes=("containers", "teams", "scores", "markets")):
    selectors = {}

    for key in passes:
        prompt = PASS_PROMPTS[key].strip() + "\n\n" + dom_json
        try:
            result = _chat(model, prompt)
            for k, v in result.items():
                if isinstance(v, str) and v.strip():
                    selectors[k] = v.strip()
        except Exception as e:
            print(f"[ollama] pass {key} failed: {e}")

    if not selectors:
        raise RuntimeError("Ollama returned no selectors")

    return selectors


def assemble_selectors(partial_selectors, model="qwen3:8b"):
    prompt = PASS_PROMPTS["assemble"] + "\n\nKnown:\n" + json.dumps(partial_selectors, ensure_ascii=False)
    try:
        return _chat(model, prompt)
    except Exception as e:
        print(f"[ollama] assemble failed: {e}")
        return partial_selectors
