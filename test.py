from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time

url = "https://sports.indiadafa.com/en/live/sport/240-FOOT"

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True
    )

    page = browser.new_page()

    page.route(
        "**/*",
        lambda route: route.abort()
        if route.request.resource_type in ["image", "font", "stylesheet"]
        else route.continue_()
    )

    page.goto(url, wait_until="domcontentloaded")

    page.wait_for_selector('div[data-slot="event-card"]', timeout=15000)

    while True:
        page.reload(wait_until="domcontentloaded")

        page.wait_for_selector(
            'div[data-slot="event-card"]',
            timeout=15000
        )

        soup = BeautifulSoup(page.content(), "html.parser")

        cards = soup.select('div[data-slot="event-card"]')

        print("\nTotal cards found:", len(cards))

        for card in cards:
            teams = card.select(
                '[data-testid^="scoresbar-opponent"]'
            )

            scores = card.select(
                '[data-testid="score"]'
            )

            print("\n================")

            for i, team in enumerate(teams):
                team_name = team.text.strip()
                score = (
                    scores[i].text.strip()
                    if i < len(scores)
                    else "N/A"
                )
                print(team_name, "-", score)

            time_elements = card.select('span.label-small.text-th-highlight-primary')
            if time_elements:
                print("Time:", time_elements[0].text.strip())

            market_counts = card.select('[data-testid="marketCount"]')
            if market_counts:
                print("Market Count:", market_counts[0].text.strip())

            markets = card.select('[data-testid="market-group"]')
            for market in markets:
                outcomes = market.select('[data-testid="outcome-button"]')
                for outcome in outcomes:
                    label_elem = outcome.select_one('[data-testid="outcome-label"]')
                    price_elem = outcome.select_one('[data-testid="outcome-price"]')
                    
                    if label_elem and price_elem:
                        print(f"  {label_elem.text.strip()}: {price_elem.text.strip()}")
                    elif price_elem:
                        print(f"  Price: {price_elem.text.strip()}")

        time.sleep(0.200)

    browser.close()