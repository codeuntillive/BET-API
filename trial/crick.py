import json
import time
import hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup


class LiveScraper:
    def __init__(self, config_path):
        self.config_path = Path(config_path)
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.url = self.config["url"]
        self.website = self.config.get("website", "unknown")
        self.selectors = self.config["selectors"]
        self.last_hash = None
        self._page = None
        self._browser = None
        self._playwright = None

    def _block_resources(self, route):
        if route.request.resource_type in ("image", "font", "stylesheet", "media"):
            route.abort()
        else:
            route.continue_()

    def start(self):
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--disable-gpu", "--disable-background-networking"]
        )
        self._page = self._browser.new_page()
        self._page.route("**/*", self._block_resources)
        self._page.goto(self.url, wait_until="domcontentloaded", timeout=30000)
        try:
            self._page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        print(f"Connected to {self.url}")

    def _safe_text(self, el):
        try:
            txt = el.get_text(separator=" ", strip=True)
            return txt if txt else ""
        except Exception:
            return ""

    def parse_teams_and_scores(self, card):
        team_selector = self.selectors.get("team_selector", "")
        score_selector = self.selectors.get("score_selector", "")

        teams = []
        if team_selector:
            for te in card.select(team_selector):
                name = self._safe_text(te)
                if name:
                    teams.append(name)

        scores = []
        if score_selector:
            for se in card.select(score_selector):
                score = self._safe_text(se)
                if score:
                    scores.append(score)

        paired = []
        for i, team in enumerate(teams):
            score = scores[i] if i < len(scores) else "N/A"
            paired.append({"team": team, "score": score})

        if not paired:
            text = self._safe_text(card)
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if len(lines) >= 2:
                paired.append({"team": lines[0], "score": lines[1] if len(lines) > 1 else "N/A"})
            elif len(lines) == 1:
                paired.append({"team": lines[0], "score": "N/A"})

        return paired

    def parse_markets(self, card):
        markets = []
        market_selector = self.selectors.get("market_group", "")
        market_title_sel = self.selectors.get("market_title", "")
        outcome_label_sel = self.selectors.get("outcome_label", "")
        outcome_price_sel = self.selectors.get("outcome_price", "")

        if not market_selector:
            return markets

        for me in card.select(market_selector):
            market = {}
            if market_title_sel:
                title = me.select_one(market_title_sel)
                if title:
                    market["market_name"] = self._safe_text(title)

            outcomes = []
            if outcome_label_sel and outcome_price_sel:
                for ob in me.select("[data-testid='outcome-button']"):
                    label_el = ob.select_one(outcome_label_sel)
                    price_el = ob.select_one(outcome_price_sel)
                    outcome = {}
                    if label_el:
                        outcome["label"] = self._safe_text(label_el)
                    if price_el:
                        outcome["price"] = self._safe_text(price_el)
                    if outcome:
                        outcomes.append(outcome)

            if outcomes:
                market["outcomes"] = outcomes
                markets.append(market)

        return markets

    def scrape(self):
        if not self._page:
            return {"error": "Browser not started"}

        self._page.reload(wait_until="domcontentloaded")
        try:
            self._page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        soup = BeautifulSoup(self._page.content(), "html.parser")
        event_selector = self.selectors.get("event_container", "div[data-slot='event-card']")
        cards = soup.select(event_selector)

        data = {
            "website": self.website,
            "url": self._page.url,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "event_count": len(cards),
            "events": []
        }

        for card in cards:
            event = {
                "teams": self.parse_teams_and_scores(card),
                "markets": self.parse_markets(card),
            }
            data["events"].append(event)

        return data

    def data_hash(self, data):
        return hashlib.md5(
            json.dumps(data, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()

    def run(self, interval=0.2):
        try:
            while True:
                data = self.scrape()
                current_hash = self.data_hash(data)
                if current_hash != self.last_hash:
                    self.last_hash = current_hash
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                time.sleep(interval)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        try:
            if self._page:
                self._page.close()
        except Exception:
            pass
        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass


if __name__ == "__main__":
    import sys
    config_path = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).parent / "selector.json")
    scraper = LiveScraper(config_path)
    scraper.start()
    scraper.run(0.2)
