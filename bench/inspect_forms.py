import asyncio, os, json
from playwright.async_api import async_playwright

BASE = "https://sysjuros.com.br"
LOGIN = f"{BASE}/auth/log-in"
OUT = "/app/bench/out"
USER = os.environ.get("SYS_USER", "")
PASS = os.environ.get("SYS_PASS", "")

async def form_dump(page, name):
    await page.wait_for_timeout(3500)
    txt = await page.evaluate("() => document.body.innerText")
    fields = await page.evaluate(
        """() => Array.from(document.querySelectorAll('input,select,textarea')).map(i=>({
            tag:i.tagName, type:i.type, ph:i.placeholder, name:i.name,
            val:(i.value||'').slice(0,30),
            vis: i.offsetParent!==null
        })).filter(x=>x.vis)"""
    )
    opts = await page.evaluate(
        """() => Array.from(document.querySelectorAll('select')).map(s=>({name:s.name, options:Array.from(s.options).map(o=>o.text)}))"""
    )
    with open(f"{OUT}/{name}.txt","w") as f:
        f.write("URL: "+page.url+"\n\n=== TEXT ===\n"+txt+"\n\n=== FIELDS ===\n"+json.dumps(fields,ensure_ascii=False,indent=2)+"\n\n=== SELECT OPTIONS ===\n"+json.dumps(opts,ensure_ascii=False,indent=2))
    await page.screenshot(path=f"{OUT}/{name}.png", full_page=True)
    print(f"{name}: fields={len(fields)} selects={len(opts)} textlen={len(txt)}")

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

        # CONTRACT create form
        await page.goto(f"{BASE}/web/contract", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)
        try:
            await page.mouse.click(1357,125)
            print("clicked Contrato +")
        except Exception as e:
            print("click err", e)
        await form_dump(page, "20_contract_form")

        # CUSTOMER create form
        await page.goto(f"{BASE}/web/customer", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)
        # find the top-right create button 'Cliente'
        pos = await page.evaluate(
            """() => { const els=[...document.querySelectorAll('button,div,span')].filter(e=>(e.innerText||'').trim()==='Cliente' && e.offsetParent!==null);
                if(!els.length) return null; const r=els[0].getBoundingClientRect(); return {x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)};}"""
        )
        print("cliente btn pos:", pos)
        if pos:
            await page.mouse.click(pos["x"], pos["y"])
        await form_dump(page, "21_customer_form")

        await browser.close()

asyncio.run(main())
