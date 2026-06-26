"""Plain-language flow of the notsofast decision, drawn for a non-technical reader.
Renders flow.svg and flow.png from one matplotlib source (no libcairo needed)."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

INK, BLUE, GREEN, CREAM = "#0F0E0B", "#1B3DFF", "#00B870", "#F4F1E8"


def render():
    fig, ax = plt.subplots(figsize=(8.6, 9.4), dpi=160)
    fig.patch.set_facecolor(CREAM); ax.set_facecolor(CREAM)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")

    def box(x, y, w, h, text, fc, ec, tc, fs=11, bold=False):
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                     boxstyle="round,pad=0.6,rounding_size=2.2", fc=fc, ec=ec, lw=1.8))
        ax.text(x, y, text, ha="center", va="center", color=tc, fontsize=fs,
                fontweight="bold" if bold else "normal", wrap=True)

    def arrow(x1, y1, x2, y2, label="", lcolor=INK):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                     mutation_scale=16, lw=1.8, color=INK, shrinkA=2, shrinkB=2))
        if label:
            ax.text((x1 + x2) / 2 + (2.5 if x2 > x1 else 0), (y1 + y2) / 2 + 1.2,
                    label, ha="center", va="center", color=lcolor, fontsize=10, fontweight="bold")

    QX, AX = 33, 78          # question column, ALLOW column
    ys = [84, 67, 50, 33]    # four question rows

    # Start
    box(QX, 96, 52, 6, "A decision the AI is about to finalize", CREAM, INK, INK, 11, True)
    arrow(QX, 92.5, QX, ys[0] + 5.6)

    questions = [
        "Did the model only check\nits OWN work?",
        "Is it a hard, right-or-wrong\ncall (not open-ended writing)?",
        "Is it high-stakes:\ncostly and hard to undo?",
        "Can an independent\ncheck be added?",
    ]
    allow_reasons = [
        "ALLOW\nsomeone else already\nchecked it",
        "ALLOW\nopen-ended work,\nself-editing helps",
        "ALLOW\nlow-stakes and\nreversible, let it stand",
    ]
    for i, q in enumerate(questions):
        box(QX, ys[i], 40, 11, q, INK, INK, CREAM, 11, True)

    # YES path down the question spine
    for i in range(3):
        arrow(QX, ys[i] - 5.5, QX, ys[i + 1] + 5.5, "YES")

    # NO -> ALLOW chips (first three questions)
    for i in range(3):
        arrow(QX + 20, ys[i], AX - 13, ys[i], "NO")
        box(AX, ys[i], 30, 11, allow_reasons[i], GREEN, GREEN, INK, 10, True)

    # Last question: YES -> REQUIRE, NO -> ESCALATE
    arrow(QX - 3, ys[3] - 5.5, 22, 14 + 5.5, "YES")
    box(22, 14, 34, 12, "REQUIRE\nINDEPENDENT CHECK\n(cross-model, tool, or human)",
        BLUE, BLUE, CREAM, 10, True)
    arrow(QX + 8, ys[3] - 5.5, 62, 14 + 5.5, "NO")
    box(64, 14, 30, 12, "ESCALATE\nTO A HUMAN\n(no check is available)",
        CREAM, INK, INK, 10, True)

    ax.text(50, 4, "The rule restricts exactly one path. Everything else is allowed.",
            ha="center", va="center", color=INK, fontsize=10, style="italic")

    fig.tight_layout()
    for ext in ("svg", "png"):
        fig.savefig(__file__.replace("flow_diagram.py", f"flow.{ext}"),
                    facecolor=CREAM)
    plt.close(fig)
    print("wrote flow.svg and flow.png")


if __name__ == "__main__":
    render()
