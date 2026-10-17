# Dávkové spracovanie

Stav: implementované (otočenie strán; súbor bez danej strany sa preskočí; ďalšie operácie sa pridávajú cez `batch.Operation`)  
Priorita: P2  
Odhad náročnosti: Stredná až vyššia (relatívny, nie časový záväzok)

## Prínos

Vykonať rovnakú operáciu nad desiatkami súborov.

## Navrhované ovládanie

Zoznam súborov alebo priečinok; výber jednej operácie; samostatný výstupný priečinok; priebeh, zrušenie a výsledok pre každý súbor.

## Prvá verzia

Dávkové otočenie vybraných strán s pravidlom pre súbory, ktoré danú stranu nemajú.

## Technické súvislosti

Znovu použiť operácie jadra. GUI nesmie vykonávať dlhú dávku blokujúco. Pri zrušení ponechať dokončené výstupy a jasne vypísať stav; rekurziu priečinkov zapínať výslovne.

Konkrétne API, správanie knižníc a potrebu nových závislostí overiť pri implementácii. Zachovať oddelenie jadra od GUI, slovenské hlášky a podporu Windows/macOS.

## Kritériá dokončenia a overenie

- Chyba jedného súboru má viditeľný výsledok.
- kolízie názvov majú jasné pravidlo.
- zrušenie nevytvorí poškodený aktuálny výstup.
- žiadne neúmyselné prepísanie zdrojov.
- Nové operácie majú primerané testy jadra a kritických interakcií GUI; existujúce testy prejdú.
- Neúspešné uloženie nepoškodí existujúci cieľ; prepísanie a neuložené zmeny sa riešia v súlade s aplikáciou.

## Otázky pred implementáciou

- Potvrdiť rozsah prvej verzie a detaily ovládania uvedené ako návrh.
- Overiť správanie na poškodených, šifrovaných a veľkých vstupoch podľa rozsahu funkcie.
- Pri úprave digitálne podpísaných PDF zohľadniť platnosť podpisov; nezaručovať ich zachovanie bez overenia.
