from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import time

def analyze_page(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font", "stylesheet", "media"] else route.continue_())
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        cards = soup.select('div[data-slot="event-card"]')
        print(f"\n{'='*60}")
        print(f"URL: {url}")
        print(f"Total event cards found: {len(cards)}")
        print(f"{'='*60}\n")

        if not cards:
            print("NO EVENT CARDS FOUND!")
            print("\n=== PAGE TITLE ===")
            print(soup.title.string if soup.title else "No title")
            print("\n=== FIRST 5000 CHARS OF BODY ===")
            body = soup.body
            if body:
                print(str(body)[:5000])
            browser.close()
            return None

        print("=== SAMPLE CARD 1 INNER HTML ===")
        print(cards[0].prettify()[:4000])

        print("\n=== UNIQUE CLASSES IN EVENT CARDS ===")
        all_classes = set()
        for card in cards:
            for el in card.find_all(True):
                if el.get("class"):
                    all_classes.update(el.get("class"))
        for cls in sorted(all_classes):
            print(f"  .{cls}")

        print("\n=== ALL data-testid ATTRIBUTES IN EVENT CARDS ===")
        testids = set()
        for card in cards:
            for el in card.find_all(True):
                tid = el.get("data-testid")
                if tid:
                    testids.add(tid)
        for tid in sorted(testids):
            print(f"  [data-testid='{tid}']")

        print("\n=== SUGGESTED SELECTORS (based on first card) ===")
        suggested = {
            "event_container": "div[data-slot='event-card']",
        }

        # Try to find league
        league = cards[0].select_one('[class*="league"]') or cards[0].select_one('[data-testid*="league"]')
        if league:
            classes = " ".join(league.get("class", []))
            suggested["league_name"] = f".{classes.split()[0]}" if classes else None

        # Try to find team names
        team_candidates = cards[0].select('[data-testid*="opponent"]') or cards[0].select('[class*="team"]')
        if len(team_candidates) >= 2:
            for i, tc in enumerate(team_candidates[:2]):
                classes = " ".join(tc.get("class", []))
                suggested["team_home" if i == 0 else "team_away"] = f".{classes.split()[0]}" if classes else tc.get("data-testid")

        # Try to find scores
        score_candidates = cards[0].select('[class*="score"]')
        if len(score_candidates) >= 2:
            for i, sc in enumerate(score_candidates[:2]):
                classes = " ".join(sc.get("class", []))
                suggested["score_home" if i == 0 else "score_away"] = f".{classes.split()[0]}" if classes else sc.get("data-testid")
        else:
            # fallback: text-right text-xs
            suggested["score_home"] = ".text-right.text-xs"
            suggested["score_away"] = ".text-right.text-xs"

        # Time
        time_el = cards[0].select_one('[class*="time"]') or cards[0].select_one('[class*="label-small"]')
        if time_el:
            classes = " ".join(time_el.get("class", []))
            suggested["event_time"] = f".{classes.split()[0]}" if classes else None

        print(json.dumps(suggested, indent=2))

        browser.close()
        return suggested

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else ""
    if not url:
        url = "https://sports.indiadafa.com/en/sports/215-CRIC"
    analyze_page(url)
