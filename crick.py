from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import time
import os

class BetScraper:
    def __init__(self, url):
        self.url = url
        self._p = None
        self._browser = None
        self._page = None

    def _abort_media(self, route):
        if route.request.resource_type in ["image", "font", "stylesheet"]:
            return route.abort()
        return route.continue_()

    def start(self):
        self._p = sync_playwright().start()
        self._browser = self._p.chromium.launch(headless=True)
        self._page = self._browser.new_page()
        self._page.route("**/*", self._abort_media)
        self._page.goto(self.url, wait_until="domcontentloaded")
        self._page.wait_for_selector('div[data-slot="event-card"]', timeout=15000)

    def parse_cards(self):
        self._page.reload(wait_until="domcontentloaded")
        self._page.wait_for_selector('div[data-slot="event-card"]', timeout=15000)
        soup = BeautifulSoup(self._page.content(), "html.parser")
        cards = soup.select('div[data-slot="event-card"]')
        events = []
        for card in cards:
            event = {}
            teams = card.select('[data-testid^="scoresbar-opponent"]')
            scores = card.select('.text-right.text-xs')
            event["teams"] = []
            for i, team in enumerate(teams):
                team_name = team.text.strip()
                score = scores[i].text.strip() if i < len(scores) else "N/A"
                event["teams"].append({"name": team_name, "score": score})
            time_elem = card.select_one('span.label-small.text-th-highlight-primary')
            if time_elem:
                event["time"] = time_elem.text.strip()
            market_count_elem = card.select_one('[data-testid="marketCount"]')
            if market_count_elem:
                event["market_count"] = market_count_elem.text.strip()
            markets = []
            for market in card.select('[data-testid="market-group"]'):
                outcomes = []
                for outcome in market.select('[data-testid="outcome-button"]'):
                    label_elem = outcome.select_one('[data-testid="outcome-label"]')
                    price_elem = outcome.select_one('[data-testid="outcome-price"]')
                    if label_elem and price_elem:
                        outcomes.append({"label": label_elem.text.strip(), "price": price_elem.text.strip()})
                    elif price_elem:
                        outcomes.append({"price": price_elem.text.strip()})
                markets.append({"outcomes": outcomes})
            event["markets"] = markets
            events.append(event)
        return events

    def run(self):
        os.system("cls" if os.name == "nt" else "clear")
        try:
            while True:
                data = self.parse_cards()
                os.system("cls" if os.name == "nt" else "clear")
                print(json.dumps(data, indent=2))
                time.sleep(0.200)
        finally:
            self.stop()

    def stop(self):
        try:
            if self._browser:
                self._browser.close()
            if self._p:
                self._p.stop()
        except Exception:
            pass


if __name__ == "__main__":
    url = input("Enter URL: ").strip() or "https://sports.indiadafa.com/en/sports/215-CRIC"
    scraper = BetScraper(url)
    scraper.start()
    scraper.run()
