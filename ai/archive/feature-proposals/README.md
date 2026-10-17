# Návrhy rozšírení PDF Nástrojov

Tento priečinok obsahuje návrhy funkcií podľa kontroly README a vybraných zdrojových súborov z 15. 10. 2026. Návrhy nie sú požiadavkou na okamžitú implementáciu ani potvrdením dostupnosti konkrétnych API.

## Odporúčané poradie

1. Pohodlie pri úpravách: veľký náhľad, Späť/Znova, presúvanie strán a nastavenia.
2. Bežné pracovné postupy: prekladanie skenov, obrázky/PDF, číslovanie, prázdne strany a vyhľadávanie.
3. Rozšírené operácie: dávky, záložky, heslá, orez a metadáta podľa reálneho používania.
4. Väčšie samostatné etapy: OCR, kompresia, porovnanie, projekty a anonymizácia.

P1 = odporúčaná prvá etapa; P2 = ďalšie praktické rozšírenia; P3 = väčší alebo špecializovaný rozsah. Náročnosť je orientačná a nezahŕňa overený odhad času.

## Zoznam návrhov

| Funkcia | Priorita | Náročnosť |
|---|---|---|
| [Presúvanie, duplikovanie a vkladanie strán](01-presuvanie-stran.md) | P1 | Stredná |
| [Späť a Znova](02-spat-a-znova.md) | P1 | Stredná |
| [Veľký náhľad strany](03-velky-nahlad.md) | P1 | Menšia až stredná |
| [Prekladanie predných a zadných skenov](04-prekladanie-skenov.md) | P2 | Menšia až stredná |
| [Obrázky do PDF a PDF do obrázkov](05-obrazky-a-pdf.md) | P2 | Stredná |
| [Číslovanie strán a pečiatky](06-cislovanie-a-peciatky.md) | P2 | Stredná |
| [Dávkové spracovanie](07-davkove-spracovanie.md) | P2 | Stredná až vyššia |
| [OCR a prehľadávateľné skeny](08-ocr.md) | P3 | Vyššia |
| [Zmenšenie veľkosti PDF](09-kompresia.md) | P3 | Vyššia |
| [Porovnanie dvoch PDF](10-porovnanie-pdf.md) | P3 | Vyššia |
| [Hľadanie prázdnych strán](11-prazdne-strany.md) | P2 | Stredná |
| [Orezanie okrajov strán](12-orezanie-stran.md) | P2 | Stredná |
| [Záložky a obsah dokumentu](13-zalozky.md) | P2 | Stredná až vyššia |
| [Otváranie a ochrana heslom](14-hesla.md) | P2 | Stredná |
| [Vlastnosti dokumentu a odstránenie metadát](15-metadata-a-sukromie.md) | P2 | Menšia až stredná |
| [Uloženie rozpracovanej práce](16-pracovne-projekty.md) | P3 | Stredná až vyššia |
| [Vyhľadávanie textu](17-vyhladavanie-textu.md) | P2 | Stredná |
| [Vloženie obrázka podpisu](18-podpis-obrazkom.md) | P3 | Stredná až vyššia |
| [Trvalé začiernenie citlivých údajov](19-anonymizacia.md) | P3 | Vysoká |
| [Zapamätanie nastavení a rýchle voľby](20-predvolby.md) | P1 | Menšia |
| [Digitálne podpisovanie certifikátom](21-digitalne-podpisovanie.md) | P3 | Vyššia |
| [Overovanie digitálnych podpisov](22-overovanie-podpisov.md) | P2 až P3 | Vyššia |
| [Vpísanie textu do strany](23-vpisanie-textu.md) | P2 | Stredná |
| [Vyplnenie formulárových polí](24-vyplnenie-formulara.md) | P2 | Stredná až vyššia |

## Väzby a spoločné pravidlá

- Presúvanie, duplikovanie a vloženie strán potrebujú stabilný model výskytov strán; dohodnúť ho spolu s históriou Späť/Znova.
- Veľký náhľad je vhodný základ pre orez, pečiatky a obrázok podpisu.
- OCR a vyhľadávanie sú samostatné funkcie: textové PDF sa dajú prehľadávať aj bez OCR.
- Dávkové spracovanie má opakovane používať overené operácie jadra.
- Návrhy predpokladajú lokálne spracovanie. Sieťové služby a odosielanie dokumentov nie sú súčasťou týchto návrhov.
- Existujúci projekt zámerne nepoužíva PyMuPDF pre AGPL licenciu; pri výbere nových enginov rešpektovať tento kontext a overiť licencie aj spôsob distribúcie.
- Chrániť zdrojové dokumenty, zachovať zrozumiteľné chyby a pri nových viacvýstupových operáciách definovať správanie pri čiastočnom zlyhaní.

## Východiskový stav

Aplikácia používa Python, PySide6/QtPdf a pypdf. Má záložky Zlúčiť PDF a Upraviť strany, podporuje rozsahy strán, otočenie, odstránenie, extrakciu a rozdelenie. Jadro je v `pdftool/operations.py`, práca so stranami v `pdftool/gui/pages_tab.py` a náhľady v `pdftool/gui/thumbnails.py`. Existujú testy jadra aj GUI. Tento balík mení iba dokumentáciu.

