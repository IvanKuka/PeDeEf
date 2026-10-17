# Presúvanie, duplikovanie a vkladanie strán

Stav: implementované (presúvanie myšou, duplikovanie, vloženie z ďalšieho PDF)  
Priorita: P1  
Odhad náročnosti: Stredná (relatívny, nie časový záväzok)

## Prínos

Opraviť poradie dokumentu priamo v mriežke náhľadov.

## Navrhované ovládanie

Presúvanie jednej aj viacerých strán myšou; duplikovanie výberu; vloženie vybraných strán z ďalšieho PDF pred alebo za aktuálnu stranu.

## Prvá verzia

Najprv presúvanie v jednom dokumente, následne duplikovanie a vloženie z ďalšieho súboru.

## Technické súvislosti

PagesTab dnes eviduje strany podľa indexu zdroja. Pre duplikáty a viac zdrojov bude potrebná samostatná identita každého výskytu strany. Zachovať PageSelection a spoločný zápis v operations.py, kde to dáva zmysel.

Konkrétne API, správanie knižníc a potrebu nových závislostí overiť pri implementácii. Zachovať oddelenie jadra od GUI, slovenské hlášky a podporu Windows/macOS.

## Kritériá dokončenia a overenie

- Presunutie viacerých strán zachová ich vzájomné poradie.
- uložené PDF zodpovedá náhľadom.
- duplikáty sa dajú nezávisle otáčať.
- vloženie zlyhaného súboru nemení rozpracovaný dokument.
- Nové operácie majú primerané testy jadra a kritických interakcií GUI; existujúce testy prejdú.
- Neúspešné uloženie nepoškodí existujúci cieľ; prepísanie a neuložené zmeny sa riešia v súlade s aplikáciou.

## Otázky pred implementáciou

- Potvrdiť rozsah prvej verzie a detaily ovládania uvedené ako návrh.
- Overiť správanie na poškodených, šifrovaných a veľkých vstupoch podľa rozsahu funkcie.
- Pri úprave digitálne podpísaných PDF zohľadniť platnosť podpisov; nezaručovať ich zachovanie bez overenia.
