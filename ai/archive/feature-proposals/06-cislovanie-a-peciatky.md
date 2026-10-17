# Číslovanie strán a pečiatky

Stav: implementované (písmo Arial vložené do PDF; text bez podkladu, takže môže prekryť obsah pri okraji)  
Priorita: P2  
Odhad náročnosti: Stredná (relatívny, nie časový záväzok)

## Prínos

Doplniť orientáciu a označenie do balíka dokumentov.

## Navrhované ovládanie

Text typu „3 / 25“, počiatočné číslo, poloha, veľkosť, rozsah strán; vlastný text, dátum alebo „KÓPIA“; náhľad pred uložením.

## Prvá verzia

Číslovanie a textová pečiatka na vybraných stranách.

## Technické súvislosti

Oddeliť vytvorenie textovej vrstvy od jej zlúčenia s PDF. Preveriť fonty so slovenskou diakritikou, licenciu a otočené strany. Závislosti vybrať až pri implementácii.

Konkrétne API, správanie knižníc a potrebu nových závislostí overiť pri implementácii. Zachovať oddelenie jadra od GUI, slovenské hlášky a podporu Windows/macOS.

## Kritériá dokončenia a overenie

- Správna diakritika a umiestnenie na rôznych rozmeroch.
- číslovanie rešpektuje zvolený rozsah.
- výstup zachová čitateľnosť dokumentu.
- Nové operácie majú primerané testy jadra a kritických interakcií GUI; existujúce testy prejdú.
- Neúspešné uloženie nepoškodí existujúci cieľ; prepísanie a neuložené zmeny sa riešia v súlade s aplikáciou.

## Otázky pred implementáciou

- Potvrdiť rozsah prvej verzie a detaily ovládania uvedené ako návrh.
- Overiť správanie na poškodených, šifrovaných a veľkých vstupoch podľa rozsahu funkcie.
- Pri úprave digitálne podpísaných PDF zohľadniť platnosť podpisov; nezaručovať ich zachovanie bez overenia.
