# Vyhľadávanie textu

Stav: implementované (text z QtPdf, bez ohľadu na veľkosť písmen a diakritiku; skeny bez textu dostanú vysvetlenie)  
Priorita: P2  
Odhad náročnosti: Stredná (relatívny, nie časový záväzok)

## Prínos

Nájsť potrebnú stranu pred extrakciou alebo odstránením.

## Navrhované ovládanie

Ctrl+F, výsledky s číslom strany, ďalší/predchádzajúci výsledok a otvorenie detailu.

## Prvá verzia

Vyhľadávanie v PDF s existujúcou textovou vrstvou bez OCR.

## Technické súvislosti

Preveriť vyhľadávacie možnosti QtPdf a mapovanie na rozpracované poradie. Indexovať priebežne, s možnosťou zrušenia. Sken bez textu má dostať zrozumiteľnú informáciu.

Konkrétne API, správanie knižníc a potrebu nových závislostí overiť pri implementácii. Zachovať oddelenie jadra od GUI, slovenské hlášky a podporu Windows/macOS.

## Kritériá dokončenia a overenie

- Výsledky sedia po otočení, vymazaní a presune.
- UI nezamŕza na veľkom dokumente.
- otestovať diakritiku a dokument bez textovej vrstvy.
- Nové operácie majú primerané testy jadra a kritických interakcií GUI; existujúce testy prejdú.
- Neúspešné uloženie nepoškodí existujúci cieľ; prepísanie a neuložené zmeny sa riešia v súlade s aplikáciou.

## Otázky pred implementáciou

- Potvrdiť rozsah prvej verzie a detaily ovládania uvedené ako návrh.
- Overiť správanie na poškodených, šifrovaných a veľkých vstupoch podľa rozsahu funkcie.
- Pri úprave digitálne podpísaných PDF zohľadniť platnosť podpisov; nezaručovať ich zachovanie bez overenia.
