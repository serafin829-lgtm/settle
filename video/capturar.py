import sys, time
from playwright.sync_api import sync_playwright
B="http://127.0.0.1:8799"; O=sys.argv[1]
def shot(pg,name): pg.wait_for_timeout(700); pg.screenshot(path=f"{O}/{name}.png")
with sync_playwright() as p:
    br=p.chromium.launch(); pg=br.new_page(viewport={"width":1600,"height":900},device_scale_factor=1.2)
    pg.set_content("<body style='margin:0;background:#0b1f3a;color:#fff;font-family:DejaVu Sans;display:flex;flex-direction:column;justify-content:center;align-items:center;height:100vh'><h1 style='font-size:96px;margin:0'>Settle</h1><p style='font-size:40px'>The AI refund desk for small PayPal merchants</p><p style='font-size:26px;opacity:.7'>PayPal AI Hackathon 2026 · demo in PayPal sandbox (simulated)</p></body>"); shot(pg,"s1_a")
    pg.goto(B+"/"); shot(pg,"s2_a")
    btns=pg.locator("[data-sku]"); btns.last.click(); shot(pg,"s2_b")
    pg.click("#mockbtn"); pg.wait_for_selector("#after",state="visible"); pg.locator("#after").scroll_into_view_if_needed(); shot(pg,"s2_c")
    pg.fill("#cemail","sam.rivera@example.com"); pg.fill("#ctext","The vase arrived cracked, I'm so sad"); shot(pg,"s3_a")
    pg.click("#send"); pg.wait_for_selector("#reply",state="visible",timeout=60000); pg.locator("#reply").scroll_into_view_if_needed(); shot(pg,"s3_b")
    pg.goto(B+"/console"); pg.wait_for_selector(".case-item"); pg.locator(".case-item").first.click(); shot(pg,"s4_a")
    for i,y in enumerate([400,800,1200]): pg.mouse.wheel(0,400); shot(pg,f"s4_{'bcd'[i]}")
    pg.locator(".checks").scroll_into_view_if_needed(); shot(pg,"s5_a")
    if pg.locator("#approve").count(): pg.click("#approve"); pg.wait_for_timeout(1500)
    pg.locator(".case-item").first.click(); pg.locator(".proposal").scroll_into_view_if_needed(); pg.mouse.wheel(0,600); shot(pg,"s6_a")
    pg.click("#seed"); pg.wait_for_timeout(4000); pg.evaluate("window.scrollTo(0,0)"); shot(pg,"s7_a")
    n=pg.locator(".case-item").count()
    for i in range(min(n,3)): pg.locator(".case-item").nth(i).click(); pg.evaluate("window.scrollTo(0,0)"); shot(pg,f"s7_{'bcd'[i]}")
    pg.locator("#policy").scroll_into_view_if_needed(); pg.fill("#lim","50"); shot(pg,"s8_a")
    pg.set_content("<body style='margin:0;background:#0b1f3a;color:#fff;font-family:DejaVu Sans Mono;display:flex;flex-direction:column;justify-content:center;align-items:center;height:100vh;font-size:26px'><pre>Shop (PayPal JS SDK) ─► PayPal Orders v2 (create/capture)\nCustomer message ─► AI agent + tools ─► proposal\n   ─► Guardrails (code) ─► auto or 1-click\n   ─► PayPal Payments v2 refund (idempotent)</pre><h1 style='font-family:DejaVu Sans;font-size:64px'>Settle — built with PayPal and AI</h1></body>"); shot(pg,"s8_b")
    br.close()
