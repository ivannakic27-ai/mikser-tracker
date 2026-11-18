# Pojmovi za pretragu samostojećih miksera

## Što se stvarno koristi na HR shopovima (provjereno)

| Shop / izvor | Kategorija koja sadrži stand mixere |
|---|---|
| Mall.hr | "Kuhinjski roboti" (`/kuhinjski-roboti`), ali i "Mikseri", "Profesionalni (planetarni) mikseri", "Multipraktici" |
| Jeftinije.hr | "Kuhinjski roboti i multipraktici" (799 proizvoda; opis: >1000 W = težko tijesto) i zasebno "Mikseri" (4282, većina ručni/štapni) |
| Nabava.net | "Mikseri" (ručni, posudni, robotski) i "Kuhinjski roboti i multipraktici" |
| Harvey Norman | "Kuhinjski roboti" u "Kuhinjski roboti i multipraktici" |
| Big Bang | "Kuhinjski roboti" |
| Ronis | "Kuhinjski roboti i multipraktici" |
| Links | "Mikseri" |
| Elipso, Instar, Mikronis | "Mikseri" / "Blenderi i mikseri" |
| Kenwood | "kMix", "Chef", "Chef XL", "kuhinjski stroj" |

Zaključak: naziv kategorije je uglavnom **"Kuhinjski roboti"** (ne "samostojeći mikser"), ali opisi proizvoda često koriste **"samostojeći mikser"** (Mall.hr za KitchenAid). Kategorije "Mikseri" miješaju ručne, štapne i stand mixere, pa je potreban filter.

## Pojmovi (HR)
samostojeći mikser, stolni mikser, kuhinjski robot, kuhinjski stroj, planetarni mikser, planetarni kuhinjski robot, mikser s posudom, mikser sa zdjelom, mikser za tijesto, robot za tijesto, mjesilica za tijesto, mijesilica, mikser s kukom za tijesto, profesionalni mikser, robotski mikser, multipraktik (pazi: često blender/sjeckalica, nije stand mixer), kuhinjski robot s grijanjem (Thermomix tip; različit proizvod, ocijeniti zasebno)

## Pojmovi (EN)
stand mixer, planetary mixer, kitchen machine, kitchen mixer, bowl mixer, dough mixer, food processor with bowl (druga kategorija, često ne mijesi tijesto kao stand mixer), tilt-head mixer, bowl-lift mixer

## Linije proizvoda koje treba tražiti po modelu
KitchenAid Artisan (5KSM125, 5KSM175, 5KSM185), KitchenAid Classic (5K45SS), KitchenAid Heavy Duty/Classic bowl-lift; Kenwood kMix (KMX), Chef (KVC), Chef XL (KVL), Titanium Chef; Bosch MUM (MUM5, MUM9, MUM58); Tefal Bake Cook/Masterchef; Philips; Gorenje MMC; Sencor STM; Severin; Smeg SMF; Electrolux; Klarstein Bella; Ravanson; Westinghouse Retro; Ruhhy; Bergner; Elit; Esperanza; Cecotec.

## Pravila filtriranja u scraperu
- Uključi: naziv/URL/specifikacije sadrže planetar, stand mixer, samostoje, posuda ≥ 3 L + nastavak za tijesto (kuka) + motor na postolju.
- Isključi: ručni mikseri, štapni mikseri, blenderi, multipraktici bez kuke za tijesto, dodaci/nastavci/posude (aksesoari), rabljeno/"Raspakirano".
- Spajanje: EAN > MPN (npr. 5KSM175PSEBK) > normalizirani brend + model.

## Napomena
Ovo je polazna lista. Kategorije po shopu treba potvrditi tijekom izrade adaptera u Fazi 2. Pojam koji vraća najviše pravih rezultata po shopu bit će zabilježen tada.
