# Orezanie okrajov strán

Stav: implementované (okraje v mm, uložené ako podiel strany; mení crop box; otočené strany overené vykreslením)  
Priorita: P2  
Odhad náročnosti: Stredná (relatívny, nie časový záväzok)

## Prínos

Zlepšiť zobrazenie dokumentov s veľkými alebo nerovnakými okrajmi.

## Navrhované ovládanie

Obdĺžnik v náhľade, číselné okraje, použitie na výber alebo všetky strany a obnova pôvodného orezu.

## Prvá verzia

Ručný orez s náhľadom pre vybrané strany.

## Technické súvislosti

Zohľadniť PDF page boxes, jednotky a rotáciu. Orez upravuje viditeľnú oblasť; obsah mimo nej nemusí byť odstránený. Neprezentovať ako anonymizáciu.

Konkrétne API, správanie knižníc a potrebu nových závislostí overiť pri implementácii. Zachovať oddelenie jadra od GUI, slovenské hlášky a podporu Windows/macOS.

## Kritériá dokončenia a overenie

- Správny výsledok na otočených a rôzne veľkých stranách.
- nemožno uložiť neplatný nulový orez.
- používateľ vidí upozornenie na zachovaný skrytý obsah.
- Nové operácie majú primerané testy jadra a kritických interakcií GUI; existujúce testy prejdú.
- Neúspešné uloženie nepoškodí existujúci cieľ; prepísanie a neuložené zmeny sa riešia v súlade s aplikáciou.

## Otázky pred implementáciou

- Potvrdiť rozsah prvej verzie a detaily ovládania uvedené ako návrh.
- Overiť správanie na poškodených, šifrovaných a veľkých vstupoch podľa rozsahu funkcie.
- Pri úprave digitálne podpísaných PDF zohľadniť platnosť podpisov; nezaručovať ich zachovanie bez overenia.
