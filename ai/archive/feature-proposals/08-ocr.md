# OCR a prehľadávateľné skeny

Stav: prvá verzia dokončená pre Windows (pribalený Tesseract, slk/ces/eng/deu, výber strán, bezpečné rušenie a zápis); na macOS systémový Tesseract z Homebrew, bez pribalenia. Automatická orientácia a oprava sklonu zostávajú ďalšou etapou.  
Priorita: P3  
Odhad náročnosti: Vyššia (relatívny, nie časový záväzok)

## Prínos

Vyhľadávať a kopírovať text aj v naskenovaných PDF.

## Navrhované ovládanie

**Upraviť strany → Kontrola a ochrana → Rozpoznať text (OCR)**. Vybrať jazyk, zadať rozsah strán v aktuálnom poradí (napr. `1-3, 5`) a výstup. Predvolia sa označené strany, prázdny rozsah znamená všetky. Strany s existujúcim textom sa vždy preskočia. Spracovanie sa dá zrušiť aj počas rozpoznávania jednej strany.

## Prvá verzia

Lokálne OCR pre obrazové strany s jedným zvoleným jazykom. Pôvodný obraz, rozmery, orez, otočenie a umiestnenie anotácií zostávajú zachované. Textová vrstva sa prispôsobí presným rozmerom výslednej strany. Úprava jednej duplikovanej strany sa neprenesie do ostatných kópií.

Obrázky sa prenášajú pamäťou a rúrami, nezapisujú sa na disk. Rozpoznávanie používa 300 dpi s limitom 6 000 pixelov na stranu a približne 25 miliónov pixelov celkovo. Obmedzenie rozlíšenia OCR nemení kvalitu pôvodného obrazu vo výsledku.

Pri chybe, zrušení alebo ak sa nerozpozná vôbec žiadny text, sa nič neuloží a existujúci cieľ zostane neporušený. Prázdne strany v zmiešanom výsledku zostávajú bez textovej vrstvy. Ochrana výstupu heslom a nastavené vlastnosti dokumentu používajú bežné pravidlá aplikácie. OCR nezachová platnosť digitálnych podpisov; rozhranie podpísaný vstup označuje.

## Technické súvislosti

Windows build pribaľuje Tesseract, načítavané DLL, `pdf.ttf` a modely tessdata_fast 4.1.0 s pripnutými SHA-256. Pri opakovanom builde sa použijú len overené modely. Zostavená aplikácia musí úspešne rozpoznať skúšobný text vlastným pribaleným Tesseractom; systémový fallback tento test nesplní.

Na macOS treba `brew install tesseract tesseract-lang`. CI inštaluje aj jazykové dáta pre integračné testy; macOS build nie je lokálne overený na Windows.

Podklady: [Tesseract CLI](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html), [kvalita skenov](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html), [Homebrew Tesseract](https://formulae.brew.sh/formula/tesseract).

## Kritériá dokončenia a overenie

- Text možno vyhľadať a skopírovať.
- pôvodný vzhľad zostáva zachovaný.
- zrušenie je bezpečné.
- testovať diakritiku, zmiešané strany a zlé skeny. Presnosť OCR nie je garantovaná.
- Nové operácie majú primerané testy jadra a kritických interakcií GUI; existujúce testy prejdú.
- Neúspešné uloženie nepoškodí existujúci cieľ; prepísanie a neuložené zmeny sa riešia v súlade s aplikáciou.

## Overené prípady a obmedzenia

- Reálne rozpoznávanie slovenčiny, češtiny, angličtiny a nemčiny vrátane diakritiky; zmiešané strany a rozsahy.
- Otočenie, orez s posunutým začiatkom súradníc, zarovnanie textu, šifrovanie a vlastnosti dokumentu.
- Kliknutie na zrušenie v Qt, ukončenie procesu so zablokovaným vstupom, poškodený/prázdny výsledok a ochrana existujúceho cieľa.
- Strany otočené nabok treba najprv ručne otočiť v náhľade. Čiastočná textová vrstva sa považuje za existujúci text a neprepisuje sa. Rozpoznávanie neobnovuje formátovanie do Wordu ani editovateľné tabuľky.
