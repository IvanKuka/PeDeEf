# Vpísanie textu do strany

Stav: implementované (viac textov na viacerých stranách, viacriadkový text, veľkosť písma; umiestnenie na otočenej a orezanej strane overené vykreslením; písmo Arial vložené do PDF)  
Priorita: P2  
Odhad náročnosti: Stredná (relatívny, nie časový záväzok)

## Prínos

Vyplniť naskenované alebo tlačené tlačivo, ktoré nemá formulárové polia, a doplniť poznámku, dátum či meno kamkoľvek na stranu.

## Ovládanie

Vložiť a podpis → Vpísať text. Kliknutím do náhľadu sa začne nový text (stred prvého riadku je v mieste kliknutia), text sa píše do poľa vľavo. Kliknutím na existujúci text sa vyberie, ťahaním alebo šípkami (po 1 bode) sa presúva. Veľkosť písma platí pre vybraný text aj pre nové texty. Prázdny text po výbere iného zanikne. Náhľad má priblíženie ako pri začiernení.

## Technické súvislosti

Text sa kreslí cez Qt do tej istej vrstvy ako pečiatky a obrázok podpisu (`stamp_layer.write_pages_with_overlay`), takže diakritika funguje v každom prehliadači. Poloha je podiel viditeľnej strany (po otočení a oreze). Text sa vždy udrží na strane. Výsledok je obsah strany, nie upraviteľná anotácia; oprava sa robí cez Späť.

Úprava textu, ktorý už v PDF je, nie je súčasťou funkcie: vyžadovala by prácu s vloženými podmnožinami písiem (napr. cez PyMuPDF, ktorý projekt pre licenciu AGPL nepoužíva).

## Kritériá dokončenia a overenie

- Umiestnenie výstupu zodpovedá náhľadu aj na otočenej strane.
- Diakritika sa dá z výsledku vyhľadať a skopírovať.
- Prázdne texty sa neukladajú; bez textu nejde potvrdiť.
- Úprava sa správa ako ostatné úpravy: Späť/Znova, uloženie na konci, zdroj sa nemení.
