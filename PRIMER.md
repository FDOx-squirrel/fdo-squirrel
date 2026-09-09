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
| `fdo_finalize.py` | `render_mermaid_to_jpg()` (braucht `mmdc`/Node, bricht sanft ab wenn fehlt), `build_finished_bundle()` |
| `fdo_manifest.py` | Neu (S14): schreibt `FDOx.yaml`, ein kurzes Build-Manifest (Generator-Version, strukturelle Vermutung über das erzeugende Upstream-Tool) |
| `fdo_visuals_utils.py` | Neu (S8): gemeinsame Stilkonstanten für die vier neuen Diagramme — Palette, Fira Sans, `resvg-py`-Rendering. An `fdox-visuals`s `visuals_utils.py` angelehnt (kopiert, nicht referenziert), nicht neu erfunden |
| `fdo_files_roles_common.py` / `fdo_files_roles_graph.py` | "Files and Roles" — welche Datei welche `fdo:role` bekommen hat. `_common` (S15, vormals `_diagram.py`) trägt nur noch die geteilten Extraktions-/Gruppierungsfunktionen; das eigenständige Faktenblatt aus S8 wurde in S15 wieder entfernt (redundant zum Graph) |
| `fdo_ttl_snippet.py` | Drei dunkle "Code-Card"-JPGs für Folien (S15, in S16 zu drei Karten ausgebaut): Metadata (fuller), Distributions (Beispiel-Blöcke), Linked Open Data (externe IRIs, nach Domain priorisiert) |
| `fdo_md_cff_diagram.py` / `fdo_md_cff_graph.py` | Neu (S8): "MD.cff ausgefüllt" als Faktenblatt bzw. Knoten-Graph — das eingelesene `MD.cff` mit echten Werten |
| `fonts/` | Neu (S8): vendorte Fira-Sans-TTFs (Regular + Bold), von `fdox-visuals` kopiert (A3: Reuse heißt kopieren) — jetzt ein eigenes, leeres Python-Package (`__init__.py`) wegen `package-data`, siehe S8 |
| `schemas/md_cff/MD.cff-schema.yaml` | Tatsächlich genutztes MD.cff-Schema (JSON Schema draft 2020-12) |
| `crosswalks/crosswalk.fdo-metadata.yaml` | Regelbasierte CFF/codemeta/schema.org/Wikidata→RDF-Abbildung (22 `cff:`-Quellfelder, siehe Befund 3) |
| `crosswalks/metadata-crosswalk.py` | Entwicklungswerkzeug zum Bauen/Pflegen des Crosswalk-Graphen; nicht Teil der Laufzeit-Pipeline, aber legitim — kein Aufräum-Kandidat (S5) |

*(`fdo_mermaid_old.py` und das Root-`MD.cff.schema.yaml` standen hier bis
S5 — beide gelöscht, siehe Befund 8/2b unten und S5 in Teil C.)*

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
| `fdo_mermaid_old.py` + Root-`MD.cff.schema.yaml` aufräumen (S5) | Beide gelöscht (`git rm`, siehe PATCH-README — ZIPs können keine Löschungen transportieren) | 2026-09-08 |
| Lokales MD.cff/CITATION.cff für `fdo-3d-packager` (Flos Vorschlag, dort S10) | In `fdo-3d-packager` umgesetzt und laut Parallel-Chat heute committet + gepusht — hier nicht verifiziert (anderes Repo). `fdo-squirrel`s S6 hängt davon ab; im nächsten `fdo-squirrel`-Chat prüfen, ob die Abhängigkeit damit erledigt ist | 2026-09-08, Notiz |
| Instanz-Diagramme ("MD.cff ausgefüllt", "Files and Roles") hier statt in `fdo-3d-packager` (S8) | Bestätigt aus dem Entwurf übernommen — brauchen `fdo-squirrel`s eigene Sicht auf ein verarbeitetes Paket; `fdo_mermaid.py` ist Präzedenzfall für dieses Muster | 2026-09-08, Vorschlag |
| Wann ein Release machen? (S10) | Erst wenn S6, S7 und S8 durch sind, nicht vorher — Flos Entscheidung | 2026-09-08 |
| Versions-Metadaten stimmten nicht mit der echten Release-Historie überein (S11) | `git tag` zeigt fünf echte Releases bis `v0.3.1` (23.02.2026), aus Arbeit vor diesem PRIMER — `CITATION.cff`/`pyproject.toml`/`README.md` standen aber noch auf `v0.1`/`0.1.0`, bei keinem Tag mitgezogen. Auf `v0.3.1` synchronisiert. Unabhängig von S10 — das war kein neuer Release, nur ein Sync-Fehler bei bereits existierenden | 2026-09-08 |
| Architektur-Bild-Referenz: eigenes `architecture.png` oder Cross-Repo-Link auf `fdox-visuals`? (S11) | Cross-Repo-Link (`raw.githubusercontent.com/.../fdox-visuals/...`) — Flos Entscheidung, bewusste Ausnahme von A3 "Reuse heißt kopieren, nicht referenzieren". Begründung: Bild dort bereits korrekt und aktuell, eigenes `architecture.png` wartet weiterhin auf lokales `mmdc` (S2). Lokale `architecture.mermaid`/`architecture.png` bleiben im Repo, werden nur von der README nicht mehr eingebunden | 2026-09-08 |
| Python-Mindestversion (README sagte 3.10, `pyproject.toml` sagt 3.9, Code braucht nachweislich nur 3.9) | README war der Tippfehler, auf 3.9 korrigiert (S9) — Flos Entscheidung | 2026-09-08 |
| fdo-squirrel-registry-Rückflussliste (5 Punkte, `fdo-squirrel-registry`s PRIMER, S10 Punkt 8) | Alle fünf bereits im Code umgesetzt, empirisch gegen einen echten Lauf bestätigt (S12) — vermutlich in Ad-hoc-Arbeit zwischen dem 2026-09-04-Befund und diesem PRIMER gefixt, nie hier dokumentiert. Kein Code geändert, nur verifiziert | 2026-09-09 |
| Nicht-IRI-förmige `id` bei unveröffentlichten Paketen (S13) | Fallback-URN aus dem Package-Source-Dateinamen (`urn:fdo-squirrel:unpublished/<slug>`) — Flos Entscheidung. `resolve_dataset_id()` löst das einmal in `main.py` auf, `cw` wird per `dataclasses.replace()` aktualisiert, damit Citation-Crosswalk-Engine und `crosswalk_to_rdf_turtle()` dieselbe ID sehen | 2026-09-09 |
| `fdo-3d-packager`s Pin auf `fdo-squirrel` bumpen (Commit `504b7af`, 8 Commits hinter HEAD) | Noch nicht gemacht — gehört in einen eigenen `fdo-3d-packager`-Chat, nicht hier mit reingezogen (A3: ein Repo pro Chat). Flo wollte es ursprünglich hier mit erledigen, davon abgeraten | 2026-09-09 |
| Wie festhalten, welche `fdo-squirrel`-Version ein FDO erzeugt hat? (S14) | Neue `FDOx.yaml` (Build-Manifest, gespeist aus `rdf_modelling_report.json`) + `prov:wasGeneratedBy`/`prov:SoftwareAgent` in der TTL selbst + `generator`-Feld im JSON-Report — Flos Entscheidung. Eine vollständige Toolchain-Datei (mit Blender-/Nexus-Versionen) bleibt außerhalb — das kann nur `fdo-3d-packager` wissen, eigener Chat | 2026-09-09 |
| S8-Rendering: Mermaid (mmdc) oder eigenes SVG? | Eigenes SVG, wie `fdox-visuals` (`resvg-py`, kein `mmdc` nötig) — Flos Entscheidung | 2026-09-09 |
| S8-Stil: Faktenblatt oder Knoten-Graph? | Beides — vier Diagramme statt zwei (Faktenblatt + Graph, für "Files and Roles" und "MD.cff ausgefüllt" je einmal) — Flos Entscheidung, nachdem er seine ursprünglichen Referenzbilder (Knoten-Graphen) gezeigt hatte | 2026-09-09 |
| "Files and Roles"-Faktenblatt behalten? (S15) | Nein, entfernt — Flo verglich beide Stile nebeneinander mit echten Daten: der Graph zeigt dieselbe Gruppierung, aber mit echten Verbindungen, das Faktenblatt bot daneben keinen Mehrwert. Bei "MD.cff" bleiben beide, da das Faktenblatt dort deutlich mehr Text kompakter unterbringt als der Graph könnte | 2026-09-09 |
| TTL-Snippet-als-JPG für Präsentationen (S15) | Automatisch pro Lauf, wie die anderen S8-Diagramme (nicht als separates, manuell aufgerufenes Werkzeug) — Flos Entscheidung | 2026-09-09 |
| TTL-Snippet-Inhalt nach Flos Test (S16) | Zu wenig Inhalt, zu niedrige Auflösung — Flo wollte "mehr Metadaten" + "Distributions" + hatte offene Frage nach einer dritten Idee. Umgesetzt: drei Karten (Metadata/Distributions/Linked Open Data), 2,5-fache Render-Auflösung | 2026-09-09 |
| PNG statt/zusätzlich zu JPG für die Snippet-Karten + `fdo_overview` (S17) | Flo fand die abgerundeten Ecken im JPG kaputt (schwarze Keile statt transparent) und wollte PNG für Einheitlichkeit mit den anderen S8-Diagrammen — dazu gleich `fdo_overview.png` neben `.jpg`. Beides umgesetzt, PNG zusätzlich zu JPG (nicht ersetzend) | 2026-09-09 |

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
| S5 | Aufräumen: `fdo_mermaid_old.py`, Root-`MD.cff.schema.yaml` (A1 Befund 2b/8) | fdo-squirrel | S0 | **erledigt 2026-09-08** (beide gelöscht, `crosswalks/metadata-crosswalk.py` bleibt — ist kein Aufräum-Kandidat, siehe Teil D) |
| S6 | CIIC 81 real durchlaufen lassen | fdo-squirrel | `fdo-3d-packager` S10 | **erledigt 2026-09-09** |
| S7 | Freshford Holy Well (`freshford-st-lachtains-well-low-poly`) ebenso | fdo-squirrel | S6 | **erledigt 2026-09-09** |
| S8 | Instanz-Diagramme aus einem echten Lauf: "MD.cff ausgefüllt", "Files and Roles" — je zwei Stile (Faktenblatt + Knoten-Graph) | fdo-squirrel | S6 | **erledigt 2026-09-09** (S15: "Files and Roles"-Faktenblatt wieder entfernt) |
| S15 | Nachtrag zu S8: "Files and Roles"-Faktenblatt entfernen (redundant zum Graph) + neues TTL-Snippet-JPG für Präsentationen | fdo-squirrel | S8 | **erledigt 2026-09-09** (S16: Snippet zu drei Karten ausgebaut) |
| S16 | Nachtrag zu S15: TTL-Snippet höher auflösen, drei gezielte Karten (Metadata/Distributions/Linked Open Data) statt einer generischen | fdo-squirrel | S15 | **erledigt 2026-09-09** (S17: PNG-Bug gefixt) |
| S17 | Nachtrag zu S16: transparentes PNG für die drei TTL-Snippet-Karten (JPG-Alpha-Bug gefixt), `fdo_overview.png` zusätzlich zu `.jpg` | fdo-squirrel | S16 | **erledigt 2026-09-09** |
| S9 | README.md auffrischen (Python-Version, MD.cff-Feldliste, Status-Abschnitt) | fdo-squirrel | — | **erledigt 2026-09-08** |
| S10 | Release: Versionsbump + Git-Tag | fdo-squirrel | — (A4: Flos Entscheidung — S6/S7/S8 sind jetzt alle durch) | offen |
| S11 | Versions-Metadaten mit tatsächlicher Release-Historie synchronisieren + Architektur-Bild-Referenz | fdo-squirrel | — | **erledigt 2026-09-08** |
| S12 | fdo-squirrel-registry-Rückflussliste verifizieren + `repository-code`-Org korrigieren | fdo-squirrel | — | **erledigt 2026-09-09** |
| S13 | Zwei Bugs aus S6/S7 gegen echte Pakete: fehlendes Escaping in Turtle-Literalen, nicht-IRI-förmige `id` bei unveröffentlichten Paketen | fdo-squirrel | S6, S7 | **erledigt 2026-09-09** |
| S14 | Generator-Version im Output festhalten: PROV-O in der TTL, `generator`-Feld im JSON-Report, neue `FDOx.yaml` als Build-Manifest | fdo-squirrel | — | **erledigt 2026-09-09** |

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

## S5 — Aufräumen

**Ziel:** die beiden in S0 gefundenen verwaisten Dateien klären
(A1 Befund 2b, 8).

**Uploads:** Repo-Bundle (A5).

**Substanz:**
- `fdo_mermaid_old.py` gelöscht — von nichts importiert, `fdo_mermaid.py`
  ist der aktive Nachfolger.
- `MD.cff.schema.yaml` (Root) gelöscht — veraltete Vorstufe von
  `schemas/md_cff/MD.cff-schema.yaml`, von keinem Code geladen.

**Abnahme:** `grep -r "fdo_mermaid_old" .` und
`grep -r "MD.cff.schema.yaml" .` (außerhalb `.git/`) liefern kein
Ergebnis mehr.

### Erledigt 2026-09-08

Beide Dateien gelöscht, nach nochmaliger Fixed-String-Suche (nicht die
erste, ungenaue Regex-Suche aus S0 — `.` im Dateinamen ist im Regex ein
Wildcard und hätte auch `MD.cff-schema.yaml` mitgetroffen) gegen den
gesamten Baum: außer diesem PRIMER selbst referenziert nichts einen der
beiden Namen.

**`crosswalks/metadata-crosswalk.py` geprüft, nicht gelöscht** — der
offene Punkt aus Teil D ist damit beantwortet: es ist der
Entwicklungswerkzeug-Generator, der `crosswalks/crosswalk.fdo-metadata.yaml`
baut/pflegt (Docstring: "FDO Metadata Crosswalk Builder", eigenständig
in VS Code lauffähig, keine CLI-Argumente). Dass `main.py` es nicht
importiert, macht es nicht tot — die Datei, die es erzeugt, wird von der
Pipeline aktiv gebraucht. Kein Aufräum-Kandidat, bleibt.

**Da ZIPs keine Löschungen transportieren können, sind
`fdo_mermaid_old.py` und `MD.cff.schema.yaml` als manuelle Schritte im
PATCH-README aufgeführt** (`git rm`), nicht im ZIP selbst.

## S6 — CIIC 81 real durchlaufen lassen

**Ziel:** `fdo-squirrel` gegen ein reales, von `fdo-3d-packager`
erzeugtes Paket (CIIC 81 Ogham Stone) laufen lassen, statt gegen
Platzhalterdaten.

**Uploads:** `cork-ogham-stone-ciic-81-ucc-4-fdo-bundle_trim.zip` (von
Flo aus `fdo-3d-packager`s echtem Lauf hochgeladen, `model.obj`/
`model.nxs` schon rausgetrimmt).

**Substanz:** `MD.cff`/`CITATION.cff`/`data/` aus dem Upload
extrahiert (die von `fdo-3d-packager`s eigenem `build_fdo`-Schritt schon
mitgelieferten `fdo-squirrel`-Outputs — `fdo-metadata.ttl` etc. —
bewusst nicht übernommen, siehe Nachtrag), neu gezippt, durch den
heutigen `fdo-squirrel`-HEAD laufen lassen.

**Abnahme:** `fdo-metadata.ttl` für CIIC 81 enthält reale Wikidata-
Objekttyp-/Material-Werte, OSM-Spatial-ID, ChronOntology-Periode statt
Platzhalter.

### Erledigt 2026-09-09

**Wichtiger Fund vor dem eigentlichen Lauf:** `fdo-3d-packager`s
`requirements.txt` pinnt `fdo-squirrel` auf Commit `504b7af` — acht
Commits hinter dem heutigen HEAD, komplett vor diesem PRIMER (siehe
A4). Das in Flos Upload bereits eingebettete `fdo-metadata.ttl` spiegelt
also nicht die heutige Arbeit. Deshalb: rohes `MD.cff`/`CITATION.cff`/
`data/` aus dem Bundle gezogen und selbst nochmal durch den aktuellen
`fdo-squirrel`-Stand laufen lassen, statt dem mitgelieferten `ttl` zu
vertrauen.

Abnahme erfüllt: `dct:type`/`dct:subject` zeigen auf echte Wikidata-Q-IDs
(`Q2016147` "Inscribed Ogham stone", `Q22731` "Stone", `Q121592049`),
`dct:spatial` auf einen echten OSM-Node
(`openstreetmap.org/node/11071361392`), `owl:sameAs` auf eine echte
ChronOntology-Periode. Diff gegen das alte, mit Commit `504b7af`
gebaute `ttl` zeigt den konkreten Effekt von S3: drei neue Tripel,
`schema:author "Anne-Karoline Distel"`, `schema:author "Florian
Thiery"`, `schema:datePublished "2024-06-05"` — vorher fehlten Creators
und Datum aus `CITATION.cff` komplett, jetzt sind sie da.

Beim Durchlaufen zwei echte Bugs gefunden, siehe S13 — CIIC 81 selbst
war davon nicht betroffen (hat schon eine echte DOI als `id`), aber der
Escaping-Bug ist ein allgemeiner Code-Fehler, keine Paket-Eigenheit.

## S7 — Freshford Holy Well

**Ziel:** wie S6, für `freshford-st-lachtains-well-low-poly`.

**Uploads:** `freshford-st-lachtains-well-low-poly-fdo-bundle.zip` (Flos
Upload, ungetrimmt).

**Abnahme:** wie S6, für das Freshford-Paket.

### Erledigt 2026-09-09

Wie S6: rohes `MD.cff`/`CITATION.cff`/`data/` extrahiert, durch den
heutigen `fdo-squirrel`-Stand laufen lassen. `dct:subject` zeigt auf
echte Wikidata-Q-IDs (`Q229370`, `Q110840`); Freshford hat kein
`temporal`/OSM-`spatial` in seinem `MD.cff`, insofern dazu nichts zu
prüfen.

**Das ist das Paket, das beide S13-Bugs tatsächlich aufgedeckt hat:**
Freshford hat noch keine Zenodo-DOI (`id` ist `fdo-3d-packager`s
Platzhaltertext) und eine mehrzeilige, aus Sketchfab importierte
`description` — beides kommt bei CIIC 81 so nicht vor. Ohne ein zweites,
noch unveröffentlichtes Paket wie dieses wären beide Bugs synthetischen
Tests vermutlich weiter entgangen.

## S8 — Instanz-Diagramme

**Ziel:** aus einem echten, abgeschlossenen `fdo-squirrel`-Lauf zwei
weitere Diagramme erzeugen, analog zu `fdo_overview.mermaid`/`.jpg`:

- **"Files and Roles"** — welche Datei im Paket welche `fdo:role`
  bekommen hat (Muster: Flos alte Folie 28).
- **"MD.cff ausgefüllt"** — das eingelesene `MD.cff` als gefülltes
  Klassendiagramm, echte Werte statt Feldnamen (Muster: Flos alte
  Folie 27).

**Uploads:** Repo-Bundle (A5); zur Verifikation die beiden echten
Bundles aus S6/S7.

**Substanz (nach Diskussion mit Flo, zwei Design-Fragen geklärt, A4):**
- **Rendering:** eigenes SVG (`resvg-py`), wie `fdox-visuals` — kein
  `mmdc` nötig, dafür eine neue optionale Abhängigkeit.
- **Stil:** Flo zeigte seine ursprünglichen Referenzbilder (Knoten-
  Graphen: zentraler Knoten/Datei-Boxen mit Pfeilen zu Rollen-Knoten) —
  deutlich anders als der erste, selbst entworfene "Faktenblatt"-Stil
  (gestapelte Panels). Entscheidung: **beide**, macht aus den zwei
  geplanten Diagrammen vier.

**Abnahme:** vier Diagramme (SVG+PNG) für CIIC 81 und Freshford erzeugt,
Sichtprüfung gegen Flos Referenzbilder, im `fdox-visuals`-Stil (Farben,
Fira Sans), deterministisch, aus einem echten `pip install` heraus
lauffähig.

### Erledigt 2026-09-09

**Sechs neue Dateien:**
- `fdo_visuals_utils.py` — Palette (`#004473` Navy, `#0E9488` Teal,
  `#8034C9` Purple, `#C2790C` Orange, `#161B2E`/`#5B6478` Text), Fira-
  Sans-`@font-face`, `resvg_py.svg_to_bytes()`-Wrapper, `wrap_text()`
  (inkl. Hart-Umbruch für lange Wörter ohne Leerzeichen — siehe Fund
  unten), Pfeil-Marker + S-Kurven-Connector für die Graph-Varianten. An
  `fdox-visuals`s `visuals_utils.py` angelehnt, kopiert nicht importiert
  (A3).
- `fdo_files_roles_diagram.py` (Faktenblatt) + `fdo_files_roles_graph.py`
  (Knoten-Graph, importiert die Extraktions-/Gruppierungslogik aus dem
  Faktenblatt-Modul statt sie zu duplizieren — beide Stile können sich
  über die Dateiliste nie widersprechen). Liest `fdo-metadata.ttl` mit
  demselben Regex-Ansatz, den `fdo_mermaid.py` schon für seine eigene
  Distribution-Erkennung nutzt (keine neue RDF-Parser-Abhängigkeit).
  Rollen mit mehr als 6 Dateien werden nach Verzeichnis gruppiert
  ("viewer/ — 8 files") statt einzeln aufgelistet — sonst wird ein
  3DHOP-Viewer-Bundle (~24 Dateien) zur Ausgabe, nicht zur Information.
- `fdo_md_cff_diagram.py` (Faktenblatt) + `fdo_md_cff_graph.py`
  (Knoten-Graph, importiert dieselben Feld-Extraktionsfunktionen aus dem
  Faktenblatt-Modul). Fünf Abschnitte (Core, Agents, Classification,
  Space & Time, Heritage Object & Technique), nur die tatsächlich
  gefüllten werden gezeichnet.

**`fonts/` vendort** (zwei Fira-Sans-TTFs von `fdox-visuals` kopiert,
A3) — musste zu einem echten Python-Package werden (`__init__.py`),
sonst fehlen die Fonts bei einem normalen (nicht editierbaren)
`pip install`, wie ihn `fdo-3d-packager`s Pin verwendet. Verifiziert:
frisches venv, `pip install` (nicht `-e`), `fdo_visuals_utils.FONTS_DIR`
zeigt korrekt auf die installierten TTFs, kompletter Lauf über den
echten `fdo-squirrel`-Konsolenbefehl erzeugt alle vier Diagramme.

**`pyproject.toml`:** die neun neuen Module in `py-modules`, `fonts` in
`packages` + `package-data`; `resvg-py` als optionales Extra
(`fdo-squirrel[diagrams]`), nicht in die Basis-Abhängigkeiten — dasselbe
Muster wie `mmdc` für `fdo_overview.jpg`: fehlt es, wird die
PNG-Erzeugung übersprungen, das SVG steht trotzdem, der Rest der
Pipeline läuft unbeeinflusst weiter.

**Zwei echte Layoutfehler beim Testen mit echten Daten gefunden und
gefixt** (Freshfords/CIIC-81s MD.cff, nicht synthetisch):
1. Eine lange URL ohne Leerzeichen (`related_resources`-Ziel) lief über
   den rechten Panelrand hinaus — `wrap_text()` konnte nur an
   Leerzeichen umbrechen. Fix: Wörter länger als die Zeilenbreite werden
   jetzt zusätzlich hart in Stücke geschnitten.
2. Im Knoten-Graphen für "MD.cff ausgefüllt" lief mehrfach der Inhalt
   über den unteren Rand der Satellitenbox hinaus in die nächste Box
   hinein. Ursache: die Höhenberechnung zählte nur die Wert-Zeilen, nicht
   die Label-Zeile jeder Zeile mit. Fix: `+1` pro Zeile in der
   Höhenberechnung.

**Verifiziert, gegen beide echten Pakete (CIIC 81, Freshford):**
- Alle vier Diagramme erzeugt, visuell geprüft (siehe die beiden
  Fixes oben) — Ergebnis entspricht in der Struktur Flos
  Referenzbildern, in der Farbgebung/Typografie der `fdox-visuals`-
  Familie.
- Determinismus (S4) hält für alle vier SVG+PNG-Paare **und**
  `fdo-metadata.ttl`: zwei Läufe, alles bytegleich.
- Aus einem echten, nicht-editierbaren `pip install` heraus (frisches
  venv, `pip install <repo>`, dann `resvg-py` dazu) über den
  `fdo-squirrel`-Konsolenbefehl gelaufen — nicht nur im Dev-Checkout.

**README.md** um die vier neuen Ausgabedateien + den optionalen
`resvg-py`-Hinweis ergänzt.

## S15 — Nachtrag zu S8: Faktenblatt raus, TTL-Snippet rein

**Ziel:** zwei Korrekturen, nachdem Flo S8 gegen ein echtes, mit
`fdo-3d-packager` gebautes CIIC-81-Bundle getestet hatte.

**Uploads:** Repo-Bundle (A5); die vier S8-PNGs aus Flos echtem Testlauf
zur Sichtprüfung.

**Substanz (nach Diskussion mit Flo, A4):**
1. **"Files and Roles"-Faktenblatt entfernen.** Nebeneinander mit dem
   Graph verglichen: gleiche Gruppierung, aber ohne die echten
   Verbindungslinien — bot keinen eigenständigen Wert. Bei "MD.cff"
   bleiben beide Stile, das Faktenblatt bringt dort spürbar mehr Text
   unter als der Graph vernünftig könnte.
2. **Neu: TTL-Snippet als JPG**, automatisch pro Lauf — Flos Idee für
   Präsentationsfolien, nach zwei Beispielbildern (dunkler Code-Block,
   syntax-eingefärbt, mit Objekt-Foto und DOI-Verweis daneben — das Foto/
   Maskottchen-Layout bleibt manuelles Folienbauen, nur der Code-Block
   wird automatisiert).

**Abnahme:** `fdo_files_roles.svg`/`.png` existieren nicht mehr;
`fdo_ttl_snippet.svg`+`.jpg` entstehen bei jedem Lauf, zeigen eine feste,
kuratierte Auswahl echter Turtle-Zeilen, deterministisch.

### Erledigt 2026-09-09

**Faktenblatt-Rückbau:** `fdo_files_roles_diagram.py` gelöscht, seine
geteilten Hilfsfunktionen (`_extract_distributions`/`_group_for_display`/
`_ROLE_ORDER`/`_ROLE_COLORS`/`_GROUP_THRESHOLD`) in ein neues
`fdo_files_roles_common.py` verschoben (ohne führenden Unterstrich, jetzt
öffentlich, da `fdo_files_roles_graph.py` sie importiert). `main.py` ruft
`write_files_roles_diagram()` nicht mehr auf, die Datei ist raus aus
`generated_files`. Dabei den in einem früheren Chat-Abschnitt schon
diskutierten, aber nie gepatchten Schutz mit eingebaut: eine feste Liste
`FDO_SQUIRREL_OWN_FILES` (eigene Signaturdateien) wird jetzt aus
`extract_distributions()` rausgefiltert — falls doch mal ein fertiges
`<slug>-fdo-bundle.zip` als frisches `--package` reinkommt (genau das war
Flos Testfall), tauchen `fdo-metadata.ttl`, die Reports etc. nicht mehr
als vermeintlicher Paketinhalt auf.

**Neues `fdo_ttl_snippet.py`:** liest `fdo-metadata.ttl` mit einem
Regex-Ansatz wie `fdo_mermaid.py`, wählt aus einer festen, priorisierten
Prädikat-Liste (`dct:title`, `dct:description`, `dct:creator`,
`dct:publisher`, `dct:license`, `dct:type`, `dct:spatial`,
`dct:subject`) bis zu sieben tatsächlich vorhandene Zeilen aus,
leichtgewichtige regex-basierte Syntax-Einfärbung (IRIs, Literale,
Prädikate je eine Farbe), dunkler Card-Hintergrund mit drei "Traffic
Light"-Punkten oben (Code-Screenshot-Ästhetik). Rendert über `resvg-py`
zu PNG-Bytes, dann direkt mit Pillow als JPG gespeichert (kein Umweg über
eine PNG-Datei) — Ausgabeformat war explizit Flos Wunsch ("als JPG").

**Ein Extraktions-Bug unterwegs gefunden und gefixt:** die erste Version
suchte den schließenden `.` des Kern-Dataset-Blocks auf einer eigenen
Zeile — in der echten TTL sitzt er aber direkt an der letzten
Prädikat-Zeile dran (`... .`  ohne Zeilenumbruch davor). Matchte dadurch
gar nichts, `fdo_ttl_snippet.jpg` bestand nur aus dem leeren Card-Rahmen.
Fix: die Dataset-Deklaration selbst als Anker suchen (`re.search`, nicht
an den Blockanfang gebunden — die @prefix-Zeilen und der Kern-Block sind
NICHT durch eine Leerzeile getrennt, nur einzelne `\n`), dann bis zur
nächsten echten Leerzeile lesen.

**Verifiziert, gegen beide echten Pakete (CIIC 81, Freshford):**
- Card zeigt für CIIC 81 sieben Zeilen (alle acht Wunsch-Prädikate bis
  auf `dct:subject`, da `dct:type` schon vorhanden war und die Kappung
  bei 7 greift), für Freshford sechs (kein `dct:spatial`/`dct:type` im
  MD.cff, fällt korrekt auf die vorhandenen zurück, inkl. der
  Fallback-URN aus S13 als Subject-Zeile).
- Lange `dct:description`-Werte werden auf ~90 Zeichen gekürzt (Freshford
  hat eine sehr lange, mehrzeilige Beschreibung — im Snippet sauber
  einzeilig mit "…" gekappt).
- Determinismus (S4) hält für `fdo_ttl_snippet.svg`+`.jpg` **und** alle
  übrigen Ausgaben: zwei Läufe, alles bytegleich (auch das JPG selbst,
  trotz JPEG-Encoder).
- Aus einem echten, nicht-editierbaren `pip install` heraus (frisches
  venv) über den `fdo-squirrel`-Konsolenbefehl gelaufen, nicht nur im
  Dev-Checkout.

**`pyproject.toml`:** `fdo_files_roles_diagram` aus `py-modules` raus,
`fdo_files_roles_common` + `fdo_ttl_snippet` rein. **README.md:**
Output-Abschnitt auf die jetzt drei (statt zwei) S8-Diagrammthemen
aktualisiert.

## S16 — Nachtrag zu S15: TTL-Snippet ausgebaut

**Ziel:** zwei Rückmeldungen von Flo nach dem ersten echten Test von
S15s TTL-Snippet (gegen `C:\tmp\fdo\CO074-148----.zip`, ein rohes,
nicht von `fdo-3d-packager` gebautes Testpaket): die Auflösung war zu
niedrig für eine Folie, und der Inhalt zu wenig — er wollte mehr
Metadaten und die Distributions sehen, dazu die offene Frage nach einer
dritten sinnvollen Karte.

**Uploads:** Repo-Bundle (A5); zur Verifikation dieselben zwei echten
Pakete wie zuvor.

**Substanz:**
1. **Auflösung:** `RENDER_SCALE = 2.5` — `resvg-py` bekommt das 2,5-fache
   der SVG-eigenen Breite/Höhe als Zielgröße, verlustfrei, da Vektor-
   Inhalt (kein Raster-Upscaling).
2. **Metadata-Karte, fuller:** von einer auf sieben Prädikate
   gedeckelten Wunschliste auf eine Ausschlussliste umgestellt (nur
   `dcat:distribution`, `dct:provenance`, `prov:wasGeneratedBy` raus —
   der Rest des Kern-Blocks bleibt, gedeckelt bei 20 Zeilen statt 7).
3. **Neue Distributions-Karte:** zwei bis drei echte
   `dcat:Distribution`-Blöcke vollständig (Pfad/mediaType/byteSize/
   role/sha256), je einer pro Rolle wo möglich (`metadata`/`model`/
   `documentation`/`data`), damit die Form eines Distribution-Eintrags
   sichtbar wird, nicht nur sein Name.
4. **Neue Links-Karte** (Flos offene Frage "c)"): `rdfs:label`/
   `owl:sameAs`-Zeilen, deren Subjekt (oder bei `owl:sameAs` auch das
   Objekt) eine echte externe IRI ist — Wikidata, OpenStreetMap,
   ChronOntology, ORCID, SPDX — nicht eine von `fdo-squirrel`s eigenen
   `urn:fdo-squirrel:`-Knoten. Die "das FDO reiht sich in einen
   föderierten Wissensgraphen ein"-Geschichte in einer Karte.

**Abnahme:** drei Karten, deutlich schärfer als vorher, Metadata-Karte
zeigt spürbar mehr als 7 Zeilen, Distributions-Karte zeigt echte
Blockstruktur, Links-Karte zeigt Wikidata/OSM/ChronOntology zuerst.

### Erledigt 2026-09-09

Wie oben umgesetzt. `write_ttl_snippet_jpg()` (eine Datei) ersetzt durch
`write_ttl_snippet_cards()` (schreibt `fdo_ttl_snippet_metadata.svg/.jpg`,
`_distributions.svg/.jpg`, `_links.svg/.jpg` — eine Karte wird
übersprungen, nicht leer geschrieben, wenn nichts zu zeigen ist, z. B.
keine externen Links gefunden). `main.py` entsprechend auf eine
dynamische Dateiliste umgestellt statt zweier fixer Pfade.
`FDO_SQUIRREL_OWN_FILES` in `fdo_files_roles_common.py` auf die drei
neuen Kartennamen aktualisiert; dabei auch `fdo_overview.png` ergänzt
(eine ältere Namenskonvention, in Flos rohem Testpaket noch vorhanden,
war vorher nicht in der Liste und wäre als Paketinhalt aufgetaucht).

**Zwei echte Content-Bugs beim ersten Rendern der neuen Karten gefunden
und gefixt, nicht nur bei Flos Test:**
1. Die Metadata-Karte zeigte eine zweite Zeile, die aussah wie ein
   Prädikat (`crmdig:D1_Digital_Object, crm:E73_Information_Object,
   fdo:3DDataFDO`), tatsächlich aber die Fortsetzung der
   `a dcat:Dataset, <Typen> ;`-Deklaration war, die vor dem
   Extraktions-Ankerpunkt beginnt. Fix: diese erste Zeile explizit
   verwerfen, nicht als Prädikat-Zeile behandeln.
2. Die erste Links-Karten-Version sortierte nach Dateireihenfolge —
   dadurch standen selbstreferenzielle Zeilen (Sketchfab-Quelle,
   Zenodo-DOI-Eigenlabel) oben, die eigentlich interessanten
   Wikidata-Labels fehlten komplett (durch den 7-Zeilen-Deckel
   verdrängt). Fix: `_LINK_DOMAIN_PRIORITY`-Liste, sortiert zuerst nach
   bekannten LOD-Domains (Wikidata → OSM → ChronOntology → ORCID → ROR
   → SPDX), Rang aus Subjekt **und** Objekt (wichtig für `owl:sameAs`,
   wo die Zieldomain die eigentlich interessante ist, nicht das eigene
   `_temporal`-Subjekt).

**Verifiziert, gegen beide echten Pakete (CIIC 81, Freshford):**
- Alle drei Karten für beide Pakete erzeugt, visuell geprüft (siehe die
  zwei Fixes oben).
- Links-Karte zeigt nach dem Fix für CIIC 81 an erster Stelle
  `wikidata.org/entity/Q2016147 rdfs:label "Inscribed Ogham stone"` und
  `Q22731 "Stone"`, dann OSM, dann den ChronOntology-`owl:sameAs`-Link —
  genau die Reihenfolge, die die Domain-Priorität vorgibt.
- Determinismus (S4) hält für alle drei Kartenpaare **und**
  `fdo-metadata.ttl`: zwei Läufe, alles bytegleich.
- Freshford (weniger Daten, kein `dct:spatial`/`dct:type`) erzeugt
  trotzdem alle drei Karten ohne Fehler — Metadata/Distributions/Links
  passen sich an, was tatsächlich vorhanden ist.

## S17 — Nachtrag zu S16: PNG statt kaputtem JPG-Alpha

**Ziel:** ein echter Rendering-Bug, den Flo an einem Screenshot zeigte —
die abgerundeten Kartenecken kamen im JPG als schwarze Keile statt als
(gedachte) Übergänge raus. Dazu sein Wunsch nach PNG-Ausgabe für alle
Diagramme, inklusive `fdo_overview`.

**Uploads:** Repo-Bundle (A5); Flos Screenshot des kaputten Renders zur
Fehlerdiagnose.

**Substanz:**
1. **Root Cause:** `_rasterise()` nahm die von `resvg-py` gelieferten
   PNG-Bytes (mit korrektem Alpha-Kanal — transparent außerhalb der
   `rx="18"`-Rundung) und rief `Image.convert("RGB")` auf, um daraus ein
   JPG zu bauen. `convert("RGB")` **verwirft** den Alpha-Kanal einfach,
   behält aber die rohen RGB-Werte darunter — bei den transparenten
   Ecken war das zufällig (0,0,0), also Schwarz. Kein Kompositieren auf
   einen Hintergrund, nur ein stillschweigend fallengelassener Kanal.
2. **Fix:** `resvg-py`s PNG-Bytes werden jetzt direkt als
   `fdo_ttl_snippet_*.png` geschrieben (kein PIL-Umweg nötig, `resvg`
   liefert schon PNG) — echte Transparenz an den Ecken. Das JPG bleibt
   zusätzlich bestehen (nicht jedes Folienwerkzeug mag Transparenz),
   wird aber jetzt korrekt auf `CARD_BG` kompositiert
   (`Image.alpha_composite`), nicht mehr das Alpha stillschweigend
   verworfen.
3. **`fdo_overview.png`:** `render_mermaid_to_jpg()` liefert von `mmdc`
   ohnehin ein PNG als Zwischenschritt, das bisher nach der JPG-
   Konvertierung einfach gelöscht wurde. Jetzt wird es vorher an
   `fdo_overview.png` kopiert und bleibt erhalten — kein neuer
   Renderaufwand, nur eine Zeile weniger Löschung.

**Abnahme:** `fdo_ttl_snippet_*.png` hat an den Kartenecken Alpha 0
(geprüft, nicht nur angenommen); das JPG zeigt an derselben Stelle
`CARD_BG`, kein Schwarz; `fdo_overview.png` existiert neben `.jpg`.

### Erledigt 2026-09-09

Wie oben umgesetzt. `CARD_BG_RGB = (0x16, 0x1B, 0x2E)` als Tupel-
Variante von `CARD_BG` ergänzt, für `Image.new("RGBA", size, CARD_BG_RGB
+ (255,))` als Kompositions-Hintergrund. `write_ttl_snippet_cards()`
schreibt jetzt SVG+PNG+JPG statt SVG+JPG; `FDO_SQUIRREL_OWN_FILES` um
die drei `.png`-Varianten ergänzt. `main.py` nimmt `fdo_overview.png`
(`jpg_path.with_suffix(".png")`) mit in `generated_files` auf.

**Verifiziert:**
- **Alpha direkt geprüft, nicht nur visuell**: `PIL.Image.getpixel((0,
  0))` auf `fdo_ttl_snippet_metadata.png` → `(0, 0, 0, 0)` (voll
  transparent), Kartenmitte → `(22, 27, 46, 255)` (deckendes
  `#161B2E`) — exakt `CARD_BG`.
- JPG-Version dieselbe Stelle: `CARD_BG`-Farbe statt Schwarz, kein
  Artefakt mehr.
- Determinismus (S4) hält für alle PNG- **und** JPG-Ausgaben: zwei
  Läufe, alles bytegleich.
- Gegen beide echten Pakete (CIIC 81, Freshford) durchgetestet.

**Nicht geprüft:** `fdo_overview.png`/`.jpg` selbst — `mmdc` steht in
diesem Sandkasten weiterhin nicht zur Verfügung (bekannte Einschränkung
seit S2), der Code-Pfad (`shutil.copyfile` vor der JPG-Konvertierung)
ist aber trivial genug, dass ein Fehlschlag dort unwahrscheinlich ist;
Flo bestätigt das beim nächsten echten Lauf.

## S9 — README.md auffrischen

**Ziel:** die drei durch S1–S5 entstandenen Diskrepanzen zwischen
README und Repo-Realität beheben.

**Uploads:** Repo-Bundle (A5).

**Substanz:**
- Python-Mindestversion: README sagte 3.10, `pyproject.toml` sagt 3.9,
  Code enthält keine 3.10-typische Syntax (kein `match`, kein
  ungeschütztes `X | Y` als Typannotation) — README auf 3.9 korrigiert.
- `MD.cff`-Feldliste unter "Input requirements" vervollständigt:
  `creators`/`contributors`/`identifiers`/`related_resources`/
  `heritage_object`/`technique`/`funding` fehlten ganz, obwohl im
  echten Schema vorhanden.
- Status-Abschnitt um die jetzt (S4) tatsächlich geprüfte Eigenschaft
  "deterministic, byte-identical output across repeated runs" ergänzt —
  vorher stand da nur "deterministic identifiers", was etwas anderes ist
  und nichts über den Rest der Ausgabe aussagt.

**Abnahme:** die drei genannten Diskrepanzen sind behoben, sonst nichts
an der README verändert.

### Erledigt 2026-09-08

Umgesetzt wie oben beschrieben. **`architecture.png` bleibt bewusst
unverändert** — das Bild selbst ist weiterhin die alte 4-Boxen-Fassung
(bestätigt: Repo-Stand vor diesem Patch zeigt noch dieselben Maße wie
vor S2), weil die lokale `mmdc`-Regeneration aus S2 noch aussteht. Kein
neuer Fund, nur zur Erinnerung — sobald das Bild lokal neu gerendert
ist, passt es automatisch zum bereits korrigierten `architecture.mermaid`.

## S11 — Versions-Metadaten synchronisieren + Architektur-Bild-Referenz

**Ziel:** zwei von Flo entdeckte Diskrepanzen beheben, die S9 nicht
gefangen hatte.

**Uploads:** Repo-Bundle (A5).

**Substanz:**
- **Versions-Sync:** `git tag` zeigt fünf echte, bereits veröffentlichte
  Releases (`v0.1` 28.01., `v0.1.1` 28.01., `v0.2` 22.02., `v0.3` 22.02.,
  `v0.3.1` 23.02. — alle vor diesem PRIMER, aus früherer Arbeit).
  `CITATION.cff` (`version`, `date-released`), `pyproject.toml`
  (`version`) und `README.md` (Kopf + Status-Abschnitt) auf `v0.3.1` /
  `0.3.1` / `2026-02-23` nachgezogen.
- **Architektur-Bild:** README verlinkt jetzt per Raw-URL auf
  `fdox-visuals`s bereits korrigiertes Bild
  (`img/fdox-fdo-squirrel-architecture.png`) statt auf das eigene,
  weiterhin veraltete `architecture.png`. Bewusste Ausnahme von A3
  (siehe A4) — Flos Entscheidung, Cross-Repo-Link statt Warten auf
  lokales `mmdc`.

**Abnahme:** alle drei Versionsangaben stimmen mit dem `v0.3.1`-Tag
überein; das README-Bild zeigt die korrigierte 7-Schritte-Architektur.

### Erledigt 2026-09-08

Umgesetzt wie oben. `architecture.mermaid` und das lokale (weiterhin
veraltete) `architecture.png` bleiben unangetastet im Repo — nur die
README bindet sie nicht mehr ein. Sollte `fdo-squirrel` die
Cross-Repo-Abhängigkeit später wieder loswerden wollen (z. B. sobald
`mmdc` lokal gelaufen ist), ist das ein Ein-Zeilen-Rücktausch in
`README.md`, nichts Strukturelles.

**Nicht geklärt:** ob `CITATION.cff`s `repository-code`
(`https://github.com/Research-Squirrel-Engineers/fdo-squirrel/`) noch
stimmt — die Organisation heißt inzwischen `FDOx-squirrel`, nicht mehr
`Research-Squirrel-Engineers`. Beiläufig aufgefallen bei diesem Schritt,
nicht Teil des Auftrags, nicht angefasst — neuer Punkt in Teil D.
*(In S12 geklärt: Redirect funktioniert per GitHub-301, trotzdem auf die
kanonische URL korrigiert.)*

## S12 — fdo-squirrel-registry-Rückflussliste verifizieren + repository-code korrigieren

**Ziel:** die fünf Punkte aus `fdo-squirrel-registry`s eigenem PRIMER
(S10, Punkt 8 — "Rückfluss nach fdo-squirrel") abarbeiten, dazu die
`repository-code`-Org in `CITATION.cff` korrigieren.

**Uploads:** Repo-Bundle (A5); `fdo-squirrel-registry` geklont (read-only,
nur zum Nachlesen der genauen Befunde, nichts dort verändert).

**Substanz:** Die fünf Punkte aus dem Registry-PRIMER (Befunde 3, 24, 12,
15, 16 dort):

1. Abgekürzte CRM/CRMdig-Klassen-IRIs (`crm:E73`, `crmdig:D1`, `crmdig:D9`
   statt der vollen Formen)
2. Fehlende `rdfs:label` an Wikidata-Konzept- und OSM-Orts-IRIs
3. `urn:fdo-squirrel:person/<hash>` statt ORCID-IRI, obwohl ORCID vorlag
4. `xsd:integer` statt eines Datumstyps an Zeitgrenzen
5. `dcat:bbox` statt `geo:hasBoundingBox`

Dazu: `CITATION.cff`s `repository-code` auf die kanonische
`FDOx-squirrel`-Org-URL korrigiert (A4).

**Abnahme:** für ein Testpaket mit allen fünf betroffenen Feldern gesetzt
erzeugt `fdo-metadata.ttl` in jedem der fünf Fälle die vom Registry-Profil
gewünschte Form.

### Erledigt 2026-09-09

**Alle fünf bereits im Code — nichts zu fixen, nur zu bestätigen.** Ein
eigens gebautes Testpaket (CIIC-83-Fixture: `heritage_object.material`/
`object_type` mit Wikidata-IDs, `spatial` mit OSM-ID + `bounding_box`,
`temporal` mit `start`/`end`, `CITATION.cff`-Autor mit ORCID) durch die
echte Pipeline laufen lassen und `fdo-metadata.ttl` geprüft:

1. `crmdig:D1_Digital_Object`, `crm:E73_Information_Object`,
   `crmdig:D9_Data_Object` — voll ausgeschrieben, an allen Stellen.
2. `<...wikidata.../Q1361864> rdfs:label "Ogham stone" .` und ebenso für
   `Q159762` — Wikidata-Konzepte bekommen ihr Label.
3. `<...openstreetmap.../relation/62273> rdfs:label "County Cork,
   Ireland" .` — OSM-Ort ebenso. Sitzt in `_apply_md_cff_mapping()`s
   `iri_optional`-Zweig als spatial-Sonderfall (Kommentar im Code
   erklärt es: "spatial has no {id, label} pairing in the schema - label
   sits as a sibling field").
4. `dcat:startDate "0300"^^xsd:gYear`, `dcat:endDate "0699"^^xsd:gYear`.
5. `geosparql:hasBoundingBox "<...EPSG/0/4326> ENVELOPE(-9.5, -8.0, 52.2,
   51.4)"^^geosparql:wktLiteral` — `geosparql:` bindet auf dieselbe
   Namensraum-IRI (`http://www.opengis.net/ont/geosparql#`) wie das
   Profil-übliche `geo:`; Prefix-Name unterschiedlich, Property
   identisch. Kein echter Unterschied, nur eine andere Abkürzung dafür.
6. `dct:creator <https://orcid.org/0000-0002-3246-3531>` — ORCID direkt,
   keine generierte URN, obwohl der Code bei fehlendem ORCID weiterhin
   korrekt auf `urn:fdo-squirrel:person/<hash>` zurückfällt.

Vermutlich zwischen dem Registry-Befund (2026-09-04) und diesem PRIMER
(ab 2026-09-08) in Ad-hoc-Arbeit gefixt, nie in einem `fdo-squirrel`-
eigenen PRIMER dokumentiert, weil es bis S0 keinen gab. `repository-code`
korrigiert wie in A4 beschrieben.

**Nicht hier erledigt, gehört in einen `fdo-squirrel-registry`-Chat:**
Punkt 8 dort als erledigt markieren — das ist ein anderes Repo, hier
nicht angefasst.

## S13 — Zwei Bugs aus S6/S7 gegen echte Pakete

**Ziel:** die beiden beim echten Durchlaufen von CIIC 81 und Freshford
gefundenen Bugs beheben.

**Uploads:** Repo-Bundle (A5).

**Substanz:**

1. **Fehlendes Escaping in mehreren `fdo_rdf.py`-Literalen.** `dct:title`,
   `dct:description`, `dct:hasVersion`, `dct:identifier`, `dct:created`,
   `dct:issued`, `dct:modified`, Keyword-Literale, Creator-Namen und die
   Distribution-Felder (`dcat:mediaType`/`fdo:path`/`fdo:role`) wurden
   direkt per f-String in die Turtle-Ausgabe eingebettet, ohne durch
   `_ttl_lit()`/`_ttl_escape()` zu laufen — obwohl diese Hilfsfunktionen
   längst existieren und an anderen Stellen korrekt benutzt werden.
2. **`id` in `MD.cff` ist nicht immer eine echte IRI.** `fdo-3d-packager`
   trägt für unveröffentlichte Pakete einen Platzhaltersatz statt einer
   DOI ein (`'TODO: id not set (pending Zenodo DOI, see PRIMER.md A4)'`)
   — `fdo-squirrel` wickelte den unvalidiert in `<...>`, was einen
   IRIREF mit Leerzeichen ergibt.

**Abnahme:** ein Testpaket mit einer mehrzeiligen `description` und ein
Paket ohne echte `id` erzeugen beide gültiges, mit `rdflib` strikt
parsbares Turtle.

### Erledigt 2026-09-09

**Bug 1 (Escaping) — gefunden, weil Freshfords `description` echte
Newlines enthält** (aus Sketchfab importierter Fließtext: "...floating
in there for a while.\n\nWikidata: Q121840779\n\n..."). Vor dem Fix
scheiterte `rdflib.Graph().parse()` an dieser Datei komplett
(`BadSyntax: newline found in string literal`) — kein Kantenfall,
sondern ein Totalausfall für jedes Paket mit mehrzeiligem Freitext.
Alle neun betroffenen Stellen auf `_ttl_lit()` umgestellt.

**Bug 2 (id-Validierung) — Flos Entscheidung: Fallback-URN aus dem
Slug.** Neue, exportierte Funktion `resolve_dataset_id(cw_id,
package_source)` in `fdo/fdo_rdf.py`: prüft mit der schon vorhandenen
`_is_iri()`, ob `cw_id` wie eine IRI aussieht; wenn nicht, baut
`urn:fdo-squirrel:unpublished/<sanitierter-Dateiname-ohne-Endung>`.
**Wichtig, erst beim zweiten Anlauf richtig:** die Citation-Crosswalk-
Engine bekommt ihr Subject in `main.py` (`engine.crosswalk(cff, cw.id)`)
**vor** dem Aufruf von `crosswalk_to_rdf_turtle()` — ein Fix nur in
`fdo_rdf.py` hätte zwei verschiedene Subjects im selben File erzeugt
(Kern-Dataset-Block unter der neuen URN, alle Citation-Crosswalk-Tripel
weiter unter dem alten Platzhaltertext). Deshalb `main.py`: `cw.id`
direkt nach `md_cff_to_crosswalk()` per `dataclasses.replace()` einmal
aufgelöst (`CrosswalkRecord` ist `frozen=True`), bevor die Engine läuft
— `crosswalk_to_rdf_turtle()` behält seinen eigenen Aufruf von
`resolve_dataset_id()` als Sicherheitsnetz für Aufrufer, die direkt mit
dieser Funktion arbeiten, ist dann aber ein No-op (`urn:` matcht schon
`_is_iri()`).

**Verifiziert, gegen beide echten Pakete:**
- `rdflib.Graph().parse(..., format='turtle')` läuft für beide sauber
  durch, 0 Warnungen (vorher: Freshford Totalausfall, dazu 38 `rdflib`-
  Warnungen "does not look like a valid URI" nach dem ersten,
  unvollständigen Fix-Versuch).
- `grep -c "TODO: id not set"` → 0 in der Freshford-Ausgabe.
- Determinismus (S4) hält weiter: zwei Läufe gegen dasselbe
  Freshford-Paket, `fdo-metadata.ttl` bytegleich.
- CIIC 81 unverändert: `_is_iri()` erkennt die echte DOI korrekt, kein
  Fallback ausgelöst.

**Nicht hier erledigt:** `fdo-3d-packager`s Pin auf `fdo-squirrel`
bumpen (A4) — anderes Repo, eigener Chat.

## S14 — Generator-Version im Output festhalten

**Ziel:** irgendwo im FDOx-Output soll stehen, welche `fdo-squirrel`-
Version es erzeugt hat — Flos Anstoß, im Hinblick auf den geplanten
Release und `fdo-3d-packager`s künftigen Pin darauf.

**Uploads:** Repo-Bundle (A5).

**Substanz (nach Diskussion mit Flo, drei Optionen abgewogen):**
- Nur RDF (PROV-O) + bestehende Reports — verworfen, Flo wollte eine
  eigene, direkt lesbare Datei zusätzlich.
- Eine vollständige Toolchain-Datei (mit Blender-/Nexus-Versionen) hier
  in `fdo-squirrel` — verworfen: das kann `fdo-squirrel` gar nicht
  wissen, das lief alles upstream in `fdo-3d-packager`, in einem anderen
  Prozess.
- **Gewählt:** eigene `FDOx.yaml` mit `fdo-squirrel`s eigenen Angaben,
  gespeist aus `rdf_modelling_report.json` statt die Provenance-Trackerei
  zu duplizieren, plus strukturelle (nicht verifizierte) Vermutung, welches
  Upstream-Tool das *Eingabe*-Paket gebaut hat — begründet: eine
  Kombination aus 3DHOP-Viewer + Nexus-Dateien baut in dieser Familie
  nur `fdo-3d-packager` so.

**Abnahme:** `FDOx.yaml` liegt im Output, enthält `fdo-squirrel`s Name +
Version; `fdo-metadata.ttl` trägt `prov:wasGeneratedBy` auf einen
`prov:SoftwareAgent`-Knoten mit derselben Version; beides bleibt
deterministisch (kein Zeitstempel).

### Erledigt 2026-09-09

**`fdo/fdo_rdf.py`:** neue, öffentliche Funktion `fdo_squirrel_version()`
— liest `importlib.metadata.version("fdo-squirrel")` (der Normalfall bei
einer `pip`-Installation, z. B. bei `fdo-3d-packager`s Pin), fällt bei
`PackageNotFoundError` auf ein direktes Auslesen von `pyproject.toml`s
`version`-Zeile zurück (Entwicklungs-Checkout ohne Installation unter
diesem Namen — kein `tomllib`, das bräuchte Python ≥3.11, `requires-
python` hier ist `>=3.9`). Neuer `prov:`-Prefix; Kern-Dataset bekommt
`prov:wasGeneratedBy <urn:fdo-squirrel:activity/build>`; neue,
zeitstempelfreie `prov:Activity`/`prov:SoftwareAgent`-Knoten mit
`schema:softwareVersion`. `generator`-Feld im JSON-Report ergänzt.

**Dabei noch einen aus S13 übrig gebliebenen Escaping-Fund behoben:**
der Publisher-Name (`schema:name` am `schema:Organization`-Knoten) war
beim Durchgehen der S13-Liste übersehen worden — jetzt auch auf
`_ttl_lit()` umgestellt.

**`fdo_manifest.py` (neu):** schreibt `FDOx.yaml`. Liest
`rdf_modelling_report.json` zurück (statt die Provenance-Trackerei zu
duplizieren) für die Liste der gesehenen Quellen; öffnet das Original-
ZIP (`info["package_local_path"]`) und prüft strukturell auf
`viewer/index.html` + `viewer/js/nexus.js` + `.nxs`/`.nxz`-Dateien —
trifft das zu, `likely_built_by: fdo-3d-packager` mit
`likely_built_by_confidence: heuristic` und einer Begründung, sonst
`null`/`unknown`. In `pyproject.toml`s `py-modules` ergänzt (sonst fehlt
es im echten `pip install`).

**`main.py`:** ruft `write_fdox_yaml()` nach dem HTML-Report auf,
`FDOx.yaml` landet in `generated_files` und wird wie jede andere
generierte Datei zu einer `dcat:Distribution` und Teil des fertigen
Bundles.

**Verifiziert:**
- Gegen beide echten Pakete (Freshford, CIIC 81): `FDOx.yaml` valides
  YAML (`yaml.safe_load`), `generator.version` korrekt `0.3.1`.
- Erkennungs-Heuristik anfangs mit einem eigenen Testpaket ohne
  `viewer/` geprüft (versehentlich, aus der S6/S7-Extraktion) —
  `likely_built_by: null`, korrekt, da das Testpaket die Struktur
  nicht hatte. Mit `viewer/` erneut gebaut: `likely_built_by:
  fdo-3d-packager` korrekt erkannt.
- `rdflib` parst beide TTLs weiterhin sauber (jetzt 204/194 Tripel,
  vorher 187/177 — die neuen `prov:`-Tripel kommen dazu).
- Determinismus (S4) hält für alle drei Ausgabedateien inkl.
  `FDOx.yaml` **und** das fertige Bundle-ZIP selbst — zwei Läufe,
  `fdo-metadata.ttl`, `FDOx.yaml`, `<slug>-fdo-bundle.zip` alle
  bytegleich.

**README.md** um `FDOx.yaml` im Output-Abschnitt ergänzt, damit sie
nicht sofort wieder veraltet ist (S9 hat genau das kritisiert).

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
