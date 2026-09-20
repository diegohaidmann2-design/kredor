import asyncio, os
from playwright.async_api import async_playwright

BASE = "https://sysjuros.com.br"
LOGIN = f"{BASE}/auth/log-in"
OUT = "/app/bench/out"
USER = os.environ.get("SYS_USER", "")
PASS = os.environ.get("SYS_PASS", "")

async def jclick(page, label):
    return await page.evaluate(
        """(label) => { const els=[...document.querySelectorAll('div,span,a,li,button')].filter(e=>(e.innerText||'').trim()===label && e.offsetParent!==null); const t=els.sort((a,b)=>a.children.length-b.children.length)[0]; if(t){t.click();return true;} return false; }""", label)

async def snap(page, name):
    await page.wait_for_timeout(2000)
    txt = await page.evaluate("() => document.body.innerText")
    with open(f"{OUT}/{name}.txt","w") as f: f.write(txt)
    await page.screenshot(path=f"{OUT}/{name}.png", full_page=True)
    # print the interesting lines
    import re
    for kw in ["Total Contrato","Valor a receber","Valor das parcelas","Custo","%"]:
        pass
    print(f"--- {name} ---")
    print(txt)

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

        # ---------- FIXO: Custo=1000, Taxa=10 ----------
        await page.goto(f"{BASE}/web/contract", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)
        await page.mouse.click(1357,125); await page.wait_for_timeout(3000)  # open form (Fixo default)
        cur = page.locator("input[placeholder='$ 0,00']")
        await cur.nth(0).fill("1000")           # Valor/Custo
        await page.locator("input[placeholder='00']").first.fill("10")  # Taxa %
        await page.wait_for_timeout(1500)
        await snap(page, "40_fixo_1000_10")

        # ---------- PARCELADO: Custo=1000, Receber=1300, 3x mensal ----------
        await jclick(page, "Parcelado"); await page.wait_for_timeout(2000)
        cur2 = page.locator("input[placeholder='$ 0,00']")
        await cur2.nth(0).fill("1000")   # Valor/Custo
        await cur2.nth(1).fill("1300")   # Valor a receber
        # numero de parcelas
        await page.locator("input[placeholder='00']").first.fill("3")
        # frequencia = Mensal (select)
        try:
            sel = page.locator("select").first
            await sel.select_option(label="Mensal")
        except Exception as e:
            print("freq select err", e)
        await page.wait_for_timeout(2000)
        await snap(page, "41_parc_1000_1300_3x")

        # cancel (no save)
        await jclick(page, "Cancelar")
        await b.close()

asyncio.run(main())
