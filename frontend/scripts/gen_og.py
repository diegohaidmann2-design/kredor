"""
Gera imagens Open Graph (1200x630) únicas por landing, com o título da página.
Texto renderizado via PIL (nítido e correto) sobre um fundo com a identidade Kredor.
Saída em frontend/public/og-<slug>.jpg (servidas como https://kredor.com.br/og-<slug>.jpg).
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(__file__)
PUBLIC = os.path.abspath(os.path.join(HERE, "..", "public"))
LOGO = os.path.abspath(os.path.join(HERE, "..", "src", "assets", "logomark.png"))

FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

W, H = 1200, 630
BG = (11, 18, 32)          # slate escuro
EMERALD = (16, 185, 129)   # primary
WHITE = (241, 245, 249)
GRAY = (148, 163, 184)

PAGES = [
    ("sistema-gestao-emprestimos", "GESTÃO DE CRÉDITO PROFISSIONAL", "Sistema de gestão de empréstimos"),
    ("cobranca-whatsapp", "RÉGUA DE COBRANÇA AUTOMÁTICA", "Cobrança automática no WhatsApp"),
    ("cobranca-pix", "PIX DINÂMICO + BAIXA AUTOMÁTICA", "Cobrança por PIX com baixa automática"),
    ("controle-de-parcelas-e-juros", "PARCELAS E JUROS AUTOMÁTICOS", "Controle de parcelas e cálculo de juros"),
    ("gestao-de-clientes", "CARTEIRA DE CLIENTES (CRM)", "Gestão de clientes e carteira de crédito"),
]


def wrap(draw, text, font, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def glow(size, color, radius):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x, y = size
    d.ellipse([x - radius, y - radius, x + radius, y + radius], fill=color)
    return layer.filter(ImageFilter.GaussianBlur(120))


def build(slug, eyebrow, title, outfile=None):
    img = Image.new("RGB", (W, H), BG)
    # brilhos de fundo
    base = img.convert("RGBA")
    base = Image.alpha_composite(base, glow((980, 120), (16, 185, 129, 90), 260))
    base = Image.alpha_composite(base, glow((120, 560), (5, 150, 105, 70), 220))
    img = base.convert("RGB")
    draw = ImageDraw.Draw(img)

    # moldura sutil
    draw.rectangle([16, 16, W - 16, H - 16], outline=(30, 41, 59), width=2)
    # barra de acento
    draw.rounded_rectangle([64, 250, 76, 470], radius=6, fill=EMERALD)

    PADL = 108
    # logo + marca
    try:
        logo = Image.open(LOGO).convert("RGBA").resize((72, 72))
        img.paste(logo, (PADL, 70), logo)
    except Exception:
        pass
    f_brand = ImageFont.truetype(FONT_BOLD, 40)
    draw.text((PADL + 88, 84), "Kredor", font=f_brand, fill=EMERALD)

    # eyebrow
    f_eye = ImageFont.truetype(FONT_BOLD, 24)
    # simula letter-spacing
    x = PADL
    ey = 232
    for ch in eyebrow:
        draw.text((x, ey), ch, font=f_eye, fill=EMERALD)
        x += draw.textlength(ch, font=f_eye) + 2

    # título (auto-wrap)
    f_title = ImageFont.truetype(FONT_BOLD, 76)
    lines = wrap(draw, title, f_title, W - PADL - 90)
    ty = 288
    for ln in lines:
        draw.text((PADL, ty), ln, font=f_title, fill=WHITE)
        ty += 88

    # rodapé: url + pill
    f_url = ImageFont.truetype(FONT_REG, 30)
    draw.text((PADL, H - 92), "kredor.com.br", font=f_url, fill=GRAY)

    f_pill = ImageFont.truetype(FONT_BOLD, 26)
    pill_txt = "7 dias grátis  •  sem cartão"
    pw = draw.textlength(pill_txt, font=f_pill)
    px1 = W - 108 - (pw + 56)
    draw.rounded_rectangle([px1, H - 100, W - 108, H - 46], radius=27,
                           fill=(6, 78, 59), outline=EMERALD, width=2)
    draw.text((px1 + 28, H - 92), pill_txt, font=f_pill, fill=(167, 243, 208))

    out = os.path.join(PUBLIC, outfile or f"og-{slug}.jpg")
    img.save(out, "JPEG", quality=86, optimize=True)
    print(f"OK {out} ({os.path.getsize(out)//1024} KB)")


if __name__ == "__main__":
    # Capa da HOME (mesmo estilo das landings), substitui a genérica.
    build("home", "GESTÃO DE EMPRÉSTIMOS + COBRANÇA",
          "Cobrança automática no PIX e WhatsApp", outfile="og-image-kredor.jpg")
    for slug, eyebrow, title in PAGES:
        build(slug, eyebrow, title)
