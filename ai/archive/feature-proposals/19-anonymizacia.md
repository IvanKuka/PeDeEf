# Trvalé začiernenie citlivých údajov

Stav: prvá verzia implementovaná (strany s oblasťami sa nahradia obrázkom z QtPdf/PDFium – bez novej závislosti; odstránenie overené dvoma nezávislými extraktormi textu, pypdf a PDFium, aj pri šifrovanom výstupe; výsledok sa pred uložením kontroluje; opravený únik vynechaných strán cez odkazy a formulárové polia pri všetkých uloženiach; strana sa označuje v náhľade bez zoomu a bez ovládania klávesnicou)  
Priorita: P3  
Odhad náročnosti: Vysoká (relatívny, nie časový záväzok)

## Prínos

Bezpečne odstrániť vybrané údaje pred zdieľaním PDF.

## Navrhované ovládanie

Výber oblastí, náhľad, nezvratné aplikovanie do nového súboru a kontrola výsledku.

## Prvá verzia

Najprv technické overenie spoľahlivého enginu a bezpečnostných testov; až potom používateľská funkcia.

## Technické súvislosti

Čierny obdĺžnik nad textom nestačí. Riešiť text, obrázky, OCR vrstvy, formuláre, komentáre a ďalšie úložiská údajov. Neprisľubovať bezpečnú redakciu bez preukázaného odstránenia dát a overenej licencie enginu.

Konkrétne API, správanie knižníc a potrebu nových závislostí overiť pri implementácii. Zachovať oddelenie jadra od GUI, slovenské hlášky a podporu Windows/macOS.

## Kritériá dokončenia a overenie

- Odstránené údaje nie je možné získať kopírovaním, extrakciou ani odkrytím vrstiev.
- testovať reprezentatívne PDF a nezávislou kontrolou výstupu. Bez týchto dôkazov funkciu nevydávať.
- Nové operácie majú primerané testy jadra a kritických interakcií GUI; existujúce testy prejdú.
- Neúspešné uloženie nepoškodí existujúci cieľ; prepísanie a neuložené zmeny sa riešia v súlade s aplikáciou.

## Otázky pred implementáciou

- Potvrdiť rozsah prvej verzie a detaily ovládania uvedené ako návrh.
- Overiť správanie na poškodených, šifrovaných a veľkých vstupoch podľa rozsahu funkcie.
- Pri úprave digitálne podpísaných PDF zohľadniť platnosť podpisov; nezaručovať ich zachovanie bez overenia.
