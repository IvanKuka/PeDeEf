# PDF Nástroje

Desktopová aplikácia pre Windows a macOS na zlučovanie, rozdeľovanie, otáčanie a mazanie strán v PDF súboroch. Postavená na Pythone, PySide6 (Qt) a pypdf. Nepoužíva žiadne knižnice Adobe.

## Funkcie

**Zlúčiť PDF**
- pridanie súborov tlačidlom alebo pretiahnutím myšou
- náhľad prvej strany a počet strán každého súboru
- zmena poradia (pretiahnutím alebo tlačidlami), odstránenie zo zoznamu
- výber strán z každého súboru, napr. `1-3, 5, 8-` (prázdne = všetky, `5-3` = opačné poradie)
- voliteľne záložka (osnova) pre každý zlúčený súbor podľa jeho názvu; pôvodné záložky zlučovaných súborov sa neprenášajú, lebo strany sa kopírujú jednotlivo a ich ciele by pri výbere strán nesedeli
- aj obrázky JPG/PNG (napr. fotky dokladov): každý je jedna strana, A4 s okrajmi alebo bez okrajov podľa obrázka; orientácia fotiek z mobilu sa rešpektuje

**Upraviť strany** (jeden dokument)
- náhľady všetkých strán (vykresľujú sa postupne, okno nezamŕza ani pri veľkých súboroch)
- veľký náhľad strany (dvojklik, Enter alebo „Náhľad“): listovanie šípkami, zoom (Ctrl + koliesko, Ctrl +/−, Ctrl+0 prispôsobí oknu), posun ťahaním myšou, Esc zatvorí; zobrazuje strany s rozpracovaným poradím aj otočením
- otočenie vybraných strán doľava/doprava (Ctrl+L / Ctrl+R, na Macu ⌘L / ⌘R)
- odstránenie vybraných strán (tlačidlo alebo kláves Delete), strany sa potom prečíslujú
- presúvanie strán myšou (aj viacerých naraz): pretiahnite vybrané strany na nové miesto, farebná čiara ukazuje, kam sa vložia
- duplikovanie vybraných strán (tlačidlo alebo Ctrl+D / ⌘D); kópie sa dajú otáčať aj odstraňovať nezávisle
- vloženie strán z iného PDF pred alebo za vybrané strany (rozsah strán napr. `1-3, 5`, prázdne = všetky)
- Späť / Znova (Ctrl+Z / Ctrl+Y, na Macu ⌘Z / ⇧⌘Z) pre všetky úpravy strán; tlačidlo ukazuje, ktorá úprava sa vráti. História sa vyčistí otvorením iného súboru aj uložením
- „Zahodiť zmeny“ vráti všetky úpravy strán (otočenie, poradie, odstránenie, duplikáty, vloženie), „Zavrieť“ zavrie omylom otvorený súbor
- zmeny sa do súboru zapíšu až pri „Uložiť ako…“; extrakcia vybraných strán do nového PDF
- „Spojiť predné a zadné skeny…“ poskladá obojstranný dokument zo skenera bez duplexu: používateľ vyberie PDF predných a PDF zadných strán (aj v opačnom poradí), aplikácia ich strieda na P1, Z1, P2, Z2…; sama typ strany nerozpoznáva
- „Číslovanie a pečiatka…“: čísla strán (napr. `{n} / {total}`, od zvoleného čísla), vlastný text ako „KÓPIA“ alebo dnešný dátum; poloha, veľkosť, rozsah strán a náhľad; použije sa v rozpracovanom dokumente so slovenskou diakritikou
- „Vpísať text…“: text kamkoľvek na stranu, napr. do naskenovaného tlačiva bez formulárových polí. Kliknutím do náhľadu sa začne nový text, ťahaním alebo šípkami sa presúva; viac textov na viacerých stranách, vlastná veľkosť písma a riadky. Text sa vpíše natrvalo do strany so slovenskou diakritikou
- „Vyplniť formulár…“: vyplnenie interaktívnych formulárových polí PDF (text, zaškrtávacie políčka, prepínače, výberové zoznamy) s náhľadom strany; kliknutím na pole v náhľade prejdete na jeho vyplnenie. Zmenené polia sa vpíšu natrvalo do strán (formulár sa „zlúči“), takže vyzerajú rovnako v každom programe aj s diakritikou; nezmenené polia zostanú. Polia len na čítanie, podpisové a heslové polia sa nevypĺňajú
- „Vložiť obrázok podpisu…“: naskenovaný podpis alebo pečiatka (PNG s priehľadnosťou alebo JPG) na jednu stranu; umiestnenie myšou alebo šípkami a veľkosť s náhľadom. Ide len o obrázok (grafický podpis), nie o elektronický ani digitálny podpis; obrázok sa nikam neukladá. Ak je dokument digitálne podpísaný, dialóg upozorní, že v novom súbore podpis platný nebude
- **Vložiť a podpis → Digitálne podpísať P12/PFX**: výber certifikátu a hesla, kontrola údajov a platnosti, voliteľný dôvod a uloženie podpísanej kópie. Ide o kryptografický podpis bez viditeľného poľa; PDF prehliadače ho zobrazia v paneli podpisov. Podpis obrázkom zostáva samostatnou akciou. Ďalší podpis sa k nezmenenému PDF pridáva inkrementálne.
- **Vložiť a podpis → Overiť podpisy**: offline kontrola integrity, pokrytia a následných zmien uloženého súboru. Dôvera certifikátu, zneplatnenie a časová pečiatka sa neoverujú. Heslá ani kľúče sa neukladajú; zdroj sa pri podpisovaní neprepisuje.
- export vybraných strán do PNG (72, 150 alebo 300 dpi), s rozpracovaným otočením
- hľadanie textu (Ctrl+F, na Macu ⌘F) bez ohľadu na veľkosť písmen a diakritiku; Enter/Shift+Enter prechádza výskyty, „Vybrať všetky nájdené“ pripraví strany napr. na extrakciu; skeny bez textovej vrstvy treba najprv rozpoznať (OCR)
- **Kontrola a ochrana → Rozpoznať text (OCR)**: vyberte jazyk (slovenčina, čeština, angličtina, nemčina) a rozsah strán, napr. `1-3, 5`; predvolia sa označené strany, prázdny rozsah znamená celý dokument. Rozpoznávajú sa len strany bez textu, takže existujúci text sa nezdvojí. Skeny dostanú neviditeľnú vrstvu na vyhľadávanie a kopírovanie; pôvodný obraz, rozmery, orez a otočenie zostávajú zachované. Spracovanie možno zrušiť aj počas práce na strane a bez zmeny zdroja či existujúceho cieľa. Pri chybe alebo ak sa nerozpozná vôbec žiadny text, sa výsledok neuloží. Veľmi veľké strany majú obmedzené rozlíšenie kvôli pamäti. Tesseract je na Windows pribalený; na macOS treba zatiaľ `brew install tesseract tesseract-lang`. Presnosť nie je zaručená: sken otočený nabok treba najprv otočiť, pri zlých alebo zošikmených skenoch môže byť text nepresný.
- „Prázdne strany…“ nájde strany, ktoré vyzerajú prázdne (aj skeny s prachom či presvitaním), ukáže ich na kontrolu a po potvrdení odstráni; dá sa to vrátiť cez Späť
- pracuje sa iba s PDF; projektové súbory nie sú súčasťou používateľského rozhrania
- „Porovnať s iným PDF…“ porovná vzhľad strán na rovnakých pozíciách (aj s rozpracovanými úpravami), zmeny vyznačí červenou a F3/Shift+F3 medzi nimi prechádza; vložená strana posunie ďalšie, preto sa ukážu ako rozdielne
- „Zmenšiť veľkosť…“: bezstratová optimalizácia, alebo aj zmenšenie obrázkov JPEG (≈150 dpi na e-mail, ≈100 dpi najmenší súbor); použije sa ako rozpracovaná úprava, text nikdy nerasterizuje
- „Orezať okraje…“ pre vybrané strany v mm s náhľadom; funguje aj na otočených stranách a dá sa vrátiť cez Späť. Orez obsah len skryje (zostáva v súbore), na odstránenie citlivých údajov nestačí – na to slúži začiernenie
- „Trvalo začierniť údaje…“: oblasti označené myšou sa natrvalo odstránia. Strana s označením sa vykreslí do obrázka (150 alebo 300 dpi), oblasti sa v ňom začiernia a strana sa nahradí len týmto obrázkom – pôvodný text, obrázky, skryté vrstvy, komentáre ani formulárové polia tej strany v súbore nezostanú; text na nej sa potom nedá označiť ani vyhľadať a súbor je väčší (rádovo stovky kB na stranu). Pred uložením sa výsledok skontroluje (žiadny text ani komentáre na začiernených stranách), inak sa neuloží. Ostatné strany sa nemenia, údaj na nich treba označiť tiež
- „Vlastnosti dokumentu…“ ukáže metadáta pôvodného súboru (autor, program, dátumy, XMP) a nastaví názov, autora, predmet a kľúčové slová uloženého súboru; bez toho uložené súbory pôvodné metadáta neobsahujú
- vynechané strany (pri extrakcii, rozdelení, odstránení) v uloženom súbore naozaj nie sú – ani skryto cez odkazy alebo formulárové polia zo zostávajúcich strán
- všetky príkazy úpravy strán sú v jednom vodorovnom páse bez vnútorných záložiek. Sekcie **Dokument**, **Strany**, **Vložiť a podpis**, **Nástroje a ochrana** majú názov nad tlačidlami a oddeľujú ich zvislé čiary. Pás možno posúvať kolieskom, trackpadom alebo spodným posuvníkom. Textové tlačidlá **Späť**, **Znova**, **Uložiť ako…** a **Uložiť** zostávajú pevne pri názve dokumentu spolu s tlačidlom **Zavrieť dokument**. Pred prepísaním aktuálneho PDF sa zobrazí potvrdenie s cestou k súboru; Zrušiť zachová pôvodné PDF aj rozpracované úpravy
- začiernenie, OCR, číslovanie, vpísaný text, vyplnený formulár, obrázok podpisu a kompresia majú tlačidlo **OK**: dajú sa kombinovať a vracať cez Späť/Znova bez otázky na uloženie po každej akcii. **Uložiť / Ctrl+S** zapíše všetky úpravy do aktuálneho PDF a zachová jeho heslo. **Uložiť ako… / Ctrl+Shift+S** vytvorí kópiu so zvoleným názvom. Pri chybe zápisu zostane pôvodné PDF aj rozpracovaná práca zachovaná. Pracovné kópie sú dočasné, šifrované náhodným heslom v pamäti a odstránia sa po uložení alebo zavretí. Začiernenie má veľký náhľad so zoomom a posúvaním
- rozdelenie: každá strana zvlášť, po N stranách alebo podľa rozsahov (`1-3, 4-6, 7-` = 3 súbory)

**Dávkové úpravy** (veľa súborov naraz)
- súbory alebo celé priečinky (podpriečinky len na požiadanie), pretiahnutím alebo tlačidlami
- otočenie zvolených strán vo všetkých súboroch; súbor, ktorý danú stranu nemá, sa preskočí
- výsledky do zvoleného priečinka, zdroje sa nemenia a nič sa neprepíše (rovnaký názov dostane „(2)“)
- spracovanie na pozadí s priebehom a zrušením; pri každom súbore je výsledok alebo dôvod chyby

Vpravo hore sú **Nastavenia**: svetlá, tmavá alebo systémová téma, tri veľkosti náhľadov a predvolený formát obrázkov pri zlučovaní. Zmeny sa použijú ihneď po uložení a zapamätajú sa. Formát obrázkov možno pri zlučovaní zvoliť aj pred ich pridaním. Aplikácia si pamätá aj veľkosť a polohu okna a posledný použitý priečinok. Po uložení ponúkne otvoriť výsledok alebo jeho priečinok.

Nové verzie: pri spustení sa aplikácia na pozadí opýta GitHubu na číslo najnovšej verzie. Ak je novšia, vpravo hore sa zobrazí tlačidlo. Na Windows je to **Aktualizovať na verziu …**: aplikácia stiahne inštalátor z GitHub releasu, overí jeho kontrolný súčet (`SHA256SUMS.txt`, ktorý pridáva workflow), nainštaluje ho bez otázok a znova sa spustí; neuložené úpravy pred zatvorením potvrdzuje ako vždy. Na macOS (aplikácia nie je podpísaná u Apple) a pri spustení zo zdrojov tlačidlo **Nová verzia … – stiahnuť** otvorí stránku s inštalátormi. Neodosielajú sa žiadne dokumenty ani údaje o používateľovi; bez internetu sa nestane nič. Kontrolu možno vypnúť v Nastaveniach.

Otvoriť sa dajú aj PDF s obmedzením tlače/úprav. Pri PDF chránenom heslom sa aplikácia spýta na heslo (pri nesprávnom znova); heslo si pamätá len počas behu, nikam ho neukladá. Dávkové úpravy sa na heslá nepýtajú a nepoužívajú ani heslo z inej záložky – chránené súbory označia ako nespracované. „Kontrola a ochrana → Uložiť s heslom…“ chráni výsledok heslom (AES-256); ak bol pôvodný dokument chránený, aplikácia sa pri ukladaní spýta, či má heslo dostať aj nový súbor.

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

Pred zabalením build zostavenú aplikáciu skúšobne spustí (`--smoke-test`). Na Windows overí aj skutočné rozpoznanie textu pribaleným Tesseractom (`--ocr-smoke-test`), takže chýbajúce DLL alebo jazykové dáta zastavia build. Už stiahnuté jazykové dáta sa pri opakovanom builde použijú len pri zhode SHA-256.

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
| `pdftool/history.py` | história Späť/Znova (snímky stavu), bez závislosti na GUI |
| `pdftool/operations.py` | zlúčenie, extrakcia, rozdelenie, rotácia, poradie strán z viacerých súborov (pypdf), bez závislosti na GUI |
| `pdftool/page_ranges.py` | parsovanie rozsahov strán `1-3, 5, 8-` |
| `pdftool/plural.py` | slovenské tvary („1 strana / 3 strany / 5 strán“) |
| `pdftool/gui/merge_tab.py` | záložka *Zlúčiť PDF* |
| `pdftool/gui/pages_tab.py`, `page_grid.py`, `page_preview.py`, `split_dialog.py`, `insert_dialog.py`, `interleave_dialog.py` | záložka *Upraviť strany*, mriežka strán s presúvaním myšou, veľký náhľad, dialógy rozdelenia, vloženia a preloženia skenov |
| `pdftool/gui/images.py`, `export_dialog.py` | obrázky do PDF a strany do PNG (len Qt, bez ďalšej knižnice) |
| `pdftool/stamps.py`, `gui/stamp_layer.py`, `gui/stamp_dialog.py` | číslovanie a pečiatky: texty (jadro), vrstva kreslená cez Qt a jej zlúčenie s PDF (`operations.apply_overlay`), spoločný náhľad |
| `pdftool/gui/text_boxes.py`, `text_box_dialog.py` | vpísaný text: poloha (podiel viditeľnej strany), kreslenie do tej istej vrstvy a dialóg s klikaním a presúvaním v náhľade |
| `pdftool/forms.py`, `gui/form_filling.py`, `gui/form_dialog.py` | formuláre: čítanie polí z widgetov strán a ich poloha na viditeľnej strane (jadro), vpísanie hodnôt a odstránenie vyplnených polí, dialóg |
| `pdftool/gui/zoomed_page.py` | náhľad strany so zoomom a kreslením navrchu, spoločný pre dialógy, ktoré umiestňujú obsah na stranu |
| `pdftool/gui/signature.py`, `signature_dialog.py` | obrázok podpisu: umiestnenie (podiel viditeľnej strany), kreslenie do tej istej vrstvy a dialóg s presúvaním v náhľade |
| `pdftool/ocr.py`, `gui/recognition.py`, `gui/ocr_dialog.py` | OCR: vyhľadanie a spustenie Tesseractu, zlúčenie textovej vrstvy (jadro), vykreslenie strán s priebehom a dialóg |
| `pdftool/gui/redaction.py`, `redaction_dialog.py` | trvalé začiernenie: strany s oblasťami nahradené obrázkom (QtPdf), kontrola výsledku pred uložením a dialóg na označenie oblastí |
| `pdftool/batch.py`, `gui/batch_tab.py` | dávkové spracovanie: pravidlá názvov a výsledky (jadro), záložka s vláknom na pozadí |
| `pdftool/gui/blank_pages.py`, `blank_pages_dialog.py` | odhad prázdnych strán podľa vykresleného obsahu a dialóg na potvrdenie |
| `pdftool/text_search.py`, `gui/search_bar.py` | hľadanie textu: porovnávanie bez diakritiky (jadro) a panel hľadania |
| `pdftool/gui/passwords.py` | dialógy hesla na otvorenie a na ochranu nového súboru; heslá drží `operations` len v pamäti |
| `pdftool/project.py` | rozpracované projekty: verzovaný formát, kontrola zdrojov odtlačkom SHA-256 |
| `pdftool/gui/compare.py`, `compare_dialog.py` | vizuálne porovnanie dvoch dokumentov po stranách |
| `pdftool/gui/compress_dialog.py` | profily zmenšenia; bezstratové kroky a výmena obrázkov sú v `operations.write_optimized`, prekódovanie JPEG v `gui/images.py` |
| `pdftool/gui/crop_dialog.py` | orez okrajov s náhľadom; prepočet na súradnice PDF je v `operations` |
| `pdftool/gui/properties_dialog.py` | vlastnosti dokumentu (metadáta) – kontrola pôvodných a nastavenie ukladaných |
| `pdftool/signing.py`, `gui/digital_signature_dialog.py` | podpisovanie P12/PFX a offline kontrola integrity cez pyHanko |
| `pdftool/pdf_resources.py` | odstránenie nepoužitých zdrojov strán vrátane skenov v zdieľaných zdrojoch |
| `pdftool/updates.py`, `gui/update_check.py` | nové verzie: porovnanie s najnovším releasom a overenie kontrolného súčtu (jadro), dopyt, stiahnutie a spustenie inštalátora cez QtNetwork |
| `pdftool/gui/settings.py`, `gui/settings_dialog.py` | nastavenia témy, náhľadov, obrázkov, okna a priečinka cez QSettings |
| `pdftool/gui/thumbnails.py` | náhľady strán (QtPdf / PDFium) |
| `pdftool/gui/widgets.py`, `style.py` | spoločné widgety, dialógy a vzhľad |
| `tests/` | testy jadra aj GUI (GUI beží v Qt režime `offscreen`) |
| `build.py`, `.github/workflows/build.yml` | build pre Windows/macOS, lokálne aj na GitHube |
| `installer/pdf_nastroje.iss` | skript Windows inštalátora (Inno Setup) |

## Licencie závislostí

PySide6 (LGPLv3), pypdf (BSD), cryptography (Apache 2.0 / BSD), pyHanko (MIT). pyHanko poskytuje inkrementálny zápis a kontrolu PDF podpisov. PyMuPDF zámerne nie je použitý, pretože je pod licenciou AGPL.

OCR: Tesseract (Apache 2.0) s jazykovými dátami tessdata_fast (Apache 2.0) sa na Windows pribaľuje ako samostatný program v priečinku `tesseract`; aplikácia ho len spúšťa. Medzi jeho knižnicami sú aj JBIG-KIT (GPL-2.0-or-later) a GNU libiconv (LGPL-2.1-or-later); zoznam všetkých súčastí a ich licencií je v [installer/tesseract-notices.txt](installer/tesseract-notices.txt), ktorý sa pribaľuje ako `tesseract/NOTICES.txt`. Build vyžaduje nainštalovaný Tesseract (`winget install --id UB-Mannheim.TesseractOCR --exact`), jazykové dáta si stiahne a overí podľa SHA-256.
