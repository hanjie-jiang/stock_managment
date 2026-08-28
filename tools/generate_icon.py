"""Generates assets/dashboard.ico, the icon used by the Desktop shortcut.

Run manually if the icon needs to change; not part of the app's runtime.
Uses Pillow, already a transitive dependency (via Streamlit).
"""

import os

from PIL import Image, ImageDraw

SIZE = 256
BG = (37, 99, 235, 255)       # blue tile
BAR = (255, 255, 255, 255)    # white bars
ARROW = (74, 222, 128, 255)   # green upward arrow

img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

margin = 10
draw.rounded_rectangle(
    [margin, margin, SIZE - margin, SIZE - margin], radius=48, fill=BG
)

# Three ascending bars, like a simple bar chart.
bar_width = 34
gap = 20
base_y = 200
bars = [
    (70, 130),   # x_left, top_y
    (70 + bar_width + gap, 100),
    (70 + 2 * (bar_width + gap), 60),
]
for x, top_y in bars:
    draw.rounded_rectangle([x, top_y, x + bar_width, base_y], radius=6, fill=BAR)

# Small upward arrow above the bars, echoing "the stock is up".
draw.polygon(
    [(178, 46), (150, 80), (166, 80), (166, 100), (190, 100), (190, 80), (206, 80)],
    fill=ARROW,
)

out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "dashboard.ico")
img.save(out_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(f"Wrote {out_path}")
