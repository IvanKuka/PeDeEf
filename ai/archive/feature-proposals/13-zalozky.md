# Záložky a obsah dokumentu

Stav: prvá verzia implementovaná (záložky podľa názvov zlúčených súborov; pôvodné záložky sa neprenášajú – zdokumentované v README; ručné úpravy vnorených záložiek zatiaľ nie)  
Priorita: P2  
Odhad náročnosti: Stredná až vyššia (relatívny, nie časový záväzok)

## Prínos

Ľahšie sa orientovať v dlhom zlúčenom dokumente.

## Navrhované ovládanie

Pri zlúčení vytvoriť záložku podľa názvu každého vstupu; neskôr ručne pridať a upraviť vnorené záložky.

## Prvá verzia

Voliteľné záložky na začiatkoch zlúčených súborov.

## Technické súvislosti

Súčasný zápis pridáva jednotlivé strany; preveriť zachovanie existujúcich záložiek a odkazov. Ciele mapovať podľa skutočného výstupného poradia a výberu strán.

Konkrétne API, správanie knižníc a potrebu nových závislostí overiť pri implementácii. Zachovať oddelenie jadra od GUI, slovenské hlášky a podporu Windows/macOS.

## Kritériá dokončenia a overenie

- Záložky smerujú na správne strany pri rozsahoch aj opačnom poradí.
- slovenské názvy fungujú.
- správanie pôvodných záložiek je zdokumentované.
- Nové operácie majú primerané testy jadra a kritických interakcií GUI; existujúce testy prejdú.
- Neúspešné uloženie nepoškodí existujúci cieľ; prepísanie a neuložené zmeny sa riešia v súlade s aplikáciou.

## Otázky pred implementáciou

- Potvrdiť rozsah prvej verzie a detaily ovládania uvedené ako návrh.
- Overiť správanie na poškodených, šifrovaných a veľkých vstupoch podľa rozsahu funkcie.
- Pri úprave digitálne podpísaných PDF zohľadniť platnosť podpisov; nezaručovať ich zachovanie bez overenia.
