import asyncio, os, json
from playwright.async_api import async_playwright

BASE = "https://sysjuros.com.br"
LOGIN = f"{BASE}/auth/log-in"
OUT = "/app/bench/out"
USER = os.environ.get("SYS_USER", "")
PASS = os.environ.get("SYS_PASS", "")

async def jclick(page, label, exact=True):
    return await page.evaluate(
        """(args) => {
            const [label, exact] = args;
            const els = Array.from(document.querySelectorAll('div,span,a,li,button'));
            const m = els.filter(e => { const x=(e.innerText||'').trim(); return e.offsetParent!==null && (exact? x===label : x.includes(label)); });
            const t = m.sort((a,b)=>a.children.length-b.children.length)[0];
            if(t){ t.click(); return (t.innerText||'').trim().slice(0,30); } return null;
        }""", [label, exact])

async def form_dump(page, name):
    await page.wait_for_timeout(2500)
    txt = await page.evaluate("() => document.body.innerText")
    fields = await page.evaluate(
        """() => Array.from(document.querySelectorAll('input,select,textarea')).filter(i=>i.offsetParent!==null).map(i=>({type:i.type, ph:i.placeholder, val:(i.value||'').slice(0,30)}))""")
    with open(f"{OUT}/{name}.txt","w") as f:
        f.write("URL: "+page.url+"\n\n=== TEXT ===\n"+txt+"\n\n=== FIELDS ===\n"+json.dumps(fields,ensure_ascii=False,indent=2))
    await page.screenshot(path=f"{OUT}/{name}.png", full_page=True)
    print(f"{name}: fields={len(fields)} textlen={len(txt)}")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path="/usr/bin/google-chrome",
                                          args=["--no-sandbox","--disable-dev-shm-usage"])
        ctx = await browser.new_context(viewport={"width":1440,"height":900})
        page = await ctx.new_page()
        await page.goto(LOGIN, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        await page.fill("input[type='email']", USER)
        await page.fill("input[type='password']", PASS)
        await page.click("button:has-text('Entrar')")
        await page.wait_for_timeout(8000)
        print("LOGGED IN:", page.url)

        # ---- CREATE TEST CLIENT ----
        await page.goto(f"{BASE}/web/customer", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)
        await page.mouse.click(1363,125)  # Cliente + button
        await page.wait_for_timeout(3000)
        # fill first + last name
        await page.fill("input[placeholder='Digite o primeiro nome']", "QABENCH")
        try:
            await page.fill("input[placeholder='Nome']", "TESTE")
        except Exception as e:
            print("lastname err", e)
        # phone (optional)
        try:
            await page.fill("input[type='tel']", "11 9 8888-7777")
        except Exception as e:
            print("phone err", e)
        r = await jclick(page, "Cadastrar")
        print("clicked cadastrar:", r)
        await page.wait_for_timeout(5000)
        await form_dump(page, "30_after_create_client")

        # ---- INSPECT PARCELADO CONTRACT TAB ----
        await page.goto(f"{BASE}/web/contract", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)
        await page.mouse.click(1357,125)  # Contrato +
        await page.wait_for_timeout(3000)
        r2 = await jclick(page, "Parcelado")
        print("clicked Parcelado:", r2)
        await page.wait_for_timeout(2500)
        await form_dump(page, "31_contract_parcelado")

        await browser.close()

asyncio.run(main())
