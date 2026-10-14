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

Hotovú aplikáciu stačí stiahnuť a rozbaliť. Python ani nič iné inštalovať netreba.

### 1. Stiahnutie

**Z Releases** (ak je vydaná verzia):
1. Otvorte <https://github.com/IvanKuka/PeDeEf/releases>.
2. Pri najnovšej verzii stiahnite `PDF-Nastroje-windows.zip` alebo `PDF-Nastroje-macos.zip`.

**Z posledného buildu** (vyžaduje prihlásenie na GitHub):
1. Otvorte <https://github.com/IvanKuka/PeDeEf/actions> a kliknite na najnovší úspešný beh **Build** (zelená fajka).
2. Dole v sekcii **Artifacts** stiahnite `PDF-Nastroje-windows.zip` alebo `PDF-Nastroje-macos.zip`.

### 2a. Windows (Windows 10 a 11, 64-bit)

1. Na stiahnutý `PDF-Nastroje-windows.zip` kliknite pravým tlačidlom → **Extrahovať všetko…** a zvoľte cieľ, napr. `C:\Programy`.
2. Vznikne priečinok `PDF Nastroje`. **Celý priečinok musí zostať pohromade.** Samotný `PDF Nastroje.exe` bez podpriečinka `_internal` nefunguje.
3. Spustite `PDF Nastroje\PDF Nastroje.exe`.
4. Pri prvom spustení môže Windows zobraziť modré okno **„Systém Windows ochránil váš počítač“** (aplikácia nie je podpísaná certifikátom). Kliknite na **Ďalšie informácie** → **Spustiť aj tak**.
5. Odporúčané: pravým tlačidlom na `PDF Nastroje.exe` → **Zobraziť ďalšie možnosti** → **Odoslať do** → **Pracovná plocha (vytvoriť odkaz)**.

Odinštalovanie: stačí zmazať priečinok `PDF Nastroje`.

### 2b. macOS (Mac s čipom Apple M1 a novším)

1. Dvakrát kliknite na `PDF-Nastroje-macos.zip`; vznikne `PDF Nastroje.app`.
2. Presuňte `PDF Nastroje.app` do priečinka **Aplikácie**.
3. Spustite ju. Keďže nie je podpísaná certifikátom Apple, macOS ju zablokuje hláškou, že nemôže overiť vývojára. Zvoľte **Hotovo** (nie „Presunúť do koša“).
4. Otvorte **Nastavenia systému → Súkromie a bezpečnosť**, zrolujte nadol a pri hláške o „PDF Nastroje“ kliknite na **Aj tak otvoriť**, potvrďte heslom.
5. Pri ďalších spusteniach sa už aplikácia otvára normálne.

Ak sa krok 4 nezobrazí, alebo macOS hlási, že je aplikácia „poškodená“, spustite v aplikácii **Terminál**:

```sh
xattr -dr com.apple.quarantine "/Applications/PDF Nastroje.app"
```

Macy s procesorom Intel nie sú podporované (build je len pre Apple Silicon).

Odinštalovanie: presuňte `PDF Nastroje.app` z Aplikácií do koša.

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

- **Windows:** `dist\PDF Nastroje\` (priečinok s `.exe`) a `dist\PDF-Nastroje-windows.zip`
- **macOS:** `dist/PDF Nastroje.app` a `dist/PDF-Nastroje-macos.zip`

### 5. Automatický build a vydanie novej verzie (GitHub Actions)

Workflow [.github/workflows/build.yml](.github/workflows/build.yml) pri každom pushnutí na `main` zostaví Windows aj Mac verziu (výsledky v **Actions → Artifacts**, uchovávajú sa 90 dní).

Vydanie verzie, ktorú si používatelia stiahnu z **Releases**:

```sh
git tag v1.0.0
git push origin v1.0.0
```

Po dobehnutí buildu sa automaticky vytvorí Release so zipmi pre obe platformy.

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

## Licencie závislostí

PySide6 (LGPLv3), pypdf (BSD), cryptography (Apache 2.0 / BSD). PyMuPDF zámerne nie je použitý, pretože je pod licenciou AGPL.
