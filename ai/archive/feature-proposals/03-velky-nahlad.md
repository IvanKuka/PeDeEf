# Veľký náhľad strany

Stav: implementované (`PageView` v page_preview.py je pripravený aj pre orez, pečiatky a podpis)  
Priorita: P1  
Odhad náročnosti: Menšia až stredná (relatívny, nie časový záväzok)

## Prínos

Overiť obsah strany pred úpravou bez otvárania iného programu.

## Navrhované ovládanie

Dvojklik otvorí detail; zoom, prispôsobenie oknu, posun a navigácia medzi stranami; detail rešpektuje rozpracované otočenie.

## Prvá verzia

Detail jednej strany so zoomom a navigáciou.

## Technické súvislosti

Nadviazať na QtPdf v thumbnails.py, ale renderovať pre veľkosť detailu. Nezväčšovať iba malý thumbnail. Obmedziť pamäť a overiť správanie pri rýchlej navigácii.

Konkrétne API, správanie knižníc a potrebu nových závislostí overiť pri implementácii. Zachovať oddelenie jadra od GUI, slovenské hlášky a podporu Windows/macOS.

## Kritériá dokončenia a overenie

- Detail ukazuje správnu stranu aj po úpravách.
- funguje klávesnica a Escape.
- veľké strany nezablokujú aplikáciu na neprimeraný čas.
- Nové operácie majú primerané testy jadra a kritických interakcií GUI; existujúce testy prejdú.
- Neúspešné uloženie nepoškodí existujúci cieľ; prepísanie a neuložené zmeny sa riešia v súlade s aplikáciou.

## Otázky pred implementáciou

- Potvrdiť rozsah prvej verzie a detaily ovládania uvedené ako návrh.
- Overiť správanie na poškodených, šifrovaných a veľkých vstupoch podľa rozsahu funkcie.
- Pri úprave digitálne podpísaných PDF zohľadniť platnosť podpisov; nezaručovať ich zachovanie bez overenia.
