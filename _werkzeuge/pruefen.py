"""Prüfwerkzeuge für die Kompetenzkarten.

Aufruf im Repo-Ordner:
  python -I _werkzeuge/pruefen.py links [--paket N | slug ...]     Links prüfen (alle Karten mit Daten, wenn nichts angegeben)
  python -I _werkzeuge/pruefen.py tabelle --paket N                Prüftabelle für die Freigabe erstellen
  python -I _werkzeuge/pruefen.py status                           Statusliste aller Karten erstellen

Ergebnisse:
  _daten/linkpruefung.json        letzter Prüfstand je Link (Datum, Dauer, Kanal ...)
  _daten/pruefungen/paket-NN.md   Prüftabelle eines Pakets
  _daten/status.md                Statusliste
"""
import concurrent.futures as cf
import datetime as dt
import html
import json
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

REPO = pathlib.Path(__file__).resolve().parent.parent
DATEN = REPO / "_daten"
CACHE = DATEN / "linkpruefung.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
HEUTE = dt.date.today().isoformat()
STUFEN = {1: "Einstieg", 2: "Vertiefung", 3: "Fortgeschritten"}


# ---------- Daten ----------

def pakete():
    return json.loads((DATEN / "pakete.json").read_text(encoding="utf-8"))


def verzeichnis():
    v = {}
    for x in json.loads((DATEN / "verzeichnis.json").read_text(encoding="utf-8")):
        v.setdefault(x["datei"].removesuffix(".html"), x)
    return v


def karte(slug):
    p = DATEN / "karten" / f"{slug}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def slugs_aus_argumenten(args):
    if "--paket" in args:
        nr = int(args[args.index("--paket") + 1])
        return next(p["karten"] for p in pakete() if p["nr"] == nr)
    if args:
        return args
    return sorted(p.stem for p in (DATEN / "karten").glob("*.json"))


# ---------- Linkprüfung ----------

def holen(url, max_bytes=None):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept-Language": "de-CH,de;q=0.9",
        "Cookie": "SOCS=CAI; CONSENT=YES+1"})  # überspringt die Cookie-Seite von YouTube
    with urllib.request.urlopen(req, timeout=40) as r:
        body = r.read(max_bytes) if max_bytes else r.read()
        return r.status, r.geturl(), body.decode("utf-8", "ignore")


def pruefe_youtube(url):
    vid = re.search(r"(?:v=|youtu\.be/)([\w-]{11})", url).group(1)
    _, _, b = holen(f"https://www.youtube.com/watch?v={vid}&hl=de")
    g = lambda pat: (m.group(1) if (m := re.search(pat, b)) else "")
    status = g(r'"playabilityStatus":\{"status":"([A-Z_]+)"')
    sek = int(g(r'"lengthSeconds":"(\d+)"') or 0)
    titel = html.unescape(g(r'<meta name="title" content="([^"]*)"'))
    return dict(ok=status == "OK", status=status or "unbekannt", sekunden=sek,
                datum=g(r'"publishDate":"([^"]*)"')[:10], kanal=g(r'"ownerChannelName":"([^"]*)"'), titel=titel)


def pruefe_srf(url):
    urn = re.search(r"urn=(urn:srf:video:[\w-]+)", url).group(1)
    _, _, b = holen(f"https://il.srgssr.ch/integrationlayer/2.0/mediaComposition/byUrn/{urn}.json")
    j = json.loads(b)
    c = j["chapterList"][0]
    gesperrt = c.get("blockReason")
    return dict(ok=not gesperrt, status=gesperrt or "OK", sekunden=c.get("duration", 0) // 1000,
                datum=(c.get("date") or "")[:10], kanal="SRF " + j.get("show", {}).get("title", ""), titel=c.get("title", ""))


def pruefe_seite(url):
    try:
        code, final, b = holen(url, 400_000)
    except urllib.error.HTTPError as e:
        return dict(ok=False, status=f"HTTP {e.code}")
    titel = html.unescape(m.group(1).strip()) if (m := re.search(r"<title[^>]*>(.*?)</title>", b, re.S | re.I)) else ""
    verdacht = re.search(r"(seite nicht gefunden|page not found|404)", titel, re.I)
    return dict(ok=not verdacht, status=("Verdacht: Fehlerseite" if verdacht else f"HTTP {code}"),
                titel=titel[:120], weiterleitung=(final if final.rstrip("/") != url.rstrip("/") else ""))


def pruefe(url):
    try:
        if "youtube.com/watch" in url or "youtu.be/" in url:
            r = pruefe_youtube(url)
        elif "srf.ch/play" in url and "urn=" in url:
            r = pruefe_srf(url)
        else:
            r = pruefe_seite(url)
    except Exception as e:  # Netzwerkfehler usw.
        r = dict(ok=False, status=f"Fehler: {e.__class__.__name__}: {e}"[:150])
    r["geprueft"] = HEUTE
    return url, r


def minuten(dauer_text):
    m = re.match(r"([\d,]+)\s*Min", dauer_text or "")
    return float(m.group(1).replace(",", ".")) if m else None


def links(args):
    slugs = slugs_aus_argumenten(args)
    aufgaben = []
    for s in slugs:
        k = karte(s)
        if not k:
            print(f"  (noch keine Daten: {s})")
            continue
        for l in k["links"]:
            aufgaben.append((s, l))
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    urls = sorted({l["url"] for _, l in aufgaben})
    with cf.ThreadPoolExecutor(8) as ex:
        for url, r in ex.map(pruefe, urls):
            cache[url] = r
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    probleme = 0
    for s, l in aufgaben:
        r = cache[l["url"]]
        hinweise = []
        if not r["ok"]:
            hinweise.append(r["status"])
        soll = minuten(l.get("dauer"))
        if soll and r.get("sekunden") and abs(soll - r["sekunden"] / 60) > 1.5:
            hinweise.append(f"Dauer auf der Seite {l['dauer']}, tatsächlich {r['sekunden'] // 60}:{r['sekunden'] % 60:02d}")
        if hinweise:
            probleme += 1
            print(f"PROBLEM  {s}: {l['titel']}\n         {l['url']}\n         {'; '.join(hinweise)}")
    print(f"\n{len(aufgaben)} Links auf {len(slugs)} Karten geprüft, {probleme} mit Problemen.")
    return 1 if probleme else 0


# ---------- Prüftabelle ----------

def alte_links(slug):
    """Links der Seite, wie sie aktuell online (origin/main) ist."""
    try:
        alt = subprocess.run(["git", "show", f"origin/main:{slug}.html"], cwd=REPO, capture_output=True, check=True).stdout.decode("utf-8", "ignore")
    except subprocess.CalledProcessError:
        return []
    return re.findall(r'<a href="(https?://[^"]+)"[^>]*>(.*?)</a>', alt)


def tabelle(args):
    nr = int(args[args.index("--paket") + 1])
    paket = next(p for p in pakete() if p["nr"] == nr)
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    v = verzeichnis()
    z = [f"# Paket {nr}: {paket['name']}", "",
         f"Erstellt am {HEUTE} aus den Kartendaten. Bitte nicht von Hand ändern, sondern die Daten anpassen und neu erzeugen.",
         "Die Videos wurden nicht vollständig angeschaut. Bewertet wurden Titel, Beschreibung, Kanal, Dauer und Datum.",
         "Legende: ✅ geprüft · ⚠️ bitte selbst anschauen · ❌ Problem", ""]
    for s in paket["karten"]:
        k = karte(s)
        titel = v.get(s, {}).get("titel", s)
        z += [f"## {titel}", ""]
        if not k:
            z += ["_Noch keine Daten._", ""]
            continue
        z += ["| | Niveau | Link | Dauer | Quelle | Datum | Begründung |", "|---|---|---|---|---|---|---|"]
        for l in sorted(k["links"], key=lambda l: l["stufe"]):
            r = cache.get(l["url"], {})
            zeichen = "❌" if r and not r.get("ok") else ("⚠️" if l.get("warnung") else ("✅" if r else "?"))
            dauer = f"{r['sekunden'] // 60}:{r['sekunden'] % 60:02d}" if r.get("sekunden") else l.get("dauer", "")
            begr = l.get("notiz", "")
            if l.get("warnung"):
                begr += (" " if begr else "") + "⚠️ " + l["warnung"]
            if r and not r.get("ok"):
                begr += f" ❌ {r.get('status')}"
            sprache = " (Englisch)" if l.get("sprache") == "en" else ""
            z.append(f"| {zeichen} | {STUFEN[l['stufe']]} | [{l['titel']}]({l['url']}){sprache} | {dauer} | {l['quelle']} | {r.get('datum', '')} | {begr} |")
        neu = {l["url"] for l in k["links"]}
        entfernt = {e["url"]: e.get("grund", "") for e in k.get("entfernt", [])}
        alt = [(u, t) for u, t in alte_links(s) if u not in neu]
        if alt:
            z += ["", "**Entfernt (bisher online):**", ""]
            for u, t in alt:
                grund = entfernt.get(u, "")
                z.append(f"- {re.sub('<[^>]+>', '', t)}: {u}" + (f" · {grund}" if grund else ""))
        if k.get("bemerkung"):
            z += ["", k["bemerkung"]]
        z.append("")
    ziel = DATEN / "pruefungen" / f"paket-{nr:02d}.md"
    ziel.parent.mkdir(exist_ok=True)
    ziel.write_text("\n".join(z) + "\n", encoding="utf-8", newline="\n")
    print("geschrieben:", ziel.relative_to(REPO))


# ---------- Statusliste ----------

def status(args):
    v = verzeichnis()
    try:
        online = set(subprocess.run(["git", "ls-tree", "--name-only", "origin/main", "_daten/karten/"], cwd=REPO,
                                    capture_output=True, check=True).stdout.decode().split())
    except subprocess.CalledProcessError:
        online = set()
    z = ["# Statusliste Kompetenzkarten", "", f"Stand {HEUTE}. Erzeugt mit `python -I _werkzeuge/pruefen.py status`.", "",
         "Status: **online** = neu und auf der Website · **bereit** = neu, aber noch nicht online · **offen** = alte Seite", ""]
    total = {"online": 0, "bereit": 0, "offen": 0}
    for p in pakete():
        zeilen = []
        for s in p["karten"]:
            if f"_daten/karten/{s}.json" in online:
                st = "online"
            elif (DATEN / "karten" / f"{s}.json").exists():
                st = "bereit"
            else:
                st = "offen"
            total[st] += 1
            zeilen.append(f"| {v.get(s, {}).get('titel', s)} | `{s}.html` | {st} |")
        z += [f"## Paket {p['nr']}: {p['name']} ({len(p['karten'])} Karten)", "", "| Karte | Seite | Status |", "|---|---|---|"] + zeilen + [""]
    z.insert(5, f"**Total:** {total['online']} online, {total['bereit']} bereit, {total['offen']} offen (von {sum(total.values())})\n")
    (DATEN / "status.md").write_text("\n".join(z) + "\n", encoding="utf-8", newline="\n")
    print("geschrieben: _daten/status.md", total)


if __name__ == "__main__":
    befehl, rest = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("", [])
    if befehl == "links":
        sys.exit(links(rest))
    elif befehl == "tabelle":
        tabelle(rest)
    elif befehl == "status":
        status(rest)
    else:
        print(__doc__)
