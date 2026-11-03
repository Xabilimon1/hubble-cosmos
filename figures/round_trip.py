"""The round trip that every result of Hubble has to pass.

Self-contained: runs as is in Google Colab or locally (needs matplotlib). Writes round_trip.png.
"""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

BG, PANEL, EDGE = "#111111", "#161616", "#3a3a3a"
INK, MUTED = "#e6e6e6", "#9a9a9a"
BLUE, ORANGE, GREEN = "#5b93e8", "#c27f42", "#4aa77d"

plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK})
fig, ax = plt.subplots(figsize=(12, 4.2), dpi=200)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
ax.set_xlim(0, 12.6)
ax.set_ylim(0, 4.2)
ax.axis("off")


def caja(x, y, titulo, detalle, color):
    ax.add_patch(FancyBboxPatch((x, y), 2.2, 1.1, boxstyle="round,pad=0.02,rounding_size=0.08",
                                facecolor=PANEL, edgecolor=color, linewidth=1.6))
    ax.text(x + 1.1, y + 0.72, titulo, ha="center", va="center", fontsize=12, color=color, weight="bold")
    ax.text(x + 1.1, y + 0.34, detalle, ha="center", va="center", fontsize=9.5, color=MUTED)


def flecha(x0, y0, x1, y1, texto="", dy=0.18):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=14,
                                 color=MUTED, linewidth=1.4))
    if texto:
        ax.text((x0 + x1) / 2, (y0 + y1) / 2 + dy, texto, ha="center", va="bottom", fontsize=9.5, color=MUTED)


# fila de arriba: lo que existe
caja(0.3, 2.7, "source.smd", "original COOL source", BLUE)
caja(4.9, 2.7, "module.omd", "compiled module", ORANGE)
flecha(2.5, 3.25, 4.9, 3.25, "Cosmos compiler")

# fila de abajo: lo que produce Hubble
caja(4.9, 0.5, "decompiled.smd", "Hubble's output", GREEN)
caja(9.5, 0.5, "again.omd", "recompiled", ORANGE)
flecha(6.0, 2.7, 6.0, 1.6, "")
ax.text(6.12, 2.15, "Hubble", ha="left", va="center", fontsize=10.5, color=GREEN, weight="bold")
flecha(7.1, 1.05, 9.5, 1.05, "same compiler")

# la comparación
ax.annotate("", xy=(10.6, 1.6), xytext=(7.1, 3.25),
            arrowprops=dict(arrowstyle="<|-|>", color=INK, linewidth=1.4, linestyle=(0, (4, 3)),
                            connectionstyle="angle,angleA=0,angleB=90,rad=0", mutation_scale=14))
ax.text(8.85, 3.35, "byte-for-byte comparison", ha="center", va="bottom", fontsize=11, color=INK)
ax.text(10.75, 2.45, "identical, or identical\nexcept for memory pointers", ha="left", va="center",
        fontsize=9, color=MUTED)

ax.text(0.3, 1.25, "If a field is not understood,\nHubble refuses the module\n(NoSoportado) instead of guessing.",
        ha="left", va="center", fontsize=10, color=MUTED, linespacing=1.5)

fig.savefig("round_trip.png", facecolor=BG, bbox_inches="tight", pad_inches=0.25)
print("round_trip.png")
