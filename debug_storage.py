"""
Diagnostic: log into saucedemo, print storage_state, then verify a new
context with that state lands on inventory (not login).
"""
import asyncio
import json
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )

        # ── Step 1: login in context A ───────────────────────────────────────
        ctx_a = await browser.new_context(viewport={"width": 1280, "height": 800})
        page_a = await ctx_a.new_page()
        await page_a.goto("https://www.saucedemo.com")
        await page_a.wait_for_load_state("networkidle", timeout=15000)

        print(f"Before login URL: {page_a.url}")

        # fill login form
        await page_a.locator("input[name='user-name'], input[placeholder*='user' i]").first.fill("standard_user")
        await page_a.locator("input[type='password']").first.fill("secret_sauce")
        await page_a.locator("input[type='submit'], button[type='submit']").first.click()
        await page_a.wait_for_load_state("networkidle", timeout=15000)

        print(f"After login URL: {page_a.url}")

        # capture storage state
        state = await ctx_a.storage_state()
        print(f"\n--- storage_state keys: {list(state.keys())}")
        print(f"Cookies count: {len(state.get('cookies', []))}")
        origins = state.get("origins", [])
        print(f"Origins count: {len(origins)}")
        for o in origins:
            print(f"  origin: {o['origin']}")
            for item in o.get("localStorage", []):
                print(f"    localStorage[{item['name']}] = {item['value']!r}")

        await ctx_a.close()

        # ── Step 2: new context B with that storage state ───────────────────
        print("\n--- Creating new context with storage_state ---")
        ctx_b = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            storage_state=state,
        )
        page_b = await ctx_b.new_page()
        await page_b.goto("https://www.saucedemo.com")
        await page_b.wait_for_load_state("networkidle", timeout=15000)
        print(f"Context B landed on: {page_b.url}")

        # also print what localStorage looks like from JS
        ls = await page_b.evaluate("JSON.stringify(Object.entries(localStorage))")
        print(f"Context B localStorage (from JS): {ls}")

        await ctx_b.close()
        await browser.close()


asyncio.run(main())
