# Uloženie rozpracovanej práce

Stav: implementované (ručné uloženie a otvorenie; zdroje overené odtlačkom SHA-256; bez automatickej obnovy)  
Priorita: P3  
Odhad náročnosti: Stredná až vyššia (relatívny, nie časový záväzok)

## Prínos

Pokračovať neskôr v skladaní dokumentu bez opakovania všetkých krokov.

## Navrhované ovládanie

Uložiť projekt so zdrojmi, poradím a úpravami; pri chýbajúcom zdroji ponúknuť jeho nové umiestnenie.

## Prvá verzia

Ručné uloženie a načítanie projektu bez automatickej obnovy.

## Technické súvislosti

Verzovaný dátový formát s validáciou; rozlíšiť projekt a výsledné PDF. Odkazy na súbory nie sú vložené kópie; zmenu zdroja detegovať a neaplikovať staré indexy potichu. Neukladať heslá.

Konkrétne API, správanie knižníc a potrebu nových závislostí overiť pri implementácii. Zachovať oddelenie jadra od GUI, slovenské hlášky a podporu Windows/macOS.

## Kritériá dokončenia a overenie

- Obnovený projekt reprodukuje poradie a rotácie.
- chýbajúce či zmenené vstupy majú jasné riešenie.
- neplatný projekt nespôsobí stratu otvorenej práce.
- Nové operácie majú primerané testy jadra a kritických interakcií GUI; existujúce testy prejdú.
- Neúspešné uloženie nepoškodí existujúci cieľ; prepísanie a neuložené zmeny sa riešia v súlade s aplikáciou.

## Otázky pred implementáciou

- Potvrdiť rozsah prvej verzie a detaily ovládania uvedené ako návrh.
- Overiť správanie na poškodených, šifrovaných a veľkých vstupoch podľa rozsahu funkcie.
- Pri úprave digitálne podpísaných PDF zohľadniť platnosť podpisov; nezaručovať ich zachovanie bez overenia.
