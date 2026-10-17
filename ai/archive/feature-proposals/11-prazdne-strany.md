# Hľadanie prázdnych strán

Stav: implementované (podiel tmavých pixelov pri 72 dpi; tri úrovne citlivosti; vždy s ručným potvrdením)  
Priorita: P2  
Odhad náročnosti: Stredná (relatívny, nie časový záväzok)

## Prínos

Rýchlo vyčistiť skeny s prázdnymi zadnými stranami.

## Navrhované ovládanie

Vyhľadať kandidátov, nastaviť citlivosť, zobraziť náhľady a až potom potvrdiť odstránenie.

## Prvá verzia

Detekcia podľa vykresleného obsahu s ručným potvrdením.

## Technické súvislosti

Neprítomnosť extrahovaného textu neznamená prázdnu stranu. Počítať so šumom, drobným číslovaním a presvitaním; detekciu prezentovať ako odhad.

Konkrétne API, správanie knižníc a potrebu nových závislostí overiť pri implementácii. Zachovať oddelenie jadra od GUI, slovenské hlášky a podporu Windows/macOS.

## Kritériá dokončenia a overenie

- Slabý text a malé poznámky sa zahrnú do skúšobných vzoriek.
- nič sa neodstráni automaticky.
- odstránenie možno vrátiť cez Späť, keď je dostupné.
- Nové operácie majú primerané testy jadra a kritických interakcií GUI; existujúce testy prejdú.
- Neúspešné uloženie nepoškodí existujúci cieľ; prepísanie a neuložené zmeny sa riešia v súlade s aplikáciou.

## Otázky pred implementáciou

- Potvrdiť rozsah prvej verzie a detaily ovládania uvedené ako návrh.
- Overiť správanie na poškodených, šifrovaných a veľkých vstupoch podľa rozsahu funkcie.
- Pri úprave digitálne podpísaných PDF zohľadniť platnosť podpisov; nezaručovať ich zachovanie bez overenia.
