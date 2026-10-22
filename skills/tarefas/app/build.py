#!/usr/bin/env python3
"""Monta a página do quadro a partir de board-src.html.

Uso: python3 build.py --titulo "Tarefas Pessoais" --out /caminho/quadro.html
                      [--tema-arquivo /caminho/tema.css]
                      [--fontes "https://fonts.googleapis.com/css2?..." | --sem-fontes-externas]
Sem --tema-arquivo, sai o tema neutro (style-base.css). Com ele, o CSS do arquivo entra depois da base e
sobrescreve os tokens (--bg, --accent, --f-display…): é o tema da marca da pessoa (quadro-tarefas § Tema).
--fontes acrescenta uma folha do Google Fonts (a única origem de estilo externa que o artefato aceita).
--sem-fontes-externas (config/tema.fontes_externas: false): a página não carrega nada de fora, nem o Google Fonts
nem os preconnect; os tokens de fonte caem nas fontes do sistema. Não combina com --fontes.
O escopo (nome, áreas, idioma, locale, fuso) NÃO vai no HTML: a página lê de config/preferencias no banco.
"""
import argparse, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FONTES_BASE = '<link rel="preconnect" href="https://fonts.googleapis.com">\n' \
              '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n' \
              '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">'
GOOGLE_FONTS = "https://fonts.googleapis.com/css2?"


# Funções aceitas no CSS do tema: cores, contas e seletores. Qualquer outra (url, image-set, image, src…)
# poderia carregar algo de fora; o quadro só aceita estilo externo do Google Fonts (--fontes).
FUNCOES_OK = {"rgb", "rgba", "hsl", "hsla", "hwb", "lab", "lch", "oklab", "oklch", "color-mix", "var", "calc",
              "clamp", "min", "max", "color", "linear-gradient", "radial-gradient", "not", "is", "where"}


def codigo_css(css, recusa):
    """O CSS sem o conteúdo de textos entre aspas (viram "") e sem comentários (somem), lido como o navegador lê:
    aspas só abrem fora de comentário, comentário só abre fora de aspas. Texto entre aspas não pode ter quebra de
    linha nem ficar aberto; comentário também tem que fechar. (Barra invertida já foi recusada antes.)"""
    out, i, n = [], 0, len(css)
    while i < n:
        c = css[i]
        if c in "\"'":
            j = i + 1
            while j < n and css[j] != c:
                if css[j] in "\r\n\f":
                    recusa("texto entre aspas com quebra de linha")
                j += 1
            if j >= n:
                recusa("texto entre aspas sem fechar")
            out.append('""')
            i = j + 1
        elif css.startswith("/*", i):
            j = css.find("*/", i + 2)
            if j < 0:
                recusa("comentário sem fechar")
            i = j + 2  # some sem deixar espaço: url/**/( vira url( e é recusado
        else:
            out.append(c)
            i += 1
    return "".join(out)


def tema_css(caminho):
    """Lê o CSS do tema e recusa o que carregaria algo de fora ou quebraria a página."""
    with open(caminho, encoding="utf-8") as f:
        css = f.read().strip()
    css = re.sub(r"^\s*<style[^>]*>|</style>\s*$", "", css).strip()  # aceita com ou sem <style>
    recusa = lambda motivo: sys.exit(f"tema recusado: {motivo} (o tema só sobrescreve tokens; fontes só por --fontes)")
    if "\\" in css:
        recusa("barra invertida (escape de CSS) não é permitida")
    if re.search(r"<|javascript:|expression", css, re.I):
        recusa("tag HTML, javascript: ou expression")
    limpo = codigo_css(css, recusa)  # at-rules e funções só contam no código, fora de aspas e comentários
    for regra in re.findall(r"@([\w-]*)", limpo):
        if regra.lower() != "media":
            recusa(f"@{regra} não é permitido (só @media)")
    for arroba, fn in re.findall(r"(@?)([\w-]+)\(", limpo):  # no CSS, função = nome colado no "("
        if not arroba and fn.lower() not in FUNCOES_OK:
            recusa(f"{fn}(...) não é permitido")
    return "<style>\n/* ===== Tema da marca (config/tema) ===== */\n" + css + "\n</style>"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--titulo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tema-arquivo", help="CSS que sobrescreve os tokens da base (tema da marca)")
    ap.add_argument("--fontes", help="URL do Google Fonts (css2) com as fontes do tema")
    ap.add_argument("--sem-fontes-externas", action="store_true",
                    help="não carrega fonte de fora (sem Google Fonts nem preconnect); usa as fontes do sistema")
    a = ap.parse_args()
    if a.sem_fontes_externas and a.fontes:
        ap.error("--sem-fontes-externas não combina com --fontes")
    def rd(nome):
        with open(os.path.join(HERE, nome), encoding="utf-8") as f:
            return f.read()
    fontes = "" if a.sem_fontes_externas else FONTES_BASE
    if a.fontes:
        if not a.fontes.startswith(GOOGLE_FONTS) or re.search(r'["<>\s]', a.fontes):
            sys.exit("--fontes precisa ser uma URL https://fonts.googleapis.com/css2?... sem aspas nem espaços")
        fontes += f'\n<link rel="stylesheet" href="{a.fontes.replace("&", "&amp;")}">'
    html = rd("board-src.html")
    html = html.replace("{{TITULO}}", a.titulo.replace("<", "").replace(">", ""))
    html = html.replace("{{FONTS}}", fontes).replace("{{CSS_BASE}}", rd("style-base.css"))
    html = html.replace("{{TEMA}}", tema_css(a.tema_arquivo) if a.tema_arquivo else "")
    assert "{{" not in html, "placeholder sobrando"
    js = re.search(r"<script>(.*)</script>", html, re.S).group(1)
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(js)
    if shutil.which("node"):  # checagem extra, só se houver Node; sem ele o quadro é montado igual
        r = subprocess.run(["node", "--check", f.name], capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if r.returncode:
            os.unlink(f.name)
            sys.exit("JS inválido:\n" + r.stderr)
    os.unlink(f.name)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(a.out)


if __name__ == "__main__":
    main()
