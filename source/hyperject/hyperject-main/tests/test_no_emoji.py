"""Guard: this project stays emoji-free. Scans the package (source, docs, config)
for emoji / pictograph characters. Plain typography (arrows, box-drawing, dashes)
is allowed; emoji are not."""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Unicode ranges that are emoji / pictographs (NOT plain-text typography).
EMOJI_RANGES = [
    (0x1F000, 0x1FAFF),   # pictographs, emoticons, transport, supplemental symbols
    (0x2600, 0x26FF),     # miscellaneous symbols (weather, warning, etc.)
    (0x2700, 0x27BF),     # dingbats (check marks, crosses, scissors)
    (0x2B00, 0x2BFF),     # misc symbols & arrows (stars, emoji arrows)
    (0x1F1E6, 0x1F1FF),   # regional indicators (flags)
    (0xFE00, 0xFE0F),     # variation selectors (emoji presentation)
]
# specific emoji-presentation geometric shapes we also disallow
EMOJI_SINGLES = {0x25B6, 0x25C0, 0x25B8, 0x25C2}

SKIP_DIRS = {"build", "__pycache__", ".pytest_cache", ".egg-info", ".git", ".demo"}
SCAN_SUFFIXES = {".py", ".md", ".json", ".toml", ".cfg", ".txt"}


def _is_emoji(ch: str) -> bool:
    o = ord(ch)
    return o in EMOJI_SINGLES or any(a <= o <= b for a, b in EMOJI_RANGES)


def _files():
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix not in SCAN_SUFFIXES:
            continue
        if any(part in SKIP_DIRS or part.endswith(".egg-info") for part in p.parts):
            continue
        yield p


def test_no_emoji_in_project():
    offenders = []
    for p in _files():
        text = p.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), 1):
            for ch in line:
                if _is_emoji(ch):
                    offenders.append(f"{p.relative_to(ROOT)}:{lineno} U+{ord(ch):04X} {ch!r}")
    assert not offenders, "emoji found (this project must stay emoji-free):\n" + \
        "\n".join(offenders)
