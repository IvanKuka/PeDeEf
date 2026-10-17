# Zapamätanie nastavení a rýchle voľby

Stav: implementované (okno, posledný priečinok, otvorenie výsledku alebo jeho priečinka, veľkosť náhľadov, svetlá/tmavá/systémová téma a predvolený formát obrázkov pri zlučovaní; nastavenia sú vpravo hore)  
Priorita: P1  
Odhad náročnosti: Menšia (relatívny, nie časový záväzok)

## Prínos

Znížiť počet opakovaných kliknutí pri každodennej práci.

## Navrhované ovládanie

Zapamätať veľkosť okna, veľkosť náhľadov a posledný výstupný priečinok; ponúknuť otvorenie výsledku alebo jeho priečinka.

## Prvá verzia

Nastavenia okna a výstupného priečinka plus otvorenie výsledku po úspešnom uložení.

## Technické súvislosti

Využiť existujúce Qt nastavenia, ak sa v projekte používajú, inak zvážiť QSettings. Uložené cesty validovať; históriu dokumentov pridať len s možnosťou vymazania.

Konkrétne API, správanie knižníc a potrebu nových závislostí overiť pri implementácii. Zachovať oddelenie jadra od GUI, slovenské hlášky a podporu Windows/macOS.

## Kritériá dokončenia a overenie

- Nedostupný priečinok má bezpečnú náhradu.
- okno sa neobnoví mimo obrazovky.
- chybné nastavenia nezabránia štartu.
- heslá sa neukladajú.
- Nové operácie majú primerané testy jadra a kritických interakcií GUI; existujúce testy prejdú.
- Neúspešné uloženie nepoškodí existujúci cieľ; prepísanie a neuložené zmeny sa riešia v súlade s aplikáciou.

## Otázky pred implementáciou

- Potvrdiť rozsah prvej verzie a detaily ovládania uvedené ako návrh.
- Overiť správanie na poškodených, šifrovaných a veľkých vstupoch podľa rozsahu funkcie.
- Pri úprave digitálne podpísaných PDF zohľadniť platnosť podpisov; nezaručovať ich zachovanie bez overenia.
