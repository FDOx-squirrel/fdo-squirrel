# PRIMER — fdo-squirrel

Arbeitsplan für `fdo-squirrel`: die FDOx-Referenzimplementierung. Liest ein
FDO-ZIP-Paket (`MD.cff` + `CITATION.cff` + beliebiger Inhalt), schreibt
`fdo-metadata.ttl` (DCAT + FDO-Vokabular + CIDOC CRM/CRMdig + GeoSPARQL),
einen Provenienzbericht, ein Mermaid-Übersichtsdiagramm und ein
selbstständiges, republizierbares Bundle-ZIP.

**Ort.** `https://github.com/FDOx-squirrel/fdo-squirrel/blob/main/PRIMER.md`

**So wird es benutzt.** Vollständig zu Beginn jedes Chats hochladen (siehe
A5). Danach genügt "wir machen S3". Teil A gilt immer, Teil B ist die
Übersicht, Teil C beschreibt den einzelnen Schritt.

**Herkunft.** Der erste Entwurf entstand als Nebenprodukt dreier
`fdox-visuals`-Chats (S4–S6: Architektur-, MD.cff- und
CITATION.cff-Schema-Diagramme), die `fdo-squirrel` frisch klonen und gegen
den echten Code lesen mussten, um diese Grafiken korrekt zu bauen. Dieser
Chat ist der erste echte `fdo-squirrel`-Chat: der Entwurf wurde hier gegen
einen frischen Klon nachgeprüft (S0). Dabei stellten sich mehrere Angaben
als ungenau heraus — siehe Nachtrag unten und die Befunde in A1. Die
bereits vorhandene, funktionierende Kernpipeline (Ingest, Validierung,
Crosswalks, RDF-Aufbau, Mermaid-Übersicht, Bundle-Finalisierung) wird
rückwirkend als S1 **erledigt** geführt — sie existierte bereits vor
diesem PRIMER, nur eben ohne ihn dokumentiert.

### Nachtrag 2026-09-08 (dieser Chat, S0)

Gegen einen frischen `git clone` von `FDOx-squirrel/fdo-squirrel`
nachgeprüft. Korrekturen gegenüber dem `fdox-visuals`-Entwurf:

- **CITATION.cff-Datenverlust ist größer als gedacht.** Empirisch
  durchgespielt (nicht nur gelesen): **16 von 22**, nicht 14 von 22
  kartierten Feldern erreichen nie RDF — und darunter auch `authors` und
  `identifiers` (Creators, DOI), nicht nur Nebenfelder. Details in Befund 3.
- **`classification_rules.yaml` liegt unter `fdo/`, nicht unter
  `crosswalks/`.** `fdo/fdo_rdf.py` löst den Pfad relativ zu sich selbst
  auf; `pyproject.toml`s `package-data` bestätigt `fdo = ["classification_rules.yaml"]`.
- **`_apply_md_cff_mapping` ist nicht die größte Funktion im Repo.** Der
  Entwurf verwechselte die Zeilennummer der *nächsten* Funktion (753) mit
  der Länge von `_apply_md_cff_mapping` selbst (tatsächlich Zeile 439–752,
  ≈314 Zeilen). Größte Funktion ist `crosswalk_to_rdf_turtle`
  (Zeile 1263 bis Dateiende 1754, ≈491 Zeilen).
- **Zwei neue Befunde** (fehlten im Entwurf, siehe A1): ein unbenutztes
  `fdo_mermaid_old.py`, und ein verwaistes Root-Duplikat
  `MD.cff.schema.yaml`, das inhaltlich stark vom tatsächlich genutzten
  `schemas/md_cff/MD.cff-schema.yaml` abweicht und von keinem Code
  referenziert wird.
- **`publisher`-Konvention präzisiert.** `cw.publisher_id`/`publisher_label`
  kommen aus dem *ersten Eintrag* der `publishers`-Liste im eingelesenen
  `MD.cff` — `fdo-squirrel` selbst hat keinen hartkodierten Fallback auf
  "Research Squirrel Engineers Network"/Q73901970. Die Konvention wird von
  den erzeugenden Repos (z. B. `fdo-3d-packager`) durchgesetzt, nicht hier.

---

# Teil A — Immer gültig

## A1. Ausgangslage

**Ein Repo, macht ein Paket maschinenlesbar.** (Zur Erinnerung, aus
`fdo-squirrel-registry`s eigenem PRIMER: "`fdo-squirrel` macht *ein* Paket
maschinenlesbar, `fdo-squirrel-registry` macht *viele* auffindbar.")

| Datei/Modul | Rolle |
|---|---|
| `main.py` | Orchestriert die volle Pipeline für **ein** Paket, siehe A2 |
| `ingest/package_source.py` | Lädt ZIP (lokal/URL) |
| `ingest/metadata_ingest.py` | `load_md_cff()`, `load_citation_cff()`, `load_classification_rules()`, `load_md_cff_schema()`, `validate_against_schema()` |
| `crosswalks/md_cff_crosswalk.py` | `MD.cff` → internes `CrosswalkRecord`; `require_id_label()` erzwingt `{id,label}`-Form überall (siehe Teil D — bekannter Widerspruch mit optionalem `creators[].id`, separat getrackt) |
| `crosswalks/citation_crosswalk_engine.py` | `CITATION.cff` → RDF-Tripel, YAML-regelbasiert (Befund 3) |
| `fdo/fdo_rdf.py` | Aggregiert alles zu Turtle (1754 Zeilen); größte Einzelfunktion ist `crosswalk_to_rdf_turtle`, nicht `_apply_md_cff_mapping` (Befund 9, korrigiert) |
| `fdo/classification_rules.yaml` | Datei→`fdo:role`-Heuristik (Befund 7, Pfad korrigiert ggü. Entwurf) |
| `fdo_mermaid.py` | `fdo-metadata.ttl` + `rdf_modelling_report.html` → `fdo_overview.mermaid` (589 Zeilen, tatsächlich importiert) |
| `fdo_mermaid_old.py` | Unbenutzte Vorgängerversion (510 Zeilen), nirgends importiert (Befund 8, neu) |
| `fdo_finalize.py` | `render_mermaid_to_jpg()` (braucht `mmdc`/Node, bricht sanft ab wenn fehlt), `build_finished_bundle()` |
| `schemas/md_cff/MD.cff-schema.yaml` | Tatsächlich genutztes MD.cff-Schema (JSON Schema draft 2020-12) |
| `MD.cff.schema.yaml` (Repo-Root) | Veraltetes Duplikat, weicht stark ab, von keinem Code geladen (Befund 2b, neu) |
| `crosswalks/crosswalk.fdo-metadata.yaml` | Regelbasierte CFF/codemeta/schema.org/Wikidata→RDF-Abbildung (22 `cff:`-Quellfelder, siehe Befund 3) |
| `crosswalks/metadata-crosswalk.py` | Entwicklungswerkzeug zum Bauen/Pflegen des Crosswalk-Graphen; nicht Teil der Laufzeit-Pipeline (nicht von `main.py` importiert) |

**Befunde (geprüft 2026-09-08, dieser Chat, gegen frischen Klon):**

1. **`architecture.mermaid`/`architecture.png` ist veraltet.** Zeigt nur
   Ingest → Crosswalk → Provenance → TTL/Report. Der echte `main.py` läuft
   heute zusätzlich durch: Schema-Validierung (direkt nach dem Laden),
   die Mermaid→JPG-Übersichtsgrafik (`FDOMermaidGenerator` +
   `render_mermaid_to_jpg`), und Bundle-Finalisierung
   (`build_finished_bundle`, schreibt `<slug>-fdo-bundle.zip`). Eine
   korrigierte Fassung liegt bereits in `fdox-visuals`
   (`img/fdox-fdo-squirrel-architecture.svg`/`.png`, S4) — aber nur dort.
2. **Das MD.cff-Schema hatte kein aktuelles Übersichtsdiagramm.** Ein
   früheres, im Umlauf befindliches Bild wich an mehreren Stellen vom
   echten `schemas/md_cff/MD.cff-schema.yaml` ab (`md_cff_version` fehlte,
   `version`/`date_created` waren fälschlich `required`, `publishers`
   müsste 1..\* statt 0..\* sein, `Technique` strukturell anders,
   `contributors`/`related_resources`/`distributions` fehlten ganz).
   Korrigierte Fassung: `fdox-visuals` `img/fdox-md-cff-schema.svg`/`.png`
   (S5).
   - **2b (neu).** Zusätzlich existiert am Repo-Root ein zweites,
     eigenständiges `MD.cff.schema.yaml` mit anderer Struktur (u. a.
     `fdo_id`/`fdo_class` statt `id`/`fdo_type`, kein `$defs`-Block,
     kein `additionalProperties: false`). Es wird von **keinem** Code
     geladen (`main.py` und `ingest/metadata_ingest.py` referenzieren
     ausschließlich `schemas/md_cff/MD.cff-schema.yaml`) — vermutlich ein
     alter Entwurfsstand, der beim Umbau auf `schemas/md_cff/` liegen
     blieb. Siehe S5.
3. **CITATION.cff: 16 von 22 in `crosswalk.fdo-metadata.yaml` kartierten
   `cff:`-Feldern erreichen nie RDF — Zahl in diesem Chat empirisch
   nachgerechnet, nicht nur gelesen (der Entwurf hatte 14 geschätzt).**
   `citation_crosswalk_engine.py`s `_normalize_citation()` liest den
   `CITATION.cff`-Dict auf eine feste Menge herunter, **bevor** die
   Crosswalk-Regeln laufen: `abstract`, `url`, `repository-code`,
   `repository`, `license`, `keywords` werden unverändert durchgereicht —
   das sind genau die 6 Felder, die ankommen. `authors` und `identifiers`
   werden dabei umgeformt zu `author_name`/`author_orcid` bzw.
   `identifier_<scheme>` statt unter ihrem Originalnamen zu erscheinen;
   da die Crosswalk-Regel nach dem Originalnamen sucht
   (`citation.get(source_field)` mit `source_field = "authors"` bzw.
   `"identifiers"`), greift sie ins Leere. Die übrigen 14 Felder
   (`cff-version`, `commit`, `contact`, `contributors`, `date-released`,
   `doi`, `license-url`, `message`, `preferred-citation`, `references`,
   `repository-artifact`, `title`, `type`, `version`) werden gar nicht
   erst in `flat` aufgenommen. Kein Fehler, der crasht oder eine Warnung
   wirft — die Felder verschwinden lautlos. Titel/Version/Datum kommen
   fürs FDO ohnehin aus `MD.cff`, das mildert einen Teil des Verlusts —
   aber Creators/DOI aus `CITATION.cff` sind ebenfalls betroffen, das ist
   weniger harmlos als der Entwurf nahelegte. Visualisiert (nicht
   gefixt) in `fdox-visuals` `img/fdox-citation-cff-schema.svg`/`.png`
   (S6).
4. **`fdo_overview.jpg` braucht `mmdc` (Mermaid CLI / Node.js) auf `PATH`,
   plus Pillow.** Laut README bewusst optional: fehlt sie, wird der
   Schritt mit einer Zeile Warnung übersprungen, alles andere läuft
   weiter. Bestätigt durch README-Lektüre in diesem Chat.
5. **Keine Tests, keine CI.** Kein `test_*.py` im Repo (geprüft, `find`
   über den gesamten Baum), kein `.github/`-Verzeichnis. Nicht bewertet,
   nur festgehalten.
6. **`publisher` kommt aus dem ersten `publishers`-Eintrag des
   eingelesenen `MD.cff`, nicht aus einem Hardcode in `fdo-squirrel`
   selbst** (`crosswalks/md_cff_crosswalk.py`: `pub_id, pub_label =
   publishers[0]`). Dass er in der Praxis "Research Squirrel Engineers
   Network" (Q73901970) ist, ist eine Konvention der erzeugenden Repos
   (z. B. `fdo-3d-packager`), nicht eine Eigenschaft von `fdo-squirrel`
   — Präzisierung ggü. Entwurf, der das als "im Code sichtbar" beschrieb.
7. **`fdo/classification_rules.yaml` ist heuristisch, pro `fdo_type`
   eigene Regeln** (Extension-Listen, Filename-Listen, Path-Prefix-Listen),
   mit `default_role` als Fallback. `MD.cff`/`CITATION.cff` selbst werden
   explizit auf `role: metadata` gematcht. Pfad korrigiert ggü. Entwurf
   (dort fälschlich `crosswalks/classification_rules.yaml`) — bestätigt
   durch `fdo/fdo_rdf.py:100` und `pyproject.toml`s `package-data`.
8. **`fdo_mermaid_old.py` (510 Zeilen) liegt neben `fdo_mermaid.py`
   (589 Zeilen) und wird von nichts importiert** (`main.py` importiert
   ausschließlich `fdo_mermaid.FDOMermaidGenerator`). Vermutlich toter
   Code aus einer früheren Iteration. Neu gefunden in diesem Chat, siehe
   S5.
9. **Größte Einzelfunktion im Repo ist `crosswalk_to_rdf_turtle`
   (`fdo/fdo_rdf.py`, Zeile 1263 bis Dateiende 1754, ≈491 Zeilen), nicht
   `_apply_md_cff_mapping`** (Zeile 439–752, ≈314 Zeilen) wie der Entwurf
   behauptete — der Entwurf hatte die Zeilennummer der *nächsten*
   Funktionsdefinition als Zeilenzahl der Funktion selbst gelesen.
   Korrigiert in diesem Chat.
10. **`fdo-squirrel` ist pip-installierbar** (`pyproject.toml`,
    `[project.scripts] fdo-squirrel = "main:main"`). Passt zur bereits
    bekannten Familienkonvention, den Skript-Pfad über
    `sysconfig.get_path("scripts")` statt `Path(sys.executable).parent`
    aufzulösen (siehe `fdo-3d-packager`-Kontext).

## A2. Zielbild

```
FDO ZIP Package                fdo-squirrel                    Derived Outputs
────────────────               ──────────────                  ────────────────
MD.cff           ──┐
CITATION.cff     ──┼──▶ Metadata ingest
                    │        │
Data/Software/    ──┼──▶     ▼
Models              │   Schema validation
                     │        │
                     │        ▼
                     │   Crosswalk & Mapping Rules ──────────▶ fdo-metadata.ttl
                     │        │                    ╲           (DCAT+FDO+CRM/CRMdig+GeoSPARQL)
                     └──▶ Role classification ───────╲
                          (ZIP → Distribution)         ╲
                               │                        ▼
                               └──────────────────▶ Provenance tracking ──▶ rdf_modelling_report
                                                          │                  (JSON/HTML)
                                                          ▼
                                                   Overview diagram ────▶ fdo_overview
                                                   (Mermaid → JPG)         (Mermaid+JPG)
                                                          │
                                                          ▼
                                                   Bundle finalisation ──▶ <slug>-fdo-bundle.zip
                                                                            (self-contained)
```

Bestätigt gegen `main.py`s tatsächliche Aufrufreihenfolge in diesem Chat
(Load → Validate → Crosswalk MD.cff → Crosswalk CITATION.cff → Aggregate
RDF → Write TTL → HTML-Report → Mermaid → JPG (best effort) → generierte
Dateien als zusätzliche `dcat:Distribution`s → Bundle). Siehe auch
`fdox-visuals`s `img/fdox-fdo-squirrel-architecture.svg` für die
gezeichnete Fassung dieses Diagramms.

Eigenschaften, an denen sich ein Rebuild messen lassen muss:

- **Ein Paket pro Lauf** — `--package`/`-p` oder `config.local.json`
  (nicht committet) oder der `PACKAGE_SOURCE`-Fallback in `main.py`.
- **`output/` wird bei jedem Lauf komplett neu geschrieben**
  (`shutil.rmtree` + `mkdir`) — kein inkrementelles Update.
- **Jede generierte Begleitdatei wird selbst als `dcat:Distribution`
  modelliert**, bevor das Bundle gepackt wird — das Bundle ist
  selbstbeschreibend.
- **Determinismus ist bisher keine geprüfte Eigenschaft** (anders als bei
  `fdox-visuals`/`fdo-3d-packager`) — offener Punkt, siehe S4.

## A3. Querschnittsregeln

- Windows/cmd ist die Referenzplattform.
- Ein Repo pro Chat.
- Reuse heißt kopieren, nicht referenzieren — hier bereits vorhandener
  Bestand, nicht neu zu entscheiden.
- **`publisher` kommt aus dem ersten `MD.cff`-`publishers`-Eintrag**
  (A1 Befund 6) — die Konvention "Research Squirrel Engineers Network"/
  `http://www.wikidata.org/entity/Q73901970`, nie LEIZA, ist Sache der
  erzeugenden Repos, nicht dieses hier. Beim Testen mit Beispielpaketen
  trotzdem beachten, damit Testdaten familienkonform bleiben.
- Sprache/Plattform-Regeln aus "How to work with the user" (informelles
  Deutsch im Chat, `PRIMER.md` deutsch, Code/README englisch).

## A4. Beschlusslage

| Frage | Beschluss | seit |
|---|---|---|
| PRIMER.md für dieses Repo einführen | Ja — dieser PRIMER, verifiziert und bestätigt im ersten echten `fdo-squirrel`-Chat | 2026-09-08 |
| Schrittnummerierung ggü. `fdox-visuals`-Entwurf | Entwurf war nie committet, daher hier neu geordnet: S0 (Verifikation, dieser Chat) und S1 (retroaktiv, Kernpipeline) neu eingeführt; ehemals S1–S6 wurden zu S2/S3/S4/S6/S7/S8; S5 (Aufräumen) neu. Ab jetzt gilt diese Zählung fest | 2026-09-08 |
| `architecture.mermaid` in diesem Repo aktualisieren (S2) | Ja, umgesetzt — Quelle aus `fdox-visuals`s `step_architecture.py`-Struktur übernommen (nicht das SVG selbst, sondern die dort bereits korrigierte Box-/Kantenstruktur) | 2026-09-08 |
| CITATION.cff-Datenverlust fixen? (S3) | Option (a): `_normalize_citation()` erweitert. Bringt 17 von 22 statt 6 von 22 zum Ziel — die restlichen 5 (`cff-version`, `commit`, `message`, `references`, `type`) haben **keinen** `to_term` im Crosswalk-YAML, das ist eine separate, größere Entscheidung (siehe Notiz unten) | 2026-09-08 |
| Für die 5 `to_term`-losen Felder auch noch `crosswalk.fdo-metadata.yaml` erweitern? | Noch nicht entschieden — eigene Entscheidung, nicht Teil von S3s Auftrag ("_normalize_citation() erweitern"). Erfordert, für jedes der 5 Felder ein sinnvolles RDF-Prädikat auszuwählen, nicht nur Python-Code | 2026-09-08, offen, neu |
| `fdo_mermaid_old.py` + Root-`MD.cff.schema.yaml` aufräumen (S5) | Vorschlag: `fdo_mermaid_old.py` löschen (unbenutzt); `MD.cff.schema.yaml` löschen oder explizit als veraltet kennzeichnen — noch nicht entschieden | 2026-09-08, Vorschlag, neu |
| Lokales MD.cff/CITATION.cff für `fdo-3d-packager` (Flos Vorschlag, dort S10) | In `fdo-3d-packager` umgesetzt und laut Parallel-Chat heute committet + gepusht — hier nicht verifiziert (anderes Repo). `fdo-squirrel`s S6 hängt davon ab; im nächsten `fdo-squirrel`-Chat prüfen, ob die Abhängigkeit damit erledigt ist | 2026-09-08, Notiz |
| Instanz-Diagramme ("MD.cff ausgefüllt", "Files and Roles") hier statt in `fdo-3d-packager` (S8) | Bestätigt aus dem Entwurf übernommen — brauchen `fdo-squirrel`s eigene Sicht auf ein verarbeitetes Paket; `fdo_mermaid.py` ist Präzedenzfall für dieses Muster | 2026-09-08, Vorschlag |

## A5. Was in welchem Chat hochgeladen wird

Das ganze Repo als ZIP:

```cmd
robocopy fdo-squirrel fdo-squirrel-bundle /E /XD .git __pycache__ output
```

`output/` explizit ausgeschlossen — das ist Lauf-Ergebnis eines
`--package`-Aufrufs, kein Quellcode, und kann pro Chat mehrere Gigabyte
groß sein (3D-Modelle im Beispielpaket).

---

# Teil B — Schrittübersicht

| ID | Schritt | Repo | hängt ab von | Status |
|---|---|---|---|---|
| S0 | PRIMER verifizieren: Entwurf gegen frischen Klon gegenprüfen, A4-Fragen aufnehmen | fdo-squirrel | — | **erledigt 2026-09-08** |
| S1 | Repo-Skeleton + Kernpipeline (Ingest, Schema-Validierung, Crosswalks, RDF-Aufbau, Mermaid-Übersicht, Bundle-Finalisierung) | fdo-squirrel | — | **erledigt** (vor Einführung dieses PRIMERs, rückwirkend dokumentiert 2026-09-08) |
| S2 | `architecture.mermaid`/`.png` im Repo aktualisieren (Quelle: `fdox-visuals` S4) | fdo-squirrel | S0 | **erledigt 2026-09-08** (Mermaid-Quelle; `.png`-Regeneration braucht lokales `mmdc`, siehe Teil C) |
| S3 | CITATION.cff-Datenverlust entscheiden + fixen (Option a) | fdo-squirrel | S0 | **erledigt 2026-09-08** (17 von 22 Feldern; 5 bleiben ohne `to_term`, neuer Offener Punkt in Teil D) |
| S4 | Determinismus prüfen + fixen (zwei Läufe, `fdo-metadata.ttl` vergleichen) | fdo-squirrel | S0 | **erledigt 2026-09-08** (drei Nichtdeterminismus-Quellen gefunden und gefixt) |
| S5 | Aufräumen: `fdo_mermaid_old.py`, Root-`MD.cff.schema.yaml` (A1 Befund 2b/8, neu) | fdo-squirrel | S0 | offen |
| S6 | CIIC 81 real durchlaufen lassen, sobald `fdo-3d-packager` reale `MD.cff`/`CITATION.cff` liefert | fdo-squirrel | `fdo-3d-packager` S10 (laut Parallel-Chat heute erledigt — hier noch zu prüfen) | offen |
| S7 | Freshford Holy Well (`freshford-st-lachtains-well-low-poly`) ebenso | fdo-squirrel | S6 | offen |
| S8 | Instanz-Diagramme aus einem echten Lauf: "MD.cff ausgefüllt", "Files and Roles" (Muster: `fdo_mermaid.py`) | fdo-squirrel | S6 (braucht einen echten Lauf zum Testen) | offen |

S2, S3, S4 und S5 sind voneinander unabhängig und können in beliebiger
Reihenfolge angegangen werden. S6, S7, S8 hängen an einem echten Lauf mit
realen Paketdaten und damit letztlich an `fdo-3d-packager` S10.

---

# Teil C — Die Schritte

## S0 — PRIMER verifizieren

**Ziel:** den `fdox-visuals`-Entwurf gegen einen frischen Klon von
`fdo-squirrel` prüfen, Ungenauigkeiten korrigieren, A4 mit den
tatsächlichen Entscheidungen füllen.

**Uploads:** keine über den Standard-Bundle hinaus — Verifikation lief
gegen `git clone` direkt im Chat.

**Abnahme:** frischer Klon gegengeprüft, alle Befunde in A1 tragen ein
Prüfdatum, A4 enthält für jede offene Frage einen konkreten Stand
(entschieden oder als Vorschlag markiert), Teil B ist vollständig
nummeriert.

### Erledigt 2026-09-08

Gegen `git clone --depth 1 https://github.com/FDOx-squirrel/fdo-squirrel.git`
geprüft. Ergebnis siehe Nachtrag oben und A1 Befunde 1–10. Wichtigste
Korrektur: CITATION.cff-Datenverlust empirisch nachgerechnet
(16 von 22 statt geschätzter 14 von 22 Felder, inkl. `authors`/
`identifiers`) — Simulation mit `_normalize_citation()` gegen ein
vollständiges Beispiel-`CITATION.cff` mit allen 22 kartierten Feldern.
Zwei neue Befunde gefunden (totes `fdo_mermaid_old.py`, verwaistes
Root-`MD.cff.schema.yaml`), ein Pfadfehler korrigiert
(`classification_rules.yaml` liegt unter `fdo/`, nicht `crosswalks/`),
eine falsche Funktionsgrößenangabe korrigiert (`crosswalk_to_rdf_turtle`
statt `_apply_md_cff_mapping` ist die größte Funktion).

## S1 — Repo-Skeleton + Kernpipeline

**Ziel:** ein FDO-ZIP-Paket vollständig zu `fdo-metadata.ttl` +
Provenienzbericht + Mermaid-Übersicht + republizierbarem Bundle
verarbeiten.

**Uploads:** —

**Abnahme:** `python main.py --package <zip>` läuft durch, schreibt
`output/fdo-metadata.ttl`, `rdf_modelling_report.json`/`.html`,
`fdo_overview.mermaid` (+ `.jpg` falls `mmdc` vorhanden) und
`<slug>-fdo-bundle.zip`.

### Erledigt (rückwirkend dokumentiert 2026-09-08)

Existierte bereits vollständig und funktionsfähig, bevor dieser PRIMER
eingeführt wurde — siehe A1-Tabelle für die beteiligten Module. Kein
neuer Code in diesem Schritt, nur Dokumentation des Ist-Zustands.

## S2 — architecture.mermaid aktualisieren

**Ziel:** `architecture.mermaid`/`.png` im Repo so aktualisieren, dass sie
den echten `main.py`-Ablauf zeigen (Schema-Validierung, Mermaid→JPG,
Bundle-Finalisierung fehlten, A1 Befund 1).

**Uploads:** Repo-Bundle (A5).

**Substanz:** `fdox-visuals` liefert kein rohes Mermaid als Quelle — S4
dort zeichnet die Architektur direkt als SVG (Python, kein `mmdc`, siehe
`fdox-visuals`s eigenes A2-Prinzip "kein externes CLI-Tool"). Übernommen
wurde daher nicht die SVG-Datei, sondern die dort bereits korrigierte
Box-/Kantenstruktur aus `py/step_architecture.py` (Zeilen 61–90,
`SINGLE_ROWS`/`FORK_LEFT`/`FORK_RIGHT`/`INPUT_BOXES`/`OUTPUT_BOXES`),
1:1 in `fdo-squirrel`s eigenen Mermaid-Dialekt (flowchart LR, dagre
Layout, Subgraphs `ZIP`/`FDO`/`RDF`) übertragen.

**Abnahme:** `architecture.mermaid` zeigt alle Schritte aus `main.py`s
tatsächlicher Aufrufkette (siehe A2) — Ingest, Schema-Validierung,
Crosswalk & Mapping Rules, Role classification, Provenance tracking,
Overview diagram, Bundle finalisation, alle vier Ausgabedateien;
`architecture.png` neu gerendert.

### Erledigt 2026-09-08

`architecture.mermaid` neu geschrieben: zusätzlich zu den bisherigen vier
Boxen (Metadata ingest, Crosswalk & Mapping Rules, Role classification,
Provenance tracking) jetzt auch Schema validation, Overview diagram
(Mermaid → JPG) und Bundle finalisation, dazu zwei neue Ausgabeknoten
(`fdo_overview`, `<slug>-fdo-bundle.zip`). Kantenführung entspricht
`fdox-visuals`s korrigierter Struktur: `Data/Software/Models` geht direkt
in `Role classification`, nicht über `Metadata ingest`; `Crosswalk &
Mapping Rules` wird ausschließlich von `Schema validation` gespeist,
nicht direkt von `Metadata ingest`; `Role classification` und `Crosswalk`
laufen als echte Parallelzweige, beide in `fdo-metadata.ttl` und
`Provenance tracking`.

**Verifiziert:** die Mermaid-Syntax wurde gegen den echten
`mermaid`-npm-Parser geprüft (`mermaid.parse()`, inkl. YAML-Frontmatter),
nicht nur von Hand gelesen — Ergebnis `flowchart-v2`, `layout: dagre`
erkannt, keine Syntaxfehler.

**Nicht geschafft:** `architecture.png` neu rendern. `mmdc` (Mermaid CLI)
braucht einen echten Browser (headless Chromium); im Sandkasten hier
gibt es keinen und er lässt sich über die freigegebenen Netzwerk-Domains
nicht nachinstallieren (Chromium-Download läuft über eine nicht
freigegebene Domain, `apt`/snap schlägt fehl). Ein Rendering-Versuch
direkt über `jsdom` (ohne echten Browser) scheitert strukturell:
`mermaid`s Dagre-Layout braucht `getBBox()` für die Boxgrößen, das
`jsdom` nicht implementiert (kein echtes Layout/keine Textmetrik) — ein
Fake-Wert dafür hätte eine geometrisch falsche Grafik erzeugt, das war
nicht die Mühe wert. `architecture.png` muss lokal neu erzeugt werden,
wo `mmdc`/Node bereits eingerichtet ist:

```cmd
mmdc -i architecture.mermaid -o architecture.png -w 2400 -H 1200 --backgroundColor white --scale 3
```

(Breite/Höhe sind Näherungswerte an das bisherige Seitenverhältnis
6747×1970 px, weißer Hintergrund wie beim bisherigen `architecture.png`
bestätigt — `mmdc` passt die tatsächliche Canvas-Größe ohnehin an den
Diagramminhalt an.)

## S3 — CITATION.cff-Datenverlust fixen

**Ziel:** die 16 von 22 nie in RDF ankommenden CITATION.cff-Felder
(A1 Befund 3) so weit wie mit einer Änderung an `_normalize_citation()`
möglich zum Ziel bringen (A4, Option a).

**Uploads:** Repo-Bundle (A5).

**Substanz:** `_normalize_citation()` in
`crosswalks/citation_crosswalk_engine.py` reicht jetzt alle 22 CFF-Felder
unter ihrem Originalnamen durch, nicht nur 6:
- Direkte String-Durchreichung für `cff-version`, `commit`,
  `date-released`, `doi`, `license-url`, `message`,
  `repository-artifact`, `title`, `type`, `version` (zusätzlich zu den
  schon funktionierenden `abstract`/`url`/`repository-code`/
  `repository`/`license`/`keywords`).
- `authors`/`contact`/`contributors` — neue Hilfsfunktion
  `_person_names()` extrahiert lesbare Namen aus den CFF-Person-/
  Entity-Objekten (bevorzugt `name`, sonst `given-names`+`family-names`);
  `authors` wird zusätzlich zu den bestehenden `author_name`/
  `author_orcid`-Feldern unter dem Originalnamen durchgereicht, damit die
  `cff:authors`-Regel greift (die bisher ins Leere lief, weil kein Rule
  je nach `author_name` gesucht hat).
- `identifiers` — Werte zusätzlich als flache Liste unter dem
  Originalnamen durchgereicht, neben den bestehenden
  `identifier_<scheme>`-Einträgen.
- `preferred-citation` (verschachteltes Citation-Objekt) — Titel/DOI/URL
  als Label durchgereicht statt des rohen Dicts (das hätte eine
  Python-Dict-Repräsentation als RDF-Literal erzeugt).
- `references` (Liste von Reference-Objekten) — Titel der einzelnen
  Referenzen als Liste durchgereicht.

**Abnahme:** für ein Testpaket mit vollständigem `CITATION.cff` erreichen
so viele der 22 Felder RDF, wie `crosswalk.fdo-metadata.yaml` ein
`to_term` dafür kennt; geprüft gegen `CitationCrosswalkEngine.crosswalk()`
direkt (isoliert) und gegen das echte `example_fdo/CITATION.cff`.

### Erledigt 2026-09-08

**Wichtiger Befund während der Umsetzung:** "alle 22 Felder erreichen
RDF" war als Abnahme zu optimistisch formuliert — `_normalize_citation()`
zu erweitern reicht nicht für alle 22, weil `crosswalk.fdo-metadata.yaml`
für **5 der 22 Felder gar kein `to_term`** definiert
(`cff-version`, `commit`, `message`, `references`, `type` — die
Crosswalk-Regel dafür hat `to_namespace: null`, ist also nur ein
CFF-Dokumentationseintrag ohne RDF-Ziel). Selbst ein perfekt gefülltes
`flat`-Dict würde für diese 5 keine Triple erzeugen, weil
`CitationCrosswalkEngine.crosswalk()` jede Regel mit ungültigem `to_term`
überspringt — unabhängig vom Wert. Das ist eine andere, größere
Entscheidung (ein RDF-Prädikat für 5 Konzepte auswählen), nicht Teil
dieses Schritts — siehe Teil D.

**Tatsächliches Ergebnis:** mit synthetischen Testdaten (alle 22 Felder
gesetzt) erzeugen jetzt **17 von 22** Feldern mindestens ein Triple
(vorher 6). Mit dem echten `example_fdo/CITATION.cff` (10 gesetzte
Felder, kein `identifiers`/`contact`/`contributors`/`preferred-citation`/
`references` darin): **18 → 25 Triples**, neu u. a. `schema:author
"Florian Thiery"`, `schema:datePublished "2025-01-15"`, `schema:name
"Ogham3D Processing Toolkit"`, `schema:softwareVersion`/`schema:version`
— Creator, Datum und Titel aus `CITATION.cff` erreichen jetzt RDF, vorher
nicht.

**Verifiziert:** `CitationCrosswalkEngine.crosswalk()` isoliert getestet,
zweimal — einmal mit einem synthetischen `CITATION.cff`, das alle 22
Felder setzt (bestätigt: genau die 17 mit `to_term` erzeugen Triples, die
5 ohne bleiben stumm), einmal mit dem echten
`example_fdo/CITATION.cff` über denselben Ladepfad, den `main.py`
benutzt (`yaml.safe_load`, nicht `ingest.metadata_ingest.load_citation_cff`
— das ist eine andere, hier ungenutzte Funktion mit anderer Rückgabeform,
Verwechslungsgefahr beim Testen).

**Nicht geschafft — neuer Befund, nicht Teil dieses Fixes:** ein
End-to-End-Lauf über `main.py --package example_fdo` scheitert schon vor
der CITATION.cff-Verarbeitung, weil `example_fdo/MD.cff` selbst weder
gegen `schemas/md_cff/MD.cff-schema.yaml` validiert (`description`/
`publishers` fehlen als Pflichtfelder, `keywords`/`license` haben die
falsche Form) noch `md_cff_to_crosswalk()`s eigene Anforderungen erfüllt
(`description` fehlt). Das bestehende Beispielpaket im Repo ist damit
unabhängig von diesem Fix nicht lauffähig — neuer Punkt in Teil D.
`crosswalk_to_rdf_turtle()` selbst wurde daher nicht End-to-End
durchlaufen, nur `CitationCrosswalkEngine.crosswalk()` isoliert (das ist
exakt die geänderte Komponente).

## S4 — Determinismus prüfen + fixen

**Ziel:** feststellen, ob zwei Läufe gegen dasselbe Paket bytegleiche
Ausgaben erzeugen (A2, bisher unbekannt), Ursache(n) bei Abweichung
identifizieren und fixen.

**Uploads:** ein Testpaket.

**Substanz:** `python main.py --package <zip>` zweimal laufen lassen,
alle fünf Ausgabedateien vergleichen (`fdo-metadata.ttl`,
`rdf_modelling_report.json`/`.html`, `fdo_overview.mermaid`,
`<slug>-fdo-bundle.zip`).

**Abnahme:** zwei Läufe, `cmp` ohne Ausgabe für alle fünf Dateien.

### Erledigt 2026-09-08

**`example_fdo/` konnte nicht als Testpaket dienen** (Teil D, aus S3:
`example_fdo/MD.cff` validiert nicht). Stattdessen ein separates,
schema-valides Test-Fixture gebaut (gleiches 3D-Modell aus
`example_fdo/data/model/`, `MD.cff` nach aktuellem Schema, `CITATION.cff`
von `example_fdo` übernommen) — nur für diesen Test, nicht Teil des
Patches, nicht committet.

**Drei echte Nichtdeterminismus-Quellen gefunden, alle drei gefixt:**

1. **`fdo/fdo_rdf.py`, `ProvenanceTracker.report()`** — schrieb
   `"generated_at": datetime.now(timezone.utc).isoformat()` in jeden
   Lauf von `rdf_modelling_report.json`. Da diese Datei selbst als
   `dcat:Distribution` gehasht wird, machte das `fdo-metadata.ttl` bei
   jedem Lauf anders. Feld ersatzlos entfernt (kein `RELEASE`-Konzept in
   diesem Repo, ein erfundenes Datum wäre irreführender als gar keins).
2. **`fdo/fdo_rdf.py`, `_load_classification_rules()`** — schrieb den
   **absoluten** Dateisystempfad (`str(rules_path)`) in den Tracker,
   der wiederum in `rdf_modelling_report.json` landet. Das hätte selbst
   bei exakt gleichzeitigen Läufen unterschiedliche Ausgaben erzeugt,
   sobald das Repo an einem anderen Ort ausgecheckt ist — schlimmer als
   reine Zeitabhängigkeit. Ersetzt durch den festen, paketinternen
   relativen Pfad `"fdo/classification_rules.yaml"`.
3. **`main.py`, `write_html_report()`** — dieselbe Art Fund wie 1., nur
   für `rdf_modelling_report.html` (`datetime.utcnow()` in der
   "Generated:"-Zeile). Zeile ersatzlos entfernt.
4. **`fdo_finalize.py`, `build_finished_bundle()`** — die neu
   hinzugefügten Dateien wurden über `zipfile.write()` ins Bundle
   geschrieben, was den echten Datei-Mtime (= Laufzeitpunkt) als
   ZIP-Eintrags-Zeitstempel übernimmt. Das Bundle-ZIP war dadurch nicht
   bytegleich, obwohl sein Inhalt es war. Auf feste `date_time=(1980, 1,
   1, 0, 0, 0)` + `external_attr` für `0o644` umgestellt (`ZipInfo` +
   `writestr()` statt `write()`) — dieselbe Konvention wie in
   `fdo-3d-packager`/`fdox-visuals`.

Alle drei ungenutzt gewordenen `datetime`-Importe (`fdo/fdo_rdf.py`,
`main.py`) entfernt.

**Verifiziert:** zwei frische Läufe gegen das Test-Fixture nach dem Fix
— `fdo-metadata.ttl`, `rdf_modelling_report.json`, `.html`,
`fdo_overview.mermaid` **und** `<slug>-fdo-bundle.zip` alle fünf
bytegleich (`cmp`, keine Ausgabe). Vor dem Fix waren alle fünf
unterschiedlich (die vier Nicht-ZIP-Dateien wegen 1./2./3., die
kaskadieren, weil `fdo-metadata.ttl` die sha256-Hashes der anderen
generierten Dateien enthält; das Bundle-ZIP zusätzlich wegen 4.).

**Nicht geprüft:** Determinismus über verschiedene Python-/
Dict-Iterationsreihenfolgen hinweg (nur derselbe Interpreter-Prozess,
zweimal hintereinander) — für CPython ≥3.7 ist Dict-Reihenfolge
Einfügereihenfolge, insofern nicht erwartungsgemäß ein Risiko, aber
nicht über mehrere Python-Versionen getestet.

## S5 — Aufräumen (Vorschlag, neu)

**Ziel:** die beiden in S0 gefundenen verwaisten Dateien klären
(A1 Befund 2b, 8).

**Uploads:** Repo-Bundle (A5).

**Substanz (Vorschlag):**
- `fdo_mermaid_old.py` löschen — von nichts importiert, `fdo_mermaid.py`
  ist der aktive Nachfolger.
- `MD.cff.schema.yaml` (Root) entweder löschen oder mit einem Kopfkommentar
  "veraltet, siehe `schemas/md_cff/MD.cff-schema.yaml`" versehen, falls es
  aus externen Gründen (Verlinkung, Referenz in einer Präsentation) nicht
  entfernt werden soll.

**Abnahme (Vorschlag):** `grep -r "fdo_mermaid_old" .` und
`grep -r "MD.cff.schema.yaml" .` (außerhalb `.git/`) liefern kein
Ergebnis mehr, oder das Root-Duplikat trägt den Veraltet-Hinweis.

## S6 — CIIC 81 real durchlaufen lassen

**Ziel:** `fdo-squirrel` gegen ein reales, von `fdo-3d-packager`
erzeugtes Paket (CIIC 81 Ogham Stone) laufen lassen, statt gegen
Platzhalterdaten.

**Uploads (Vorschlag):** das von `fdo-3d-packager` erzeugte
`<slug>-fdo-bundle.zip` oder `dist/<slug>/` für CIIC 81.

**Substanz:** hängt an `fdo-3d-packager` S10 (lokale MD.cff/CITATION.cff-
Overrides) — laut Parallel-Chat heute committet und gepusht, hier aber
nicht verifiziert (anderes Repo, siehe A4). Im nächsten `fdo-squirrel`-
Chat: prüfen, ob ein reales CIIC-81-Bundle bereits vorliegt oder erst
erzeugt werden muss.

**Abnahme:** `fdo-metadata.ttl` für CIIC 81 enthält reale Wikidata-
Objekttyp-/Material-Werte, OSM-Spatial-ID, ChronOntology-Periode statt
Platzhalter.

## S7 — Freshford Holy Well

**Ziel:** wie S6, für `freshford-st-lachtains-well-low-poly`.

**Uploads (Vorschlag):** wie S6.

**Abnahme:** wie S6, für das Freshford-Paket.

## S8 — Instanz-Diagramme (Vorschlag)

**Ziel:** aus einem echten, abgeschlossenen `fdo-squirrel`-Lauf (Ausgabe:
`fdo-metadata.ttl` + `rdf_modelling_report.html`) zwei weitere Diagramme
erzeugen, analog zu `fdo_overview.mermaid`/`.jpg`:

- **"Files and Roles"** — welche Datei im Paket welche `fdo:role`
  bekommen hat (Muster: Flos alte Folie 28) — liest dieselben Daten, die
  die Rollen-Klassifikation in `fdo/fdo_rdf.py` schon berechnet.
- **"MD.cff ausgefüllt"** — das eingelesene `MD.cff` als gefülltes
  Klassendiagramm (Muster: Flos alte Folie 27; strukturell verwandt mit
  `fdox-visuals`s S5, nur mit echten Werten statt Feldnamen).

**Uploads (Vorschlag):** ein echtes `output/`-Verzeichnis aus einem
CIIC-81- oder Freshford-Lauf (S6/S7), nicht neu generieren müssen.

**Substanz (Vorschlag, im Chat zu verfeinern):**
- Vermutlich neue Module `fdo_files_roles_diagram.py`/
  `fdo_md_cff_diagram.py`, parallel zu `fdo_mermaid.py`, nicht als
  Erweiterung *von* `fdo_mermaid.py`.
- Offene Frage: Mermaid (wie `fdo_overview`, durch dieselbe
  `render_mermaid_to_jpg()`-Pipeline) oder eigenes SVG (wie
  `fdox-visuals`s Ansatz, dann aber eine neue, `mmdc`-freie Abhängigkeit
  in `fdo-squirrel`) — beide haben in der Familie Präzedenzfälle.
- Vermutlich separates Tool wie `fdo_mermaid.py` es teilweise schon ist
  (in der Pipeline UND einzeln aufrufbar), passt zum bestehenden Muster.

**Abnahme (Vorschlag):** beide Diagramme für den echten CIIC-81-Lauf
erzeugt, Sichtprüfung gegen die alten Folien 27/28 (nicht identisch, aber
inhaltlich vergleichbar — echte Werte statt der alten Beispieldaten).

---

# Teil D — Offene Punkte

- **`example_fdo/MD.cff` ist selbst nicht lauffähig** (neu, gefunden
  während S3): validiert nicht gegen `schemas/md_cff/MD.cff-schema.yaml`
  (`description`/`publishers` fehlen, `keywords`/`license` haben falsche
  Form, `abstract`/`publisher` sind nicht erlaubte Zusatzfelder) und
  erfüllt auch `md_cff_to_crosswalk()`s eigene Mindestanforderungen nicht
  (`description` fehlt). `python main.py --package example_fdo` scheitert
  dadurch schon vor jeder Crosswalk-Verarbeitung. Nicht Teil von S3,
  eigener Schritt nötig, falls das Beispielpaket als Demo/CI-Fixture
  dienen soll.
- **5 CFF-Felder ohne `to_term`** (`cff-version`, `commit`, `message`,
  `references`, `type`) — `_normalize_citation()` reicht sie seit S3
  durch, aber `crosswalk.fdo-metadata.yaml` hat für keins ein RDF-Ziel.
  Eigene Entscheidung, falls gewünscht (A4).
- **Keine Tests, keine CI** (A1 Befund 5) — nicht bewertet, ob das ein
  Problem ist; einfach noch nie Thema gewesen.
- **`fdo_overview.jpg` braucht `mmdc`/Node** (A1 Befund 4) — bewusste
  Abwägung laut README, kein Widerspruch zu lösen.
- **`require_id_label()` vs. optionales `creators[].id`** — bekannter
  Widerspruch zwischen `crosswalks/md_cff_crosswalk.py`s Erzwingung von
  `{id,label}` und dem Schema, das `creators[].id` als optional führt.
  Wird bereits in einem separaten Chat als eigenständiges Upstream-Issue
  getrackt — hier nur Querverweis, kein neuer Schritt.
- **`fdo-squirrel-registry`s Rückfluss-Liste** (aus deren eigenem PRIMER,
  S10 Punkt 8) wartet ebenfalls auf einen `fdo-squirrel`-Chat: abgekürzte
  Klassen-IRIs, `xsd:integer` an weiteren Zeitgrenzen,
  `<DOI>_geom`/`<DOI>_temporal`-IRIs in fremdem Namensraum, ORCID statt
  Personen-URN, `dcat:bbox` statt `geo:hasBoundingBox`. Noch keinem
  Schritt zugeordnet.
- **`crosswalks/metadata-crosswalk.py`** — Entwicklungswerkzeug, das den
  Crosswalk-Graphen baut/pflegt; nicht geprüft, ob es noch aktiv genutzt
  wird oder ebenfalls ein Aufräum-Kandidat für S5 ist.
