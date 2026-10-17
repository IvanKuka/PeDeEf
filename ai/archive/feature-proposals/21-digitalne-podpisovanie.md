# Digitálne podpisovanie PDF certifikátom

Stav: prvá verzia implementovaná (P12/PFX, pyHanko, podpis bez viditeľného poľa, inkrementálny zápis a kontrola integrity; viditeľné pole, eID, tokeny a časová pečiatka zatiaľ nie)
Priorita: P3
Náročnosť: vyššia

## Prínos a rozsah

Podpísať PDF certifikátom. Grafický podpis z návrhu 18 je samostatná funkcia: viditeľný obrázok a kryptografický podpis sa musia v rozhraní rozlišovať.

## Prvá verzia a ovládanie

Aktuálne ovládanie: **Upraviť strany → Vložiť a podpis → Digitálne podpísať P12/PFX**. Vybrať certifikát, zadať heslo, načítať a skontrolovať údaje podpisujúceho a platnosť, prípadne doplniť dôvod, potom uložiť samostatné PDF. Podpis je bez viditeľného poľa; zobrazí ho panel podpisov PDF prehliadača. Výsledok sa pred uložením skontroluje. Šifrovanie nezmeneného vstupu sa zachová. Ďalší podpis sa pridáva inkrementálne len k nezmenenému dokumentu a iba ak sa zachová integrita predchádzajúcich podpisov. Zdroj sa neprepisuje.

Nasledujúce body sú cieľový rozsah ďalších etáp; viditeľné umiestnenie zatiaľ nie je implementované.

- Akcia Podpísať PDF otvorí výber certifikátu zo súboru P12/PFX a zadanie hesla.
- Používateľ môže zvoliť miesto viditeľného podpisového poľa, meno zobrazovať podľa certifikátu a doplniť dôvod podpisu.
- Zobraziť súhrn pred podpisom a uložiť samostatné podpísané PDF.
- Po podpísaní ponúknuť kontrolu výsledku, pozri návrh 22.
- Podporu eID, systémového úložiska, USB tokenov a vzdialeného podpisovania riešiť ako ďalšie samostatné etapy po overení poskytovateľov a platforiem.

## Technický návrh a obmedzenia

Existujúci zápis strán cez pypdf nepovažovať za podpisovací engine. Vybrať a overiť udržiavanú knižnicu pre PDF podpisy vrátane licencie, podpory algoritmov a balenia Windows/macOS. Konkrétne API ani kompatibilita zatiaľ nie sú overené.

Podpisovať až finálny dokument. Pre už podpísané vstupy najprv analyzovať existujúce podpisy a povolené zmeny. Pridanie ďalšieho podpisu vyžaduje overený inkrementálny zápis; nesmie potichu prepísať pôvodnú štruktúru bežným exportom strán.

Heslo, súkromný kľúč ani obsah certifikátového balíka neukladať do logov alebo nastavení. Predvolene si nepamätať súbor certifikátu. Nepoužívať vlastnú kryptografiu.

Časovú pečiatku, údaje pre dlhodobé overovanie a konkrétny profil PAdES navrhnúť až po overení požiadaviek a enginu. Sieťové služby zapájať iba s viditeľným vysvetlením, čo sa odosiela. Samotný výber PFX ani obrázok podpisu neoznačovať automaticky za kvalifikovaný elektronický podpis; právne kategórie nie sú týmto návrhom posúdené.

## Kritériá dokončenia

- Výsledný podpis overí nezávislý kompatibilný nástroj; samotné zobrazenie podpisového obrázka nie je úspešný test.
- Otestovať nesprávne heslo, chýbajúci súkromný kľúč, neplatný vstup, zrušenie a chybu zápisu.
- Zmena podpísaného obsahu sa pri overovaní rozpozná.
- Podpisové pole sedí aj na otočenej strane a pri inom rozmere.
- Existujúce podpisy sa zachovajú iba v overenom podporovanom postupe; nepodporovaný prípad má jasnú hlášku.
- Zdroj zostane zachovaný a citlivé údaje sa neobjavia v diagnostike.
