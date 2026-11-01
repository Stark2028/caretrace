"""Check the real review workflow at desktop and mobile sizes."""
import argparse
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright


async def run(args):
    output = Path(args.screenshots)
    output.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        options = {"headless": True}
        if args.executable:
            options["executable_path"] = args.executable
        browser = await playwright.chromium.launch(**options)
        for name, width, height in (("desktop", 1440, 1050), ("mobile", 390, 844)):
            page = await browser.new_page(viewport={"width": width, "height": height})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            await page.goto(args.url, wait_until="networkidle")
            await page.locator("#example").click()
            await page.locator("#extract").click()
            await page.locator(".order").first.wait_for(timeout=15000)
            assert await page.locator("#engine").inner_text() == "SOURCE EXTRACTOR"
            await page.locator(".turn-link").first.click()
            assert await page.locator(".source-turn.selected").count() == 1
            await page.get_by_role("button", name="Accept", exact=True).first.click()
            assert await page.get_by_role("button", name="Accept", exact=True).first.get_attribute("aria-pressed") == "true"
            assert await page.evaluate("document.documentElement.scrollWidth") <= width
            await page.screenshot(path=str(output / f"{name}.png"), full_page=True)
            await page.locator("#transcript").fill("Doctor: Changed transcript.")
            assert await page.locator(".order").count() == 0
            assert await page.locator("#evidence-section").is_hidden()
            assert not errors, errors
            print(f"{name}: evidence, review, stale invalidation, layout and console passed")
            await page.close()
        await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--executable", help="Optional installed Chromium/Edge executable")
    parser.add_argument("--screenshots", default=".tmp/screenshots")
    asyncio.run(run(parser.parse_args()))
