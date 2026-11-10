"""Recherche-Hilfe für ein ganzes Paket in einem Durchgang.

Aufruf:  python -I _werkzeuge/recherche.py --paket N [suchbegriffe.json]

Zeigt für jede Karte des Pakets: Aufgabe und Ziel der gedruckten Karte, die Links der alten Seite mit Prüfergebnis
und, wenn eine Datei mit Suchbegriffen angegeben ist ({"slug": ["Suche 1", "Suche 2"]}), YouTube-Treffer mit
Dauer, Alter, Kanal und Aufrufen. Alles läuft parallel. Ausgabe auch in _daten/recherche/paket-NN.txt.
"""
import concurrent.futures as cf
import html
import json
import pathlib
import re
import sys
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import pruefen  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO, DATEN = pruefen.REPO, pruefen.DATEN


def youtube_suche(q, n=10):
    url = "https://www.youtube.com/results?hl=de&gl=CH&search_query=" + urllib.parse.quote(q)
    _, _, b = pruefen.holen(url)
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", b)
    if not m:
        return q, []
    daten = json.loads(m.group(1))
    treffer = []
    for s in daten["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"]["sectionListRenderer"]["contents"]:
        for it in s.get("itemSectionRenderer", {}).get("contents", []):
            v = it.get("videoRenderer")
            if not v:
                continue
            txt = lambda o: "".join(r["text"] for r in o.get("runs", [])) if o else ""
            treffer.append(dict(id=v["videoId"], dauer=v.get("lengthText", {}).get("simpleText", "live?"),
                                alter=v.get("publishedTimeText", {}).get("simpleText", ""),
                                kanal=txt(v.get("ownerText")), aufrufe=v.get("viewCountText", {}).get("simpleText", ""),
                                titel=txt(v.get("title"))))
            if len(treffer) >= n:
                return q, treffer
    return q, treffer


def alte_seite(slug):
    t = (REPO / f"{slug}.html").read_text(encoding="utf-8")
    intro = re.search(r"Einf.hrung</h[23]>\s*<p>(.*?)</p>", t, re.S)
    links = [(html.unescape(html.unescape(u)), re.sub("<[^>]+>", "", l)) for u, l in re.findall(r'<a href="(https?://[^"]+)"[^>]*>(.*?)</a>', t)]
    return (" ".join(intro.group(1).split()) if intro else ""), links


def details(vid):
    """Datum, Kanal, Dauer und Anfang der Beschreibung eines YouTube-Videos."""
    _, _, b = pruefen.holen(f"https://www.youtube.com/watch?v={vid}&hl=de")
    g = lambda p: (m.group(1) if (m := re.search(p, b)) else "")
    beschr = g(r'"shortDescription":"((?:[^"\\]|\\.)*)"').replace("\\n", " ")
    sek = int(g(r'"lengthSeconds":"(\d+)"') or 0)
    return (f"{vid} | {sek // 60}:{sek % 60:02d} | {g(r'\"publishDate\":\"([^\"]*)\"')[:10]} | "
            f"{g(r'\"ownerChannelName\":\"([^\"]*)\"')}\n    {beschr[:260]}")


def main():
    args = sys.argv[1:]
    if args and args[0] == "--details":  # python -I _werkzeuge/recherche.py --details ID ID ... [URL ...]
        ids = [a for a in args[1:] if not a.startswith("http")]
        urls = [a for a in args[1:] if a.startswith("http")]
        with cf.ThreadPoolExecutor(10) as ex:
            for zeile in ex.map(details, ids):
                print(zeile)
            for u, r in ex.map(pruefen.pruefe, urls):
                print(f"{r['status'][:35]} | {(r.get('titel') or '')[:90]} | {u}")
        return
    nr = int(args[args.index("--paket") + 1])
    such = json.loads(pathlib.Path(args[-1]).read_text(encoding="utf-8")) if args[-1].endswith(".json") else {}
    paket = next(p for p in pruefen.pakete() if p["nr"] == nr)
    v = pruefen.verzeichnis()
    alt = {s: alte_seite(s) for s in paket["karten"]}
    alle_urls = sorted({u for _, ls in alt.values() for u, _ in ls})
    abfragen = sorted({q for s in paket["karten"] for q in such.get(s, [])})
    with cf.ThreadPoolExecutor(10) as ex:
        pruef = dict(ex.map(pruefen.pruefe, alle_urls))
        suche = dict(ex.map(youtube_suche, abfragen))
    aus = []
    for s in paket["karten"]:
        x = v[s]
        intro, links = alt[s]
        aus += [f"\n######## {x['titel']}  ({s}.html, {x['kategorie']})", f"Aufgabe: {x['aufgabe']}", f"Ziel: {x['ziel']}", f"Alt-Intro: {intro[:300]}", "Alte Links:"]
        for u, l in links:
            r = pruef[u]
            sek = r.get("sekunden")
            d = f"{sek // 60}:{sek % 60:02d}" if sek else ""
            aus.append(f"  {'OK ' if r['ok'] else 'TOT'} {d:>6} {r.get('datum', ''):10} {r.get('kanal', '')[:25]:25} | {l[:60]} | {u}")
        for q in such.get(s, []):
            aus.append(f"  Suche «{q}»:")
            for t in suche.get(q, []):
                aus.append(f"    {t['id']} | {t['dauer']:>7} | {t['alter']:15} | {t['kanal'][:28]:28} | {t['aufrufe']:16} | {t['titel'][:90]}")
    text = "\n".join(aus)
    ziel = DATEN / "recherche" / f"paket-{nr:02d}.txt"
    ziel.parent.mkdir(exist_ok=True)
    ziel.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
