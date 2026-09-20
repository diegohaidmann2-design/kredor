import asyncio, os, json, re
from playwright.async_api import async_playwright

BASE = "https://sysjuros.com.br"
LOGIN = f"{BASE}/auth/log-in"
OUT = "/app/bench/out"
os.makedirs(OUT, exist_ok=True)

USER = os.environ.get("SYS_USER", "")
PASS = os.environ.get("SYS_PASS", "")

# passive network log (path only, strip query strings to avoid leaking tokens)
net = []

def on_request(req):
    try:
        if req.resource_type in ("xhr", "fetch"):
            u = req.url.split("?")[0]
            net.append({"m": req.method, "u": u, "rt": req.resource_type})
    except Exception:
        pass

async def dump(page, name):
    try:
        await page.wait_for_timeout(2500)
        txt = await page.evaluate("() => document.body ? document.body.innerText : ''")
        links = await page.evaluate(
            "() => Array.from(document.querySelectorAll('a[href]')).map(a=>({t:(a.innerText||'').trim().slice(0,60), h:a.getAttribute('href')}))"
        )
        with open(f"{OUT}/{name}.txt", "w") as f:
            f.write("URL: " + page.url + "\n\n=== INNER TEXT ===\n" + (txt or "") )
            f.write("\n\n=== LINKS ===\n")
            for l in links:
                f.write(f"[{l['t']}] -> {l['h']}\n")
        await page.screenshot(path=f"{OUT}/{name}.png", full_page=True)
        print(f"DUMP {name} url={page.url} textlen={len(txt or '')} links={len(links)}")
        return links
    except Exception as e:
        print(f"DUMP-ERR {name}: {e}")
        return []

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await ctx.new_page()
        page.on("request", on_request)

        # 1) LOGIN
        await page.goto(LOGIN, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        await page.screenshot(path=f"{OUT}/00_login.png", full_page=True)

        # discover input structure
        inputs = await page.evaluate(
            "() => Array.from(document.querySelectorAll('input')).map(i=>({type:i.type,ph:i.placeholder,name:i.name,id:i.id}))"
        )
        print("LOGIN INPUTS:", json.dumps(inputs, ensure_ascii=False))

        # fill email + password by type
        try:
            email_sel = "input[type='email']"
            if await page.query_selector(email_sel) is None:
                email_sel = "input[type='text']"
            await page.fill(email_sel, USER)
            await page.fill("input[type='password']", PASS)
            print("FILLED credentials")
        except Exception as e:
            print("FILL-ERR:", e)

        # click login button
        clicked = False
        for sel in ["button:has-text('Entrar')", "button:has-text('Login')", "button:has-text('Acessar')",
                    "text=Entrar", "button[type='submit']", "button"]:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.click()
                    clicked = True
                    print("CLICKED login via", sel)
                    break
            except Exception as e:
                print("click try err", sel, e)
        print("clicked?", clicked)
        await page.wait_for_timeout(8000)
        print("AFTER LOGIN URL:", page.url)

        # session evidence (keys only, no values)
        try:
            ck = await ctx.cookies()
            ls = await page.evaluate("() => Object.keys(window.localStorage)")
            ss = await page.evaluate("() => Object.keys(window.sessionStorage)")
            with open(f"{OUT}/session.txt", "w") as f:
                f.write("cookie_names: " + json.dumps([c['name'] for c in ck]) + "\n")
                f.write("localStorage_keys: " + json.dumps(ls) + "\n")
                f.write("sessionStorage_keys: " + json.dumps(ss) + "\n")
            print("COOKIES:", [c['name'] for c in ck])
            print("LS KEYS:", ls)
        except Exception as e:
            print("session-err", e)

        # dump landing after login + collect menu links
        links = await dump(page, "01_after_login")

        # save network log
        with open(f"{OUT}/network.json", "w") as f:
            json.dump(net, f, ensure_ascii=False, indent=2)
        # unique internal endpoints
        uniq = sorted(set((n["m"], n["u"]) for n in net))
        with open(f"{OUT}/endpoints.txt", "w") as f:
            for m, u in uniq:
                f.write(f"{m} {u}\n")
        print("NET events:", len(net), "unique:", len(uniq))

        await browser.close()

asyncio.run(main())
