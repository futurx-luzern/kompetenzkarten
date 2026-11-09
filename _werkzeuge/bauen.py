"""Baut die Kompetenzkarten-Seiten aus den Daten in _daten/karten/*.json.

Aufruf (im Repo-Ordner):  python -I _werkzeuge/bauen.py [slug ...]
Ohne Angabe werden alle Karten mit Datendatei gebaut.
Ordner mit "_" am Anfang werden von GitHub Pages nicht veröffentlicht.
"""
import html
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
DATEN = REPO / "_daten"
E = html.escape

# Kartentyp (Farbe wie auf den gedruckten Karten)
SOZIAL = {"Soziale Kompetenz", "Kommunikation und Präsentation"}
METHODE = {"Lerntechniken", "Prüfungen bestehen", "Digitale Kompetenzen", "Lesekompetenz", "Methodenkompetenzen"}

STUFEN = {1: "Einstieg", 2: "Vertiefung", 3: "Für Fortgeschrittene"}
STUFEN_INFO = {
    1: "Kurz und einfach erklärt.",
    2: "Länger, mit mehr Hintergrund und Beispielen.",
    3: "Anspruchsvoller, für alle, die es genau wissen wollen.",
}
TYP = {"video": "Video", "lesen": "Lesen", "test": "Test", "audio": "Hören"}

NOTIZFRAGEN = [
    "Worum geht es bei diesem Thema? Erkläre es in zwei, drei Sätzen.",
    "Was ist dir geblieben? Was war neu oder überraschend für dich?",
    "Welches Video oder welcher Text hat dir am meisten geholfen? Warum?",
    "Was hat das Thema mit dir zu tun? Wo begegnet es dir in Schule, Beruf oder Freizeit?",
    "Was möchtest du ausprobieren oder ändern? Was wäre ein erster kleiner Schritt?",
    "Was ist dir unklar geblieben? Worüber möchtest du sprechen?",
]


VERZEICHNIS = {}
if (DATEN / "verzeichnis.json").exists():
    for _v in json.loads((DATEN / "verzeichnis.json").read_text(encoding="utf-8")):
        VERZEICHNIS.setdefault(_v["datei"].removesuffix(".html"), _v)
FAMILIE_KLASSE = {"Selbstkompetenz": "bereich-selbst", "Sozialkompetenz": "bereich-sozial", "Fachkompetenz": "bereich-methode"}


def bereich(kategorie, slug=None):
    """Farbe wie auf der gedruckten Karte (Rückseite: Selbst-, Sozial-, Fachkompetenz)."""
    v = VERZEICHNIS.get(slug or "")
    if v and v["familie"] in FAMILIE_KLASSE:
        return FAMILIE_KLASSE[v["familie"]]
    if kategorie in SOZIAL:
        return "bereich-sozial"
    if kategorie in METHODE:
        return "bereich-methode"
    return "bereich-selbst"


def leiter(n):
    return '<span class="leiter" aria-hidden="true">' + "".join(
        f'<i{" class=\"an\"" if i < n else ""}></i>' for i in range(3)) + "</span>"


def block_methode(slug, k):
    datei = DATEN / "methoden" / f"{slug}.html"
    if not datei.exists():
        return ""
    inhalt = datei.read_text(encoding="utf-8").strip()
    titel = k.get("methode_titel", "So funktioniert die Methode")
    return f"""
<div class="band hell"><div class="innen">
  <h2>{E(titel)}</h2>
  <div class="kasten">
{inhalt}
  </div>
</div></div>
"""


def block_uebung(k):
    u = k.get("uebung")
    if not u:
        return ""
    eintraege = []
    for it in u["aufgaben"]:
        knoepfe = "".join(f'<button type="button">{E(o)}</button>' for o in u["optionen"])
        hinweis = f' data-hinweis="{E(u["hinweis"])}"' if u.get("hinweis") else ""
        eintraege.append(
            f'    <li data-richtig="{E(it["richtig"])}" data-erklaerung="{E(it["warum"])}"{hinweis}>\n'
            f'      <span class="aufgabe">{E(it["text"])}</span>\n'
            f'      <div class="wahl">{knoepfe}</div>\n'
            f'      <p class="rueckmeldung" aria-live="polite"></p>\n'
            "    </li>")
    liste = "\n".join(eintraege)
    return f"""
<div class="band"><div class="innen">
  <h2>Probier es aus</h2>
  <p>{E(u["frage"])} Tippe auf deine Antwort.</p>
  <ul class="uebung">
{liste}
  </ul>
  <p class="uebung-stand"></p>
</div></div>
"""


def block_qr_hinweis(k):
    """Hinweis für gedruckte Karten, deren QR-Code auf diese Seite statt auf die eigene zeigt.
    Daten: "qr_hinweis": [{"karte": "Titel der gedruckten Karte", "seite": "datei.html"}]"""
    teile = []
    for h in k.get("qr_hinweis", []):
        teile.append(
            '<div class="qr-hinweis"><div class="innen"><div class="kasten">'
            f'<b>Hast du die Karte «{E(h["karte"])}» gescannt?</b><br>'
            f'Dann bist du hier auf der falschen Seite. <a href="{E(h["seite"])}">Hier geht es zu deiner Karte →</a>'
            '</div></div></div>')
    return "\n".join(teile)


def block_links(k):
    teile = []
    for s in (1, 2, 3):
        ls = [l for l in k["links"] if l["stufe"] == s]
        if not ls:
            continue
        teile.append(f'  <div class="stufe">{leiter(s)}<h3>{STUFEN[s]}</h3></div>\n'
                     f'  <p class="hinweis">{STUFEN_INFO[s]}</p>\n  <ul class="links">')
        for l in ls:
            teile.append(
                f'    <li><a href="{E(l["url"])}" target="_blank" rel="noopener">'
                f'<span class="chips"><span class="chip">{TYP[l["typ"]]}</span><span class="chip zeit">{E(l["dauer"])}</span></span>'
                f'<span class="t">{E(l["titel"])}</span><span class="q">{E(l["quelle"])}</span></a></li>')
        teile.append("  </ul>")
    return "\n".join(teile)


def seite(slug, k):
    absaetze = "\n".join(f"  <p>{p}</p>" for p in k["text"])
    fragen = "\n".join(f"    <li>{E(f)}</li>" for f in k["fragen"])
    such = "".join(f"<li>{E(s)}</li>" for s in k["suche"])
    notiz = "\n".join(f"      <li>{E(f)}</li>" for f in NOTIZFRAGEN)
    ist_methode = (DATEN / "methoden" / f"{slug}.html").exists()
    link_hinweis = ("Starte beim Einstieg. Für Vertiefung und Fortgeschrittene solltest du die Methode oben schon verstanden haben."
                    if ist_methode else
                    "Starte beim Einstieg und geh so weit, wie es dich interessiert. Du musst nicht alles anschauen.")
    skript = '\n<script src="assets/uebung.js" defer></script>' if k.get("uebung") else ""
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(k["titel"])} · Kompetenzkarten</title>
<link rel="stylesheet" href="assets/karte.css">{skript}
</head>
<body class="{bereich(k["kategorie"], slug)}">
{block_qr_hinweis(k)}
<header class="band farbe held"><div class="innen">
  <a class="zurueck" href="index.html">← Alle Kompetenzkarten</a><br>
  <span class="etikett">{E(k["kategorie"])}</span>
  <h1>{E(k["titel"])}</h1>
  <div class="kasten">
    <p><b>Aufgabe:</b> {E(k["aufgabe"])}</p>
    <p><b>Ziel:</b> {E(k["ziel"])}</p>
  </div>
</div></header>

<main>
<div class="band"><div class="innen">
  <h2>So gehst du vor</h2>
  <ol class="schritte">
    <li><span class="gross">10 Min.</span><b>Einsteigen</b>Lies die Einführung und denk über die Fragen nach.</li>
    <li><span class="gross">35 Min.</span><b>Recherchieren</b>Wähle Videos und Texte aus. Du musst nicht alles anschauen.</li>
    <li><span class="gross">15 Min.</span><b>Notizen machen</b>Halte Stichworte fest für das Gespräch mit deiner Lehrperson.</li>
  </ol>
</div></div>

<div class="band weiss"><div class="innen">
  <h2>Worum geht es?</h2>
{absaetze}
</div></div>
{block_methode(slug, k)}{block_uebung(k)}
<div class="band hell"><div class="innen">
  <h2>Fragen zum Nachdenken</h2>
  <ul class="fragen">
{fragen}
  </ul>
</div></div>

<div class="band"><div class="innen">
  <h2>Videos und Links</h2>
  <p class="hinweis">{link_hinweis}</p>
{block_links(k)}
  <h3 style="margin-top:2rem">Selber suchen</h3>
  <ul class="such">{such}</ul>
</div></div>

<div class="band farbe"><div class="innen">
  <h2>Notizen für das Gespräch</h2>
  <div class="kasten notizen">
    <p>Nach der Recherche sprichst du mit deiner Lehrperson über das Thema. Mach dir zu diesen Fragen Stichworte:</p>
    <ul>
{notiz}
    </ul>
  </div>
</div></div>
</main>

<footer>Kompetenzkarten · FuturX · <a href="index.html">Übersicht</a></footer>
</body>
</html>
"""


def uebersicht():
    """Baut index.html aus _daten/verzeichnis.json (nur gedruckte Karten)."""
    import re
    def slugify(t):
        t = t.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
        return re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    eintraege = {}
    for v in json.loads((DATEN / "verzeichnis.json").read_text(encoding="utf-8")):
        alt = eintraege.get(v["datei"])
        # bei zwei Karten mit derselben Seite: den Titel nehmen, der zum Dateinamen passt
        if alt is None or slugify(v["titel"]) == v["datei"].removesuffix(".html"):
            eintraege[v["datei"]] = v
    teile = []
    for familie, klasse, text in (
        ("Selbstkompetenz", "bereich-selbst", "Wie du dich selbst organisierst, motivierst und gesund bleibst."),
        ("Sozialkompetenz", "bereich-sozial", "Wie du mit anderen sprichst, zusammenarbeitest und Konflikte löst."),
        ("Fachkompetenz", "bereich-methode", "Wie du lernst, Prüfungen vorbereitest und digital sicher arbeitest."),
    ):
        karten = [v for v in eintraege.values() if v["familie"] == familie]
        gruppen = {}
        for v in karten:
            gruppen.setdefault(v["kategorie"], []).append(v)
        gross = sorted((k for k, l in gruppen.items() if len(l) >= 2), key=lambda k: -len(gruppen[k]))
        weitere = sorted((v for k, l in gruppen.items() if len(l) < 2 for v in l), key=lambda v: v["titel"])
        bloecke = []
        for kat, liste in [(k, sorted(gruppen[k], key=lambda v: v["titel"])) for k in gross] + ([("Weitere Themen", weitere)] if weitere else []):
            links = "".join(
                f'<li><a href="{E(v["datei"])}" data-suche="{E((v["titel"] + " " + kat).lower())}">{E(v["titel"])}</a></li>'
                for v in liste)
            bloecke.append(f'<div class="gruppe"><h3>{E(kat)}</h3><ul class="liste">{links}</ul></div>')
        teile.append(f"""
<section class="{klasse}">
<div class="band farbe"><div class="innen"><h2>{familie}</h2><p>{text}</p></div></div>
<div class="band"><div class="innen">
{chr(10).join(bloecke)}
</div></div>
</section>""")
    seite_html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kompetenzkarten · Übersicht</title>
<link rel="stylesheet" href="assets/karte.css">
</head>
<body class="uebersicht">
<header class="band weiss"><div class="innen">
  <span class="etikett">FuturX</span>
  <h1>Kompetenzkarten</h1>
  <div class="kasten">
    <p>Zu jeder Kompetenzkarte gibt es hier eine Seite mit einer kurzen Einführung, Videos und Links zum Recherchieren und Fragen für das Gespräch mit deiner Lehrperson.</p>
    <p>Scanne den QR-Code auf deiner Karte oder such das Thema hier aus.</p>
  </div>
  <label class="suche-label" for="suche">Thema suchen</label>
  <input id="suche" class="suche" type="search" placeholder="z.B. Prüfung, Motivation, Konflikt" autocomplete="off">
  <p id="kein-treffer" class="hinweis" hidden>Kein Thema gefunden. Versuch es mit einem anderen Wort.</p>
</div></header>
<main>
{"".join(teile)}
</main>
<footer>Kompetenzkarten · FuturX</footer>
<script>
(function () {{
  var feld = document.getElementById('suche'), leer = document.getElementById('kein-treffer');
  feld.addEventListener('input', function () {{
    var q = feld.value.trim().toLowerCase(), treffer = 0;
    document.querySelectorAll('.liste a').forEach(function (a) {{
      var ok = !q || a.getAttribute('data-suche').indexOf(q) > -1;
      a.parentElement.hidden = !ok; if (ok) treffer++;
    }});
    document.querySelectorAll('.gruppe').forEach(function (g) {{ g.hidden = !g.querySelector('li:not([hidden])'); }});
    document.querySelectorAll('main section').forEach(function (s) {{ s.hidden = !s.querySelector('li:not([hidden])'); }});
    leer.hidden = treffer > 0;
  }});
}})();
</script>
</body>
</html>
"""
    (REPO / "index.html").write_text(seite_html, encoding="utf-8", newline="\n")
    print("gebaut: index (", len(eintraege), "Karten )")


def main():
    if sys.argv[1:] == ["--uebersicht"]:
        uebersicht()
        return
    wahl = set(sys.argv[1:])
    for datei in sorted((DATEN / "karten").glob("*.json")):
        slug = datei.stem
        if wahl and slug not in wahl:
            continue
        k = json.loads(datei.read_text(encoding="utf-8"))
        (REPO / f"{slug}.html").write_text(seite(slug, k), encoding="utf-8", newline="\n")
        print("gebaut:", slug)


if __name__ == "__main__":
    main()
