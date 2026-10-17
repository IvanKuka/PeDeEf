# Vyplnenie formulárových polí

Stav: implementované (textové polia vrátane viacriadkových, zaškrtávacie políčka, prepínače, výberové zoznamy; vyplnené polia sa zlúčia do strany)  
Priorita: P2  
Odhad náročnosti: Stredná až vyššia (relatívny, nie časový záväzok)

## Prínos

Vyplniť interaktívny PDF formulár (žiadosť, tlačivo úradu) bez Adobe Readera, so slovenskou diakritikou.

## Ovládanie

Vložiť a podpis → Vyplniť formulár. Vľavo je zoznam polí (popis poľa, ak ho formulár má, inak názov), vpravo náhľad strany. Kliknutie na pole v náhľade presunie kurzor na jeho vyplnenie a pri prechode na pole sa zobrazí jeho strana. Polia len na čítanie sú zobrazené, ale nedajú sa meniť. Dokument bez polí odkáže na Vpísať text.

## Technické súvislosti

- Polia sa čítajú z widgetov na stranách (`forms.read_form_fields`), nie zo slovníka `/AcroForm`: aplikácia kopíruje strany jednotlivo a slovník formulára sa pri tom nezachová. Pri kopírovaní strán sa preto zachovávajú rodičovské polia widgetov (`operations._keep_field_parents`); bez nich by sa po každej úprave strán stratili názvy, typy a hodnoty polí s hierarchiou (napr. všetky prepínače).
- Zmenené polia sa zlúčia: hodnota sa nakreslí cez Qt do strany (písmo vložené, diakritika funguje všade) a widget poľa sa zo strany odstráni. Nezmenené polia zostanú tak, ako sú. Generovanie vzhľadu cez pypdf sa nepoužíva, pretože písma formulárov často nemajú slovenské znaky.
- Zachová sa farba pozadia a okraja poľa (`/MK`). Vlastný vzhľad poľa mimo `/MK` sa po zlúčení nezachová.
- Automatická veľkosť písma (`0 Tf`) sa prispôsobí výške poľa a dlhý text sa zmenší na šírku poľa. Zarovnanie podľa `/Q`, otočenie podľa otočenia strany a `/MK /R`.
- Nevypĺňajú sa podpisové, heslové, súborové polia a tlačidlá. Hrebeňové polia (comb) sa kreslia ako bežný text.
- Náhľady QtPdf nevykresľujú widgety formulárov, preto dialóg nezmenené polia len podfarbí a vpíše do nich ich aktuálnu hodnotu.

## Kritériá dokončenia a overenie

- Hodnoty s diakritikou sa dajú z výsledku vyhľadať; vyplnené widgety vo výsledku nie sú, ostatné áno.
- Poloha poľa sedí na otočenej strane aj pri duplikovanej strane.
- Polia s rodičom (napr. prepínače) sa dajú vyplniť aj po predchádzajúcej úprave strán.
- Pri digitálne podpísanom dokumente dialóg upozorní, že podpis v novom súbore nebude platný.

## Možné rozšírenia

- Ponechať formulár interaktívny: zachovať `/AcroForm` pri ukladaní a generovať vzhľad poľa z vrstvy Qt ako Form XObject.
- Vykresľovať anotácie aj v náhľadoch strán (QtPdf `RenderFlag.Annotations`).
