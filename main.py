import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import sys

sys_path_dir = str(Path(__file__).parent.resolve())
if sys_path_dir not in sys.path:
    sys.path.insert(0, sys_path_dir)

from trial.dom_compressor import compress_dom
from trial.ollama_client import discover_selectors, assemble_selectors
from trial.selector_validator import score_selectors


CONFIDENCE_THRESHOLD = 0.4
MAX_RETRIES = 3


def fetch_dom(url: str, wait_ms: int = 30000):
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(
        headless=True,
        args=["--disable-dev-shm-usage", "--disable-gpu", "--disable-background-networking"],
    )
    page = browser.new_page()
    page.route("**/*", lambda route: route.abort() if route.request.resource_type in ("image", "font", "stylesheet", "media") else route.continue_())
    page.goto(url, wait_until="domcontentloaded", timeout=wait_ms)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    html = page.content()
    title = page.title()
    final_url = page.url
    browser.close()
    playwright.stop()
    return html, title, final_url


def discover_for_url(url: str, out_path: str = None, model: str = "qwen3:8b"):
    out_path = Path(out_path) if out_path else Path(__file__).parent / "selector.json"
    print(f"[discovery] Fetching {url}")
    html, title, final_url = fetch_dom(url)
    soup = BeautifulSoup(html, "html.parser")

    dom_json = compress_dom(soup, max_tags=1500)
    print(f"[discovery] DOM compressed to {len(dom_json)} chars")

    attempt = 0
    config = None

    while attempt < MAX_RETRIES:
        attempt += 1
        print(f"[discovery] Attempt {attempt}/{MAX_RETRIES}")

        try:
            selectors = discover_selectors(dom_json, model=model)
        except Exception as e:
            print(f"[discovery] Ollama discovery failed: {e}")
            break

        if not selectors:
            print("[discovery] No selectors returned")
            continue

        config = {
            "website": "auto-detected",
            "url": final_url,
            "selectors": selectors,
        }
        config["confidence"] = score_selectors(soup, selectors)["confidence"]
        print(f"[discovery] Confidence: {config['confidence']}")

        if config["confidence"] >= CONFIDENCE_THRESHOLD:
            print("[discovery] Selectors passed confidence threshold")
            break
        else:
            print("[discovery] Confidence too low, trying again with refined prompt")
            dom_json = compress_dom(soup, max_tags=2000)
            selectors = assemble_selectors(selectors, model=model)
            config["selectors"] = selectors
            config["confidence"] = score_selectors(soup, selectors)["confidence"]
            if config["confidence"] >= CONFIDENCE_THRESHOLD:
                break

    if config is None:
        raise RuntimeError("Discovery failed after all attempts")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"[discovery] Saved selector.json to {out_path.resolve()}")
    print(json.dumps(config, indent=2, ensure_ascii=False))
    return config


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else ""
    if not url:
        url = input("Enter URL to discover selectors for: ").strip()
    if not url:
        raise SystemExit("URL required")
    out = sys.argv[2] if len(sys.argv) > 2 else ""
    discover_for_url(url, out_path=out or None)
