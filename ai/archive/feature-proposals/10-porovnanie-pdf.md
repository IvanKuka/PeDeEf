# Porovnanie dvoch PDF

Stav: prvá verzia implementovaná (vizuálne porovnanie na rovnakých pozíciách pri 72 dpi; zmena jedného znaku sa zachytí; párovanie posunutých strán a synchronizovaný zoom zatiaľ nie)  
Priorita: P3  
Odhad náročnosti: Vyššia (relatívny, nie časový záväzok)

## Prínos

Nájsť zmeny medzi dvoma verziami dokumentu.

## Navrhované ovládanie

Dokumenty vedľa seba, synchronizovaný zoom, prechod na rozdiely a označenie pridaných či chýbajúcich strán.

## Prvá verzia

Vizuálne porovnanie strán na rovnakých pozíciách; obmedzenie výslovne uviesť v rozhraní.

## Technické súvislosti

Použiť konzistentné renderovanie. Posun strán po vložení jednej strany potrebuje samostatné párovanie; vizuálne rozdiely nie sú dôkazom významovej zmeny. Textové porovnanie odložiť.

Konkrétne API, správanie knižníc a potrebu nových závislostí overiť pri implementácii. Zachovať oddelenie jadra od GUI, slovenské hlášky a podporu Windows/macOS.

## Kritériá dokončenia a overenie

- Zhodné dokumenty nemajú falošné zásadné rozdiely.
- odlišné rozmery a počty sú zrozumiteľné.
- rozdiely sa dajú prechádzať klávesnicou.
- Nové operácie majú primerané testy jadra a kritických interakcií GUI; existujúce testy prejdú.
- Neúspešné uloženie nepoškodí existujúci cieľ; prepísanie a neuložené zmeny sa riešia v súlade s aplikáciou.

## Otázky pred implementáciou

- Potvrdiť rozsah prvej verzie a detaily ovládania uvedené ako návrh.
- Overiť správanie na poškodených, šifrovaných a veľkých vstupoch podľa rozsahu funkcie.
- Pri úprave digitálne podpísaných PDF zohľadniť platnosť podpisov; nezaručovať ich zachovanie bez overenia.
