# Werkzeuge für die Kompetenzkarten

Die Seiten der Kompetenzkarten werden nicht von Hand geschrieben, sondern aus Daten erzeugt.
Ordner mit `_` am Anfang (`_daten`, `_werkzeuge`) werden von GitHub Pages **nicht** veröffentlicht.

## Wichtigste Regel

**Keine Datei umbenennen oder löschen**, auf die ein gedruckter QR-Code zeigt. Das gilt für alle `*.html`-Seiten im Hauptordner.
Sonderfälle stehen in [`_daten/qr-sonderfaelle.md`](../_daten/qr-sonderfaelle.md).

## Ordner

| Pfad | Inhalt |
|---|---|
| `_daten/karten/<seite>.json` | Inhalt einer Karte: Texte, Fragen, Links, Übung |
| `_daten/methoden/<seite>.html` | Mini-Einführung «So funktioniert …» für Arbeitstechniken (optional) |
| `_daten/verzeichnis.json` | Alle gedruckten Karten: Titel, Kompetenzbereich, Kategorie, Aufgabe, Ziel, QR-Ziel |
| `_daten/pakete.json` | Welche Karte in welchem Paket bearbeitet wird |
| `_daten/linkpruefung.json` | Letzte Linkprüfung (wird automatisch geschrieben) |
| `_daten/pruefungen/paket-NN.md` | Prüftabelle eines Pakets für die Freigabe (wird erzeugt) |
| `_daten/status.md` | Statusliste aller Karten (wird erzeugt) |
| `assets/` | Stylesheet, Schrift, Übungs-Skript |

## Befehle

Alle Befehle im Ordner `kompetenzkarten-repo` ausführen:

```
python -I _werkzeuge/bauen.py                    # alle Kartenseiten neu bauen
python -I _werkzeuge/bauen.py nein-sagen         # nur eine Seite
python -I _werkzeuge/bauen.py --uebersicht       # index.html neu bauen
python -I _werkzeuge/pruefen.py links            # alle Links prüfen
python -I _werkzeuge/pruefen.py links --paket 1  # Links eines Pakets prüfen
python -I _werkzeuge/pruefen.py tabelle --paket 1
python -I _werkzeuge/pruefen.py status
```

Die Linkprüfung meldet tote Links, gesperrte oder gelöschte Videos und Videos, deren Dauer nicht zur Angabe auf der Seite passt.
Sie lässt sich jederzeit wiederholen, zum Beispiel einmal pro Semester.

## Ablauf pro Paket

1. Branch anlegen: `git switch -c paket-N` (von `main`)
2. Für jede Karte des Pakets `_daten/karten/<seite>.json` anlegen, bei Arbeitstechniken auch `_daten/methoden/<seite>.html`
3. `pruefen.py links --paket N` und `pruefen.py tabelle --paket N`
4. **Freigabe 1:** Prüftabelle `_daten/pruefungen/paket-NN.md` durchsehen, Videos mit ⚠️ selbst anschauen
5. `bauen.py`, Seiten lokal und in der Handy-Ansicht prüfen
6. `pruefen.py status`, committen, Pull Request erstellen
7. **Freigabe 2:** Pull Request mergen. Nach 1 bis 2 Minuten ist alles online.

## Kriterien für Links

- Drei Stufen: **Einstieg** (kurz, einfach), **Vertiefung** (länger, bis ca. 30 Min.), **Für Fortgeschrittene** (anspruchsvoller)
- Seriöse Quellen, kein Verkaufsfokus, aktuell genug, Deutsch, Schweizer Bezug bevorzugt
- Englisch nur bei «Für Fortgeschrittene», nur ohne gute deutsche Alternative, und gekennzeichnet (`"sprache": "en"`)
- Bei Arbeitstechniken: Mini-Einführung, wenn sinnvoll eine Übung, und **alle Links behandeln die Methode selbst**

## Felder einer Karte (`_daten/karten/<seite>.json`)

| Feld | Pflicht | Bedeutung |
|---|---|---|
| `titel`, `kategorie`, `aufgabe`, `ziel` | ja | wie auf der gedruckten Karte (siehe `verzeichnis.json`) |
| `text` | ja | Absätze für «Worum geht es?» (HTML erlaubt, z.B. `<strong>`) |
| `fragen` | ja | Fragen zum Nachdenken |
| `suche` | ja | Suchbegriffe |
| `links` | ja | Liste mit `stufe` (1–3), `typ` (video, lesen, test, audio), `url`, `titel`, `dauer`, `quelle`; optional `notiz` (Begründung), `warnung` (bitte selbst prüfen), `sprache` |
| `methode_titel` | nein | Titel der Mini-Einführung, z.B. «So funktioniert die SMART-Methode» |
| `uebung` | nein | `frage`, `optionen`, `aufgaben` (je `text`, `richtig`, `warum`), optional `hinweis` |
| `entfernt` | nein | Links der alten Seite mit `url` und `grund` (erscheinen in der Prüftabelle) |
| `qr_hinweis` | nein | Hinweis-Kasten für fremde Karten, deren QR-Code auf diese Seite zeigt |
| `bemerkung` | nein | Freier Text unter der Tabelle in der Prüftabelle |
