# Vlastnosti dokumentu a odstránenie metadát

Stav: implementované (uložené súbory pôvodné metadáta ani XMP neobsahujú; zapíšu sa len zadané vlastnosti)  
Priorita: P2  
Odhad náročnosti: Menšia až stredná (relatívny, nie časový záväzok)

## Prínos

Skontrolovať autora a ďalšie údaje pred odoslaním dokumentu.

## Navrhované ovládanie

Zobraziť a upraviť názov, autora, predmet a kľúčové slová; voliteľne odstrániť podporované metadáta.

## Prvá verzia

Editor bežných metadát s jasným rozsahom čistenia.

## Technické súvislosti

Preveriť klasické PDF metadata aj XMP. Neoznačovať výsledok za úplne anonymný: prílohy, komentáre či obsah môžu stále obsahovať osobné údaje.

Konkrétne API, správanie knižníc a potrebu nových závislostí overiť pri implementácii. Zachovať oddelenie jadra od GUI, slovenské hlášky a podporu Windows/macOS.

## Kritériá dokončenia a overenie

- Overiť opätovným otvorením výstupu.
- diakritika funguje.
- UI presne uvádza, ktoré údaje odstraňuje a ktoré nekontroluje.
- Nové operácie majú primerané testy jadra a kritických interakcií GUI; existujúce testy prejdú.
- Neúspešné uloženie nepoškodí existujúci cieľ; prepísanie a neuložené zmeny sa riešia v súlade s aplikáciou.

## Otázky pred implementáciou

- Potvrdiť rozsah prvej verzie a detaily ovládania uvedené ako návrh.
- Overiť správanie na poškodených, šifrovaných a veľkých vstupoch podľa rozsahu funkcie.
- Pri úprave digitálne podpísaných PDF zohľadniť platnosť podpisov; nezaručovať ich zachovanie bez overenia.
