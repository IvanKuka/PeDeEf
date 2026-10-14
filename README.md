# PDF Nástroje

Desktopová aplikácia pre Windows a macOS na zlučovanie, rozdeľovanie, otáčanie a mazanie strán v PDF súboroch. Postavená na Pythone, PySide6 (Qt) a pypdf. Nepoužíva žiadne knižnice Adobe.

## Funkcie

**Zlúčiť PDF**
- pridanie súborov tlačidlom alebo pretiahnutím myšou
- náhľad prvej strany a počet strán každého súboru
- zmena poradia (pretiahnutím alebo tlačidlami), odstránenie zo zoznamu
- výber strán z každého súboru, napr. `1-3, 5, 8-` (prázdne = všetky, `5-3` = opačné poradie)

**Upraviť strany** (jeden dokument)
- náhľady všetkých strán (vykresľujú sa postupne, okno nezamŕza ani pri veľkých súboroch)
- otočenie vybraných strán doľava/doprava (Ctrl+L / Ctrl+R, na Macu ⌘L / ⌘R)
- odstránenie vybraných strán (tlačidlo alebo kláves Delete), strany sa potom prečíslujú
- „Zahodiť zmeny“ vráti otočenia aj odstránené strany, „Zavrieť“ zavrie omylom otvorený súbor
- zmeny sa do súboru zapíšu až pri „Uložiť ako…“; extrakcia vybraných strán do nového PDF
- rozdelenie: každá strana zvlášť, po N stranách alebo podľa rozsahov (`1-3, 4-6, 7-` = 3 súbory)

Otvoriť sa dajú aj PDF s obmedzením tlače/úprav. PDF chránené heslom na otvorenie aplikácia odmietne so zrozumiteľnou hláškou.

---

## Inštalácia pre používateľov

Stačí stiahnuť inštalátor pre váš systém. Python ani nič iné inštalovať netreba.

### 1. Stiahnutie

1. Otvorte <https://github.com/IvanKuka/PeDeEf/releases>.
2. Pri najnovšej verzii v časti **Assets** stiahnite:
   - **Windows:** `PDF-Nastroje-Setup.exe`
   - **Mac s čipom Apple (M1, M2, M3, M4…):** `PDF-Nastroje-macos-apple-silicon.dmg`
   - **Mac s procesorom Intel:** `PDF-Nastroje-macos-intel.dmg`

   Aký čip má váš Mac zistíte cez ponuku Apple (logo jablka vľavo hore) → **O tomto Macu**: riadok **Čip** (napr. „Apple M2“) znamená Apple, riadok **Procesor** s textom „Intel“ znamená Intel.

Zipy (`PDF-Nastroje-windows.zip`, `PDF-Nastroje-macos-….zip`) sú alternatíva bez inštalácie (pozri nižšie).

Najnovší, ešte nevydaný build: <https://github.com/IvanKuka/PeDeEf/actions> → najnovší úspešný beh **Build** (zelená fajka) → sekcia **Artifacts** (vyžaduje prihlásenie na GitHub).

### 2a. Windows (Windows 10 a 11, 64-bit)

1. Spustite stiahnutý `PDF-Nastroje-Setup.exe`.
2. Windows môže zobraziť modré okno **„Systém Windows ochránil váš počítač“** (inštalátor nie je podpísaný certifikátom). Kliknite na **Ďalšie informácie** → **Spustiť aj tak**.
3. Prejdite sprievodcom (**Ďalej**). Predvolene sa aplikácia inštaluje len pre vás a nepotrebuje administrátorské práva. Voliteľne vytvorí zástupcu na ploche.
4. Po skopírovaní súborov nechajte zaškrtnuté **Spustiť PDF Nástroje** a kliknite na **Dokončiť**.

Aplikáciu potom nájdete v ponuke **Štart** (a na ploche, ak ste to zvolili). Novšiu verziu nainštalujete rovnako, priamo cez starú; odinštalovať ju predtým netreba.

Odinštalovanie: **Nastavenia → Aplikácie → Nainštalované aplikácie → PDF Nástroje → Odinštalovať**.

<details>
<summary>Bez inštalácie (zip)</summary>

1. Na `PDF-Nastroje-windows.zip` kliknite pravým tlačidlom → **Extrahovať všetko…** a zvoľte cieľ.
2. **Počkajte, kým okno s priebehom rozbaľovania úplne zmizne** (môže to trvať niekoľko minút, Windows Defender kontroluje každý súbor). Ak aplikáciu spustíte skôr, zobrazí chybu *Failed to load Python DLL*.
3. Spustite `PDF Nastroje\PDF Nastroje.exe`. Celý priečinok musí zostať pohromade; samotný `.exe` bez podpriečinka `_internal` nefunguje.

Odinštalovanie: zmažte priečinok `PDF Nastroje`.
</details>

### 2b. macOS (macOS 14 Sonoma alebo novší, čip Apple aj Intel)

1. Dvakrát kliknite na stiahnutý `.dmg` súbor pre váš Mac. Otvorí sa okno s aplikáciou **PDF Nastroje** a priečinkom **Applications**.
2. Pretiahnite **PDF Nastroje** na priečinok **Applications** a počkajte, kým Finder dokončí kopírovanie.
3. Zatvorte okno a v bočnom paneli Findera kliknite na tlačidlo vysunutia (⏏) pri **PDF Nástroje**.
4. Spustite aplikáciu z priečinka **Aplikácie** (alebo cez Launchpad). Keďže nie je podpísaná certifikátom Apple, macOS ju zablokuje hláškou, že nemôže overiť vývojára. Zvoľte **Hotovo** (nie „Presunúť do koša“).
5. Otvorte **Nastavenia systému → Súkromie a bezpečnosť**, zrolujte nadol a pri hláške o „PDF Nastroje“ kliknite na **Aj tak otvoriť**, potvrďte heslom.
6. Pri ďalších spusteniach sa už aplikácia otvára normálne.

Ak sa krok 5 nezobrazí, alebo macOS hlási, že je aplikácia „poškodená“, spustite v aplikácii **Terminál**:

```sh
xattr -dr com.apple.quarantine "/Applications/PDF Nastroje.app"
```

Novšiu verziu nainštalujete rovnako; pri kopírovaní potvrďte **Nahradiť**.

Ak macOS hlási, že aplikáciu nemožno otvoriť, lebo nie je podporovaná na tomto Macu, stiahli ste verziu pre iný typ čipu.

Aplikácia vyžaduje **macOS 14 Sonoma alebo novší** (požiadavka knižnice Qt). Staršie Macy s Intelom, na ktoré macOS 14 nejde nainštalovať (približne modely pred rokom 2018), nie sú podporované.

Odinštalovanie: presuňte `PDF Nastroje` z Aplikácií do koša.

<details>
<summary>Bez obrazu disku (zip)</summary>

Dvakrát kliknite na zip pre váš Mac (`PDF-Nastroje-macos-apple-silicon.zip` alebo `PDF-Nastroje-macos-intel.zip`), vzniknutú `PDF Nastroje.app` presuňte do **Aplikácií** a pokračujte krokom 4 vyššie.
</details>

---

## Inštalácia pre vývojárov (spustenie zo zdrojového kódu)

### 1. Predpoklady

- **Python 3.11 alebo novší** (testované s 3.14)
  - Windows: stiahnite z <https://www.python.org/downloads/> a pri inštalácii zaškrtnite **Add python.exe to PATH**. Inštalátor pridá aj príkaz `py`.
  - macOS: stiahnite z <https://www.python.org/downloads/> alebo `brew install python`.
- **Git**: <https://git-scm.com/downloads> (na Macu sa ponúkne sám pri prvom použití príkazu `git`).

### 2. Stiahnutie kódu a inštalácia závislostí

Windows (PowerShell):

```powershell
git clone https://github.com/IvanKuka/PeDeEf.git
cd PeDeEf
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

macOS (Terminál):

```sh
git clone https://github.com/IvanKuka/PeDeEf.git
cd PeDeEf
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-dev.txt
```

### 3. Spustenie a testy

Na macOS nahraďte `.\.venv\Scripts\python.exe` za `.venv/bin/python`.

```powershell
.\.venv\Scripts\python.exe -m pdftool              # spustí aplikáciu
.\.venv\Scripts\python.exe -m pdftool a.pdf b.pdf  # súbory sa pridajú do zoznamu na zlúčenie
.\.venv\Scripts\python.exe -m pytest               # testy
```

### 4. Zostavenie aplikácie (build)

```powershell
.\.venv\Scripts\python.exe build.py
```

Skript spustí testy a zostaví aplikáciu **pre systém, na ktorom beží** (Windows verziu treba zostaviť na Windows, Mac verziu na Macu):

- **Windows:** `dist\PDF-Nastroje-Setup.exe` (inštalátor), `dist\PDF-Nastroje-windows.zip` a priečinok `dist\PDF Nastroje\`. Na inštalátor treba [Inno Setup 6](https://jrsoftware.org/isinfo.php): `winget install --id JRSoftware.InnoSetup --scope user`.
- **macOS:** `dist/PDF-Nastroje-macos-<čip>.dmg` (obraz disku), `dist/PDF-Nastroje-macos-<čip>.zip` a `dist/PDF Nastroje.app`, kde `<čip>` je `apple-silicon` alebo `intel` podľa Macu, na ktorom build beží (verzia pre Intel sa dá zostaviť len na Intel Macu).

Pred zabalením build zostavenú aplikáciu raz skúšobne spustí (`--smoke-test`); ak sa nespustí, build zlyhá.

### 5. Automatický build a vydanie novej verzie (GitHub Actions)

Workflow [.github/workflows/build.yml](.github/workflows/build.yml) pri každom pushnutí na `main` zostaví Windows verziu a obe Mac verzie (Apple Silicon a Intel) vrátane inštalátorov (výsledky v **Actions → Artifacts**, uchovávajú sa 90 dní).

Vydanie verzie, ktorú si používatelia stiahnu z **Releases**:

```sh
git tag v1.0.0
git push origin v1.0.0
```

Po dobehnutí buildu sa automaticky vytvorí Release s inštalátormi a zipmi pre obe platformy.

---

## Štruktúra

| Súbor | Účel |
|---|---|
| `pdftool/operations.py` | zlúčenie, extrakcia, rozdelenie, rotácia (pypdf), bez závislosti na GUI |
| `pdftool/page_ranges.py` | parsovanie rozsahov strán `1-3, 5, 8-` |
| `pdftool/plural.py` | slovenské tvary („1 strana / 3 strany / 5 strán“) |
| `pdftool/gui/merge_tab.py` | záložka *Zlúčiť PDF* |
| `pdftool/gui/pages_tab.py`, `split_dialog.py` | záložka *Upraviť strany* a dialóg rozdelenia |
| `pdftool/gui/thumbnails.py` | náhľady strán (QtPdf / PDFium) |
| `pdftool/gui/widgets.py`, `style.py` | spoločné widgety, dialógy a vzhľad |
| `tests/` | testy jadra aj GUI (GUI beží v Qt režime `offscreen`) |
| `build.py`, `.github/workflows/build.yml` | build pre Windows/macOS, lokálne aj na GitHube |
| `installer/pdf_nastroje.iss` | skript Windows inštalátora (Inno Setup) |

## Licencie závislostí

PySide6 (LGPLv3), pypdf (BSD), cryptography (Apache 2.0 / BSD). PyMuPDF zámerne nie je použitý, pretože je pod licenciou AGPL.
