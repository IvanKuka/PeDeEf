# Späť a Znova

Stav: implementované (všetky úpravy strán; história sa po uložení začína odznova)  
Priorita: P1  
Odhad náročnosti: Stredná (relatívny, nie časový záväzok)

## Prínos

Vrátiť jednotlivý omyl bez zahodenia všetkých úprav.

## Navrhované ovládanie

Ctrl+Z a Ctrl+Y, na macOS systémové skratky; pomenované akcie v ponuke; podpora mazania, otáčania a neskôr presúvania či vkladania.

## Prvá verzia

História otočení a odstránení v jednom otvorenom dokumente.

## Technické súvislosti

Zvážiť Qt undo stack. Ukladať stav úprav alebo príkazy, nie celé renderované obrázky. Zohľadniť bod posledného uloženia a existujúce has_unsaved_changes().

Konkrétne API, správanie knižníc a potrebu nových závislostí overiť pri implementácii. Zachovať oddelenie jadra od GUI, slovenské hlášky a podporu Windows/macOS.

## Kritériá dokončenia a overenie

- Po novej úprave sa vetva Znova vymaže.
- návrat k uloženému stavu odstráni indikáciu zmien.
- otvorenie iného dokumentu vyčistí históriu.
- Nové operácie majú primerané testy jadra a kritických interakcií GUI; existujúce testy prejdú.
- Neúspešné uloženie nepoškodí existujúci cieľ; prepísanie a neuložené zmeny sa riešia v súlade s aplikáciou.

## Otázky pred implementáciou

- Potvrdiť rozsah prvej verzie a detaily ovládania uvedené ako návrh.
- Overiť správanie na poškodených, šifrovaných a veľkých vstupoch podľa rozsahu funkcie.
- Pri úprave digitálne podpísaných PDF zohľadniť platnosť podpisov; nezaručovať ich zachovanie bez overenia.
