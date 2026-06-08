import json
import time
import hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright


class LiveScraper:

    def __init__(self, config_path):
        self.config_path = Path(config_path)

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.url = self.config["url"]
        self.website = self.config.get("website", "unknown")

        self.event_selector = self.config["selectors"]["event_container"]
        self.fields = {k: v for k, v in self.config["selectors"].items() if k != "event_container"}

        self.last_hash = None

    def block_resources(self, route):

        if route.request.resource_type in (
            "image",
            "font",
            "stylesheet",
            "media"
        ):
            route.abort()
        else:
            route.continue_()

    def start(self):

        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-background-networking"
            ]
        )

        self.page = self.browser.new_page()

        self.page.route("**/*", self.block_resources)

        self.page.goto(
            self.url,
            wait_until="domcontentloaded",
            timeout=30000
        )

        print("Connected")

    def safe_text(self, locator):

        try:
            txt = locator.text_content(timeout=100)

            if txt:
                return txt.strip()

        except:
            pass

        return ""

    def scrape(self):

        events = []

        cards = self.page.locator(self.event_selector)

        count = cards.count()

        for i in range(count):

            card = cards.nth(i)

            row = {}

            for field_name, selector in self.fields.items():

                try:
                    value = self.safe_text(
                        card.locator(selector).first
                    )

                    row[field_name] = value

                except:
                    row[field_name] = ""

            events.append(row)

        return {
            "website": self.website,
            "timestamp": time.time(),
            "event_count": count,
            "events": events
        }

    def data_hash(self, data):

        return hashlib.md5(
            json.dumps(
                data,
                sort_keys=True,
                ensure_ascii=False
            ).encode()
        ).hexdigest()

    def run(self, interval=0.2):

        try:

            while True:

                data = self.scrape()

                current_hash = self.data_hash(data)

                if current_hash != self.last_hash:

                    self.last_hash = current_hash

                    print(
                        json.dumps(
                            data,
                            indent=2,
                            ensure_ascii=False
                        )
                    )

                time.sleep(interval)

        except KeyboardInterrupt:
            pass

        finally:
            self.stop()

    def stop(self):

        try:
            self.browser.close()
            self.playwright.stop()
        except:
            pass


if __name__ == "__main__":
        config_path = input(
            "selector.json path: "
        ).strip()

        if not config_path:
            config_path = Path(__file__).parent / "selector.json"
        elif not Path(config_path).exists():
            config_path = Path(__file__).parent / config_path

        scraper = LiveScraper(config_path)

        scraper.start()

        scraper.run(0.2)