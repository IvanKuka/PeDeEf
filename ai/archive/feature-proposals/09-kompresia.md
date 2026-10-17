# Zmenšenie veľkosti PDF

Stav: implementované (bezstratovo cez pypdf; voliteľne prekódovanie bežných JPEG obrázkov cez Qt – bez novej knižnice; malé písmo 6 bodov je pri profile „Najmenší súbor“ horšie čitateľné, dialóg na to upozorňuje)  
Priorita: P3  
Odhad náročnosti: Vyššia (relatívny, nie časový záväzok)

## Prínos

Pripraviť menší dokument pre e-mail alebo formulár s limitom veľkosti.

## Navrhované ovládanie

Profily kvality, porovnanie veľkosti a náhľad detailu; samostatný nový výstup.

## Prvá verzia

Najprv bezstratová optimalizácia s poctivým hlásením výsledku; potom voliteľná úprava obrázkov.

## Technické súvislosti

Oddeliť bezstratové čistenie od stratového prevzorkovania obrázkov. Nerasterizovať automaticky textové PDF. Presný engine a jeho licenciu preveriť pri realizácii.

Konkrétne API, správanie knižníc a potrebu nových závislostí overiť pri implementácii. Zachovať oddelenie jadra od GUI, slovenské hlášky a podporu Windows/macOS.

## Kritériá dokončenia a overenie

- Zobraziť skutočné veľkosti pred/po.
- ak sa súbor nezmenší, uviesť to.
- testovať text, skeny, priehľadnosť a čitateľnosť malého písma.
- Nové operácie majú primerané testy jadra a kritických interakcií GUI; existujúce testy prejdú.
- Neúspešné uloženie nepoškodí existujúci cieľ; prepísanie a neuložené zmeny sa riešia v súlade s aplikáciou.

## Otázky pred implementáciou

- Potvrdiť rozsah prvej verzie a detaily ovládania uvedené ako návrh.
- Overiť správanie na poškodených, šifrovaných a veľkých vstupoch podľa rozsahu funkcie.
- Pri úprave digitálne podpísaných PDF zohľadniť platnosť podpisov; nezaručovať ich zachovanie bez overenia.
