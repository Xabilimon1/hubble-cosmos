"""Anatomy of a compiled module: where each byte of a .omd goes.

The numbers are `hubble secciones` on imhex/demo.smd compiled for 64 bits (5914 bytes).
Self-contained: runs as is in Google Colab or locally (needs matplotlib). Writes anatomy.png.
"""
import matplotlib.pyplot as plt

BG, PANEL, EDGE = "#111111", "#161616", "#3a3a3a"
INK, MUTED, GAP = "#e6e6e6", "#9a9a9a", "#111111"
BLUE, ORANGE, GREEN, GREY = "#5b93e8", "#c27f42", "#4aa77d", "#4a4a4a"

# (sección, bytes, grupo); grupos: estructura, código, nombres y textos, tablas de entrada
SECCIONES = [
    ("header", 76, "frame"), ("index A", 192, "frame"), ("EMO", 80, "frame"), ("FON", 80, "frame"),
    ("CMD", 36, "frame"), ("index B", 768, "frame"), ("CTE", 48, "code"), ("CLA", 88, "code"),
    ("OBJ", 320, "code"), ("PRO", 128, "code"), ("STM", 672, "code"), ("REF", 2496, "code"),
    ("IDE", 290, "text"), ("STR", 82, "text"), ("index C", 224, "frame"), ("EPR", 88, "entry"),
    ("ECL", 40, "entry"), ("EID", 200, "entry"), ("SVL", 6, "text"),
]
COLOR = {"frame": GREY, "code": BLUE, "text": ORANGE, "entry": GREEN}
NOMBRE = {"frame": "container and indexes", "code": "code",
          "text": "names and strings", "entry": "entry tables"}
DETALLE = {"STM": "statements", "REF": "expression nodes", "OBJ": "objects",
           "IDE": "identifiers", "index B": "section index"}  # PRO es estrecho: sin etiqueta

total = sum(b for _, b, _ in SECCIONES)
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK})
fig, ax = plt.subplots(figsize=(12, 3.0), dpi=200)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

x = 0
for nombre, b, g in SECCIONES:
    ax.barh(0, b, left=x, height=0.55, color=COLOR[g], edgecolor=GAP, linewidth=1.5)
    if b / total > 0.045:
        ax.text(x + b / 2, 0, nombre, ha="center", va="center", fontsize=10, color=BG, weight="bold")
    if nombre in DETALLE:
        ax.text(x + b / 2, -0.42, DETALLE[nombre], ha="center", va="top", fontsize=8.5, color=MUTED)
    x += b

ax.set_xlim(0, total)
ax.set_ylim(-0.9, 0.75)
ax.set_yticks([])
ax.set_xticks([0, 1000, 2000, 3000, 4000, 5000, total])
ax.set_xticklabels(["0", "1000", "2000", "3000", "4000", "5000", f"{total} bytes"], color=MUTED, fontsize=9)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color(EDGE)
ax.tick_params(color=EDGE, labelcolor=MUTED, length=3)

# leyenda en una fila, con el texto en tinta y no en el color de la serie
for i, g in enumerate(("code", "text", "entry", "frame")):
    fig.text(0.06 + i * 0.16, 0.93, "■", color=COLOR[g], fontsize=13, va="center")
    fig.text(0.075 + i * 0.16, 0.93, NOMBRE[g], color=INK, fontsize=9.5, va="center")
fig.text(0.06, 0.03, "Every byte is accounted for: no gaps, no overlaps. Expression nodes alone take 42% of this small program.",
         color=MUTED, fontsize=9.5)

fig.subplots_adjust(top=0.82, bottom=0.2, left=0.04, right=0.94)
fig.savefig("anatomy.png", facecolor=BG, pad_inches=0.2)
print("anatomy.png")
