#!/usr/bin/env python3
"""Poll SIGAA PPGI news page once, alert on new items via ntfy. Run by cron/Actions."""
import os
import re
from datetime import date
from urllib.request import Request, urlopen

URL = "https://sigaa.ufpb.br/sigaa/public/programa/noticiasGerais.jsf?lc=pt_BR&id=1879"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "ppgi-yuri")
SEEN_FILE = os.path.join(os.path.dirname(__file__), "seen_ids.txt")

ITEM_RE = re.compile(
    r'<span class="data"[^>]*>\s*<strong>\((\d{2}/\d{2}/\d{4}) (\d{2}:\d{2})\)</strong></span>\s*'
    r'<a href="noticias_desc\.jsf\?lc=pt_BR&id=1879&noticia=(\d+)" class="cor">([^<]+)</a>'
)


def fetch_items():
    req = Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    html = urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    return ITEM_RE.findall(html)


def load_seen():
    try:
        with open(SEEN_FILE) as f:
            return set(f.read().split())
    except FileNotFoundError:
        return set()


def save_seen(ids):
    with open(SEEN_FILE, "w") as f:
        f.write("\n".join(sorted(ids)))


def notify(title, body):
    print(f"{title}: {body}")
    req = Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=body.encode("utf-8"),
        headers={"Title": title.encode("utf-8"), "Priority": "urgent"},
        method="POST",
    )
    urlopen(req, timeout=10)


def main():
    today = date.today().strftime("%d/%m/%Y")
    seen = load_seen()
    items = fetch_items()
    ids_now = {noticia_id for _, _, noticia_id, _ in items}

    if not seen:
        # first run ever: baseline only, don't spam alerts for existing items
        save_seen(ids_now)
        print(f"Baseline salvo: {len(ids_now)} itens")
        return

    new_ids = ids_now - seen
    if new_ids:
        for d, hh, noticia_id, title in items:
            if noticia_id in new_ids:
                tag = "HOJE! " if d == today else ""
                notify(f"SIGAA PPGI - Nova notícia {tag}", f"({d} {hh}) {title}")
        save_seen(seen | new_ids)
    else:
        print("Sem novidades")


if __name__ == "__main__":
    main()
