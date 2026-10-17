# Otváranie a ochrana heslom

Stav: implementované (otvorenie s heslom vrátane náhľadov; uloženie s heslom AES-256; prázdne heslo sa skúša automaticky, ručne zadané prázdne je nesprávne)  
Priorita: P2  
Odhad náročnosti: Stredná (relatívny, nie časový záväzok)

## Prínos

Pracovať s vlastnými zaheslovanými PDF a chrániť nový výstup.

## Navrhované ovládanie

Pri otvorení dialóg na heslo s opakovaným pokusom; pri ukladaní voliteľné heslo na otvorenie s potvrdením.

## Prvá verzia

Otvorenie dokumentu pomocou zadaného hesla; šifrovanie výstupu v ďalšom kroku.

## Technické súvislosti

open_pdf() dnes skúša iba prázdne heslo. Zabezpečiť rovnakú autorizáciu aj pre QtPdf náhľady. Heslá neposielať do logov ani trvalých nastavení; algoritmus overiť vo verzii pypdf používanej projektom.

Konkrétne API, správanie knižníc a potrebu nových závislostí overiť pri implementácii. Zachovať oddelenie jadra od GUI, slovenské hlášky a podporu Windows/macOS.

## Kritériá dokončenia a overenie

- Nesprávne heslo a zrušenie majú jasný výsledok.
- správne heslo funguje v náhľadoch aj operáciách.
- výstup sa bez hesla neotvorí.
- prázdne heslo má explicitné pravidlo.
- Nové operácie majú primerané testy jadra a kritických interakcií GUI; existujúce testy prejdú.
- Neúspešné uloženie nepoškodí existujúci cieľ; prepísanie a neuložené zmeny sa riešia v súlade s aplikáciou.

## Otázky pred implementáciou

- Potvrdiť rozsah prvej verzie a detaily ovládania uvedené ako návrh.
- Overiť správanie na poškodených, šifrovaných a veľkých vstupoch podľa rozsahu funkcie.
- Pri úprave digitálne podpísaných PDF zohľadniť platnosť podpisov; nezaručovať ich zachovanie bez overenia.
