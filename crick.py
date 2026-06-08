from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time

url = "https://sports.indiadafa.com/en/live/sport/215-CRIC"

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True
    )

    page = browser.new_page()

    # optional faster loading
    page.route(
        "**/*",
        lambda route: route.abort()
        if route.request.resource_type in ["image", "font", "stylesheet"]
        else route.continue_()
    )

    page.goto(url, wait_until="domcontentloaded")

    # IMPORTANT
    page.wait_for_selector('div[data-slot="event-card"]', timeout=15000)

    while True:

        page.reload(wait_until="domcontentloaded")

        # wait until cards appear
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
                '.text-right.text-xs'
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

        time.sleep(0.200)

    browser.close()