"""Generate fixed native UI assets from reviewed local source files."""
from pathlib import Path
import sys

ASSETS = (("index.html", "pf_ui_html"), ("ui.css", "pf_ui_css"), ("ui.js", "pf_ui_js"))
def build(out):
    src = Path(__file__).resolve().parent / "web"
    lines = ["/* Generated source; do not edit. */", "#ifndef PF_UI_ASSETS_H", "#define PF_UI_ASSETS_H"]
    for name, symbol in ASSETS:
        data = (src / name).read_bytes()
        if not 0 < len(data) < 65536 or b"\0" in data:
            raise ValueError("invalid embedded asset: " + name)
        lines.append("static const unsigned char " + symbol + "[] = {")
        for i in range(0, len(data), 24):
            lines.append(" " + ",".join(str(x) for x in data[i:i+24]) + ",")
        lines.extend((" 0", "};"))
    lines.append("#endif")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="ascii")
if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: embed_ui.py OUTPUT")
    build(sys.argv[1])
