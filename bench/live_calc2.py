import asyncio, os
from playwright.async_api import async_playwright

BASE = "https://sysjuros.com.br"
LOGIN = f"{BASE}/auth/log-in"
OUT = "/app/bench/out"
USER = os.environ.get("SYS_USER", "")
PASS = os.environ.get("SYS_PASS", "")

async def snap(page, name):
    await page.wait_for_timeout(1800)
    txt = await page.evaluate("() => document.body.innerText")
    with open(f"{OUT}/{name}.txt","w") as f: f.write(txt)
    await page.screenshot(path=f"{OUT}/{name}.png", full_page=True)
    print(f"--- {name} ---\n{txt}\n")

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox","--disable-dev-shm-usage"])
        ctx = await b.new_context(viewport={"width":1440,"height":900})
        page = await ctx.new_page()
        await page.goto(LOGIN, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        await page.fill("input[type='email']", USER); await page.fill("input[type='password']", PASS)
        await page.click("button:has-text('Entrar')"); await page.wait_for_timeout(8000)
        print("LOGGED IN:", page.url)

        await page.goto(f"{BASE}/web/contract", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)
        await page.mouse.click(1357,125); await page.wait_for_timeout(3000)

        # ---- switch to Parcelado tab ----
        try:
            await page.get_by_text("Parcelado", exact=True).first.click()
            print("clicked Parcelado tab")
        except Exception as e:
            print("tab err", e)
        await page.wait_for_timeout(2500)

        vis = "input[placeholder='$ 0,00']:visible"
        n = await page.locator(vis).count()
        print("visible currency inputs:", n)
        try:
            await page.locator(vis).nth(0).fill("1000")   # Valor/Custo
            await page.locator(vis).nth(1).fill("1300")   # Valor a receber
            await page.locator("input[placeholder='00']:visible").first.fill("3")  # parcelas
            print("filled parcelado")
        except Exception as e:
            print("fill err parcelado", e)
        # frequencia
        try:
            await page.locator("select:visible").first.select_option(label="Mensal")
        except Exception as e:
            print("freq err", e)
        await snap(page, "42_parc_1000_1300_3x")

        # ---- also test Fixo taxa additive: switch back ----
        try:
            await page.get_by_text("Fixo", exact=True).first.click()
            await page.wait_for_timeout(2000)
            fvis = "input[placeholder='$ 0,00']:visible"
            await page.locator(fvis).nth(0).fill("1000")     # Custo
            await page.locator("input[placeholder='00']:visible").first.fill("10")  # Taxa %
            await snap(page, "43_fixo_1000_taxa10")
        except Exception as e:
            print("fixo err", e)

        await page.get_by_text("Cancelar", exact=True).first.click()
        await b.close()

asyncio.run(main())
