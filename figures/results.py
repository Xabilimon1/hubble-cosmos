"""Round-trip results over the Cosmos 8.6 evaluation kits.

Numbers from the last full round trip (64 and 32 bits). Self-contained: runs as is in Google Colab
or locally (needs matplotlib). Writes results.png.
"""
import matplotlib.pyplot as plt

BG, EDGE = "#111111", "#3a3a3a"
INK, MUTED = "#e6e6e6", "#9a9a9a"
BLUE, GREEN, RED = "#5b93e8", "#4aa77d", "#e06a5f"

# corpus: (idénticos byte a byte, idénticos salvo punteros de memoria, distintos, rechazados a propósito)
CORPUS = [
    ("Sample programs, 64-bit", 262, 151, 0, 2),
    ("Sample programs, 32-bit", 276, 137, 0, 2),
    ("Kit applications, 64-bit", 77, 43, 0, 0),
    ("Kit applications, 32-bit", 80, 41, 0, 0),
]

plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK})
fig, ax = plt.subplots(figsize=(11, 4), dpi=200)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

for i, (nombre, exactos, punteros, distintos, rechazados) in enumerate(CORPUS):
    y = len(CORPUS) - 1 - i
    total = exactos + punteros + distintos
    a = exactos / total * 100
    b = punteros / total * 100
    ax.barh(y, a, height=0.5, color=BLUE, edgecolor=BG, linewidth=2)
    ax.barh(y, b, left=a, height=0.5, color=GREEN, edgecolor=BG, linewidth=2)
    ax.text(a / 2, y, str(exactos), ha="center", va="center", color=BG, fontsize=10, weight="bold")
    ax.text(a + b / 2, y, str(punteros), ha="center", va="center", color=BG, fontsize=10, weight="bold")
    extra = f"{total} modules, {distintos} different" + (f", {rechazados} refused" if rechazados else "")
    ax.text(101.5, y, extra, ha="left", va="center", color=MUTED, fontsize=9.5)
    ax.text(-1.5, y, nombre, ha="right", va="center", color=INK, fontsize=10.5)

ax.set_xlim(0, 100)
ax.set_ylim(-0.6, len(CORPUS) - 0.4)
ax.set_yticks([])
ax.set_xticks([0, 25, 50, 75, 100])
ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"], color=MUTED, fontsize=9)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color(EDGE)
ax.tick_params(color=EDGE, labelcolor=MUTED, length=3)

fig.text(0.24, 0.93, "■", color=BLUE, fontsize=13, va="center")
fig.text(0.255, 0.93, "identical byte for byte", color=INK, fontsize=9.5, va="center")
fig.text(0.47, 0.93, "■", color=GREEN, fontsize=13, va="center")
fig.text(0.485, 0.93, "identical except for memory pointers", color=INK, fontsize=9.5, va="center")
fig.text(0.24, 0.04, "Decompile, recompile with the same compiler, compare. No module comes back different.",
         color=MUTED, fontsize=9.5)

fig.subplots_adjust(left=0.24, right=0.76, top=0.84, bottom=0.17)
fig.savefig("results.png", facecolor=BG, pad_inches=0.2)
print("results.png")
