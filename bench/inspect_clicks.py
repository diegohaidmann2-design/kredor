import asyncio, os, json
from playwright.async_api import async_playwright

BASE = "https://sysjuros.com.br"
LOGIN = f"{BASE}/auth/log-in"
OUT = "/app/bench/out"
USER = os.environ.get("SYS_USER", "")
PASS = os.environ.get("SYS_PASS", "")

async def clickables(page):
    return await page.evaluate(
        """() => {
            const out = [];
            const els = Array.from(document.querySelectorAll('*'));
            for (const e of els) {
                const s = getComputedStyle(e);
                if (s.cursor === 'pointer' && e.offsetParent !== null) {
                    const r = e.getBoundingClientRect();
                    if (r.width>0 && r.height>0 && r.width<600) {
                        out.push({
                            t: (e.innerText||'').trim().slice(0,40),
                            tag: e.tagName,
                            cls: (e.className||'').toString().slice(0,40),
                            x: Math.round(r.x+r.width/2),
                            y: Math.round(r.y+r.height/2),
                            w: Math.round(r.width), h: Math.round(r.height)
                        });
                    }
                }
            }
            // dedupe by x,y
            const seen = new Set(); const res=[];
            for (const o of out){ const k=o.x+','+o.y; if(!seen.has(k)){seen.add(k);res.push(o);} }
            return res;
        }"""
    )

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

        for route in ["customer","contract"]:
            await page.goto(f"{BASE}/web/{route}", wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)
            cl = await clickables(page)
            with open(f"{OUT}/click_{route}.json","w") as f:
                json.dump(cl, f, ensure_ascii=False, indent=2)
            print(f"=== {route}: {len(cl)} clickables ===")
            for c in cl:
                print(f"  ({c['x']},{c['y']}) {c['tag']} w{c['w']}h{c['h']} '{c['t']}'")
        await browser.close()

asyncio.run(main())
