import asyncio, os, json
from playwright.async_api import async_playwright

BASE = "https://sysjuros.com.br"
LOGIN = f"{BASE}/auth/log-in"
OUT = "/app/bench/out"
os.makedirs(OUT, exist_ok=True)
USER = os.environ.get("SYS_USER", "")
PASS = os.environ.get("SYS_PASS", "")

MENUS = ["Clientes", "Contratos", "Vencimentos", "Relatorios", "Configuracoes"]
# accents handled via label map for clicking
CLICK_LABELS = {"Relatorios": "Relatórios", "Configuracoes": "Configurações"}

async def dump(page, name):
    try:
        await page.wait_for_timeout(3500)
        txt = await page.evaluate("() => document.body ? document.body.innerText : ''")
        with open(f"{OUT}/{name}.txt", "w") as f:
            f.write("URL: " + page.url + "\n\n=== INNER TEXT ===\n" + (txt or ""))
        await page.screenshot(path=f"{OUT}/{name}.png", full_page=True)
        print(f"DUMP {name} url={page.url} textlen={len(txt or '')}")
    except Exception as e:
        print(f"DUMP-ERR {name}: {e}")

async def click_label(page, label):
    # click the lowest DOM element whose exact trimmed text == label
    ok = await page.evaluate(
        """(label) => {
            const els = Array.from(document.querySelectorAll('div,span,a,li,button'));
            const matches = els.filter(e => (e.innerText||'').trim() === label);
            // choose the deepest (fewest children with same text)
            const target = matches.sort((a,b)=> a.children.length - b.children.length)[0];
            if (target) { target.click(); return true; }
            return false;
        }""",
        label,
    )
    return ok

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path="/usr/bin/google-chrome",
                                          args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await ctx.new_page()
        await page.goto(LOGIN, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        await page.fill("input[type='email']", USER)
        await page.fill("input[type='password']", PASS)
        await page.click("button:has-text('Entrar')")
        await page.wait_for_timeout(8000)
        print("LOGGED IN:", page.url)

        for key in MENUS:
            label = CLICK_LABELS.get(key, key)
            try:
                clicked = await click_label(page, label)
                print(f"MENU {label} clicked={clicked}")
                await page.wait_for_timeout(4000)
                await dump(page, f"10_{key}")
                # try to open a "novo/adicionar/+" create form to reveal fields
                created = await page.evaluate(
                    """() => {
                        const els = Array.from(document.querySelectorAll('div,span,a,li,button'));
                        const kw = ['Novo','Adicionar','Cadastrar','+ ','Criar'];
                        const t = els.find(e => { const x=(e.innerText||'').trim(); return x.length<25 && kw.some(k=>x.startsWith(k)); });
                        if (t) { t.click(); return (t.innerText||'').trim(); }
                        return null;
                    }"""
                )
                if created:
                    print(f"  open-create '{created}'")
                    await page.wait_for_timeout(3500)
                    await dump(page, f"11_{key}_create")
                    # dump form fields
                    fields = await page.evaluate(
                        "() => Array.from(document.querySelectorAll('input,select,textarea')).map(i=>({tag:i.tagName,type:i.type,ph:i.placeholder,name:i.name}))"
                    )
                    with open(f"{OUT}/12_{key}_fields.json","w") as f:
                        json.dump(fields, f, ensure_ascii=False, indent=2)
                    print(f"  fields={len(fields)}")
                    # close modal via Escape
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(1500)
            except Exception as e:
                print(f"MENU-ERR {label}: {e}")
                continue

        await browser.close()

asyncio.run(main())
