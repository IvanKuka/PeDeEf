# Overovanie digitálnych podpisov PDF

Stav: prvá lokálna kontrola implementovaná (kryptografická integrita, pokrytie a následné zmeny; dôvera certifikátu, zneplatnenie a overená časová pečiatka zatiaľ nie)
Priorita: P2 až P3
Náročnosť: vyššia

## Prínos

Zistiť, či dokument obsahuje digitálne podpisy, čo pokrývajú a aký je výsledok ich overenia. Nadväzuje na návrh 21, ale je užitočné aj samostatne pre prijaté dokumenty.

## Ovládanie a prvá verzia

Aktuálna akcia: **Upraviť strany → Vložiť a podpis → Overiť podpisy**. Kontroluje uložený súbor, nie rozpracované úpravy. Zobrazuje meno z certifikátu, integritu a pokrytie celého súboru alebo staršej revízie. Neodosiela sieťové požiadavky a výslovne uvádza neoverenú dôveru certifikátu, zneplatnenie a časovú pečiatku. Výsledok bez podpisov je odlíšený od chyby načítania/overovania.

Panel Podpisy zobrazí zoznam podpisov, údaje podpisujúceho z certifikátu, dostupné časové údaje a podrobný výsledok. Prvá verzia má lokálne overenie integrity a výslovné pomenovanie toho, čo nebolo overené. Meno z certifikátu nezamieňať s nezávisle overenou totožnosťou.

## Výsledky zobrazovať oddelene

- Kryptografická integrita podpisu a podpísanej revízie.
- Rozsah podpisu a následné zmeny dokumentu vrátane ďalších podpisov.
- Dôveryhodnosť certifikačnej cesty podľa zvolenej politiky a úložiska dôvery.
- Platnosť a stav zneplatnenia certifikátu, ak sú dostupné potrebné údaje.
- Čas uvedený podpisujúcim oproti overenej časovej pečiatke.
- Neznámy alebo neoveriteľný výsledok s konkrétnym dôvodom.

Nedostupná sieť alebo chýbajúci koreňový certifikát nesmú viesť k zjednodušenému tvrdeniu, že dokument bol pozmenený. Platná podpísaná staršia revízia sama osebe nepotvrdzuje nezmenenosť celej aktuálnej verzie.

## Technické súvislosti

Vybrať overovací engine a politiku dôvery, preveriť ich API a licenciu. Náhľad QtPdf nie je dôkazom platnosti podpisu. Sieťové overovanie certifikátov a časových pečiatok musí mať explicitne navrhnutý režim, limity a informáciu o odosielaných údajoch. Prvá verzia nesľubuje právne posúdenie ani univerzálnu podporu všetkých podpisových profilov.

Pri otvorení podpísaného PDF na úpravu zobraziť dôsledky plánovanej operácie. Bežné zlučovanie a export strán nepovažovať za postup zachovávajúci podpisy.

## Kritériá dokončenia

- Overiť vzorky so správnym podpisom, pozmeneným obsahom, neznámou autoritou, viacerými podpismi a následnými zmenami.
- Rozlíšiť neplatnosť, nedôveryhodnosť a nedostatok údajov.
- Uviesť zdroj času a rozsah vykonaných kontrol.
- Porovnať výsledky s nezávislým overovačom pri rovnakej politike dôvery.
- Poškodený podpis alebo dokument nespôsobí pád aplikácie.
