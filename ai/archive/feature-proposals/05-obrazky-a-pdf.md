# Obrázky do PDF a PDF do obrázkov

Stav: implementované (obrázky v záložke Zlúčiť PDF, export vybraných strán do PNG; JPG export zatiaľ nie)  
Priorita: P2  
Odhad náročnosti: Stredná (relatívny, nie časový záväzok)

## Prínos

Vytvoriť dokument z fotiek alebo exportovať strany pre ďalšie použitie.

## Navrhované ovládanie

Import JPG/PNG, poradie, A4 alebo rozmer obrázka, orientácia a okraje; export vybraných strán do PNG/JPG s nastavením rozlíšenia.

## Prvá verzia

Dva jednoduché postupy: obrázky do PDF a vybrané PDF strany do PNG.

## Technické súvislosti

Pre export preveriť existujúci QtPdf; pri importe preveriť možnosti Qt a existujúcich závislostí pred pridaním knižnice. Rešpektovať EXIF orientáciu, priehľadnosť a limity rozmerov.

Konkrétne API, správanie knižníc a potrebu nových závislostí overiť pri implementácii. Zachovať oddelenie jadra od GUI, slovenské hlášky a podporu Windows/macOS.

## Kritériá dokončenia a overenie

- Správny pomer strán bez deformácie.
- fotky majú správnu orientáciu.
- názvy výstupov sa nekolidujú potichu.
- chybný obrázok má jasnú hlášku.
- Nové operácie majú primerané testy jadra a kritických interakcií GUI; existujúce testy prejdú.
- Neúspešné uloženie nepoškodí existujúci cieľ; prepísanie a neuložené zmeny sa riešia v súlade s aplikáciou.

## Otázky pred implementáciou

- Potvrdiť rozsah prvej verzie a detaily ovládania uvedené ako návrh.
- Overiť správanie na poškodených, šifrovaných a veľkých vstupoch podľa rozsahu funkcie.
- Pri úprave digitálne podpísaných PDF zohľadniť platnosť podpisov; nezaručovať ich zachovanie bez overenia.
