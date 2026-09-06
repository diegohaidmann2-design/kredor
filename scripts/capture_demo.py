import asyncio, os
from playwright.async_api import async_playwright

BASE = "http://localhost:3000"
OUT = "/app/frontend/src/assets/demo"
os.makedirs(OUT, exist_ok=True)

PAGES = [
    ("/dashboard", "dashboard"),
    ("/emprestimos", "emprestimos"),
    ("/consultas", "consultas"),
    ("/simulacao", "simulacao"),
    ("/relatorios", "relatorios"),
]

SANITIZE = """
() => {
  const NAME='Conta Demo';
  const EMAIL='conta@gestorcred.cloud';
  const walk=document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
  const nodes=[]; while(walk.nextNode()) nodes.push(walk.currentNode);
  nodes.forEach(n=>{
    const v=n.nodeValue||'';
    const low=v.toLowerCase();
    if(v.includes('@') && (low.includes('gmail')||low.includes('haidmann')||low.includes('diego')||low.includes('@'))){
      if(low.includes('@gmail')||low.includes('haidmann')||low.includes('diego')) n.nodeValue=EMAIL;
    }
    if(low.includes('diego') || low.includes('haidmann')){ n.nodeValue = v.includes('@')?EMAIL:NAME; }
  });
}
"""

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path="/usr/bin/google-chrome",
                                           args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = await browser.new_context(viewport={"width": 1440, "height": 860},
                                        device_scale_factor=2)
        page = await ctx.new_page()
        await page.goto(f"{BASE}/login", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(1500)
        await page.fill("[data-testid='input-email']", "diego.haidmann@gmail.com")
        await page.fill("[data-testid='input-senha']", "Demo@2026")
        await page.click("[data-testid='submit-button']")
        await page.wait_for_timeout(5000)
        print("after login:", page.url)
        for path, name in PAGES:
            try:
                await page.goto(f"{BASE}{path}", wait_until="networkidle", timeout=60000)
                await page.wait_for_timeout(4000)
                await page.evaluate(SANITIZE)
                await page.wait_for_timeout(400)
                await page.screenshot(path=f"{OUT}/{name}.png", full_page=False)
                print("saved", name)
            except Exception as e:
                print("err", name, e)
        await browser.close()

asyncio.run(main())
