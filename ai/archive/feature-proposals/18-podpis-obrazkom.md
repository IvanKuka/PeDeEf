# Vloženie obrázka podpisu

Stav: prvá verzia implementovaná (jeden obrázok PNG/JPG na jednej strane; priehľadnosť a umiestnenie na otočenej strane overené vykreslením; upozornenie pri digitálne podpísanom dokumente; obrázok sa neukladá)  
Priorita: P3  
Odhad náročnosti: Stredná až vyššia (relatívny, nie časový záväzok)

## Prínos

Umiestniť vlastný naskenovaný podpis alebo pečiatku na dokument.

## Navrhované ovládanie

Vybrať PNG, umiestniť ho v detaile, zmeniť veľkosť a uložiť nové PDF.

## Prvá verzia

Jeden obrázok na jednej vybranej strane s náhľadom.

## Technické súvislosti

Ide o grafický podpis, nie certifikovaný digitálny podpis. Správne previesť súradnice pri zoome a rotácii; obrázok podpisu trvalo neukladať bez výslovnej voľby používateľa.

Konkrétne API, správanie knižníc a potrebu nových závislostí overiť pri implementácii. Zachovať oddelenie jadra od GUI, slovenské hlášky a podporu Windows/macOS.

## Kritériá dokončenia a overenie

- Umiestnenie výstupu zodpovedá náhľadu.
- priehľadnosť funguje.
- rozhranie jednoznačne pomenúva grafický charakter podpisu.
- Nové operácie majú primerané testy jadra a kritických interakcií GUI; existujúce testy prejdú.
- Neúspešné uloženie nepoškodí existujúci cieľ; prepísanie a neuložené zmeny sa riešia v súlade s aplikáciou.

## Otázky pred implementáciou

- Potvrdiť rozsah prvej verzie a detaily ovládania uvedené ako návrh.
- Overiť správanie na poškodených, šifrovaných a veľkých vstupoch podľa rozsahu funkcie.
- Pri úprave digitálne podpísaných PDF zohľadniť platnosť podpisov; nezaručovať ich zachovanie bez overenia.
