# Prekladanie predných a zadných skenov

Stav: implementované (zadných strán rovnako alebo o jednu menej; výsledok sa otvorí ako upraviteľný dokument)  
Priorita: P2  
Odhad náročnosti: Menšia až stredná (relatívny, nie časový záväzok)

## Prínos

Poskladať obojstranný dokument zo skenera bez automatického duplexu.

## Navrhované ovládanie

Dva vstupy: predné a zadné strany; voľba obráteného poradia zadných strán; náhľad výsledného poradia.

## Prvá verzia

Prekladanie A1, B1, A2, B2 s voliteľným obrátením B.

## Technické súvislosti

Poradie zostaviť v jadre cez PageSelection. Rozdielne počty strán musia mať explicitné pravidlo, napríklad povolenie jednej poslednej prednej strany navyše.

Konkrétne API, správanie knižníc a potrebu nových závislostí overiť pri implementácii. Zachovať oddelenie jadra od GUI, slovenské hlášky a podporu Windows/macOS.

## Kritériá dokončenia a overenie

- Overiť rovnaký počet, jednu prednú navyše, opačné poradie a neplatné počty.
- zdrojové súbory zostanú zachované.
- Nové operácie majú primerané testy jadra a kritických interakcií GUI; existujúce testy prejdú.
- Neúspešné uloženie nepoškodí existujúci cieľ; prepísanie a neuložené zmeny sa riešia v súlade s aplikáciou.

## Otázky pred implementáciou

- Potvrdiť rozsah prvej verzie a detaily ovládania uvedené ako návrh.
- Overiť správanie na poškodených, šifrovaných a veľkých vstupoch podľa rozsahu funkcie.
- Pri úprave digitálne podpísaných PDF zohľadniť platnosť podpisov; nezaručovať ich zachovanie bez overenia.
