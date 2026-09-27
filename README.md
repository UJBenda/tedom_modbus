# Tedom Cogeneration Modbus

Integrace pro Home Assistant, která čte a ovládá kogenerační jednotky TEDOM
(řídicí jednotka ComAp InteliCompact) přes Modbus TCP.

## Instalace (HACS)

1. HACS → Integrace → ⋮ → Vlastní repozitáře → přidat `https://github.com/UJBenda/tedom_modbus` (kategorie *Integration*).
2. Nainstalovat **Tedom Cogeneration** a restartovat Home Assistant.
3. Nastavení → Zařízení a služby → Přidat integraci → **Tedom Cogeneration**
   (IP, port, Modbus adresa řídicí jednotky, interval čtení).

## Co integrace umí

- **Generátor** – výkon (celkem i po fázích), jalový a zdánlivý výkon, účiník,
  napětí (fázová i sdružená), proudy, frekvence
- **Síť a spotřeba** – výkon ze sítě, výkon zátěže, napětí a frekvence sítě
- **Motor a teplo** – otáčky, teploty vody, SEKCE 1/2, lambda, baterie
- **Údržba** – motohodiny, čas do servisu, počet startů a stopů, vyrobená energie
- **Stavy a signály** – stav motoru a jističe, časovač, výstraha, centrální stop,
  tlak a hladina oleje, stykače, ventil paliva, čerpadla, lampy ECU, poruchy ECU
- **Nastavení** – režim stroje, požadovaný výkon, požadovaná teplota
- **Tlačítka** – Reset poruch, Start motoru, Stop motoru

Méně důležité entity jsou ve výchozím stavu vypnuté – zapnout je lze v nastavení entity.

Start/Stop se posílá jako ComAp příkaz (argument do 46359–46360, `1` do 46361).
Controller ho provede jen v režimu **SEM** nebo **MAN**; v AUT jednotka poslouchá vstup
Ext. Start/Stop. Pokud příkaz neprovede, Home Assistant zobrazí chybu.

## Plánovač podle spotových cen

Integrace umí sama naplánovat běh jednotky podle spotových cen a spínat ji
(příkazy Start/Stop) – bez pyscriptu a bez automatizací.

1. Nainstaluj integraci **Czech Energy Spot Prices** (HACS).
2. U jednotky v **Nastavit** vyber senzor ceny (výchozí
   `sensor.current_spot_electricity_price`, lze i `…_15min`) a případně senzor teploty nádrže.
3. V entitách zařízení nastav **Plánovač režim** (Vypnuto / Ručně / Podle teploty).

Jak plánuje:

- **Počet startů × bloky na běh** – např. 3 × 3 = 9 čtvrthodin (2 h 15 min). Každý běh
  má aspoň „bloky na běh“ čtvrthodin, startů je nejvýš „počet startů“.
- **Strategie** *Nejdražší* (výchozí – výroba do sítě) nebo *Nejlevnější*.
- **Cena startu (Kč)** – plán se rozdělí na víc běhů jen tehdy, když to vynese víc než
  cena dalšího startu. 0 = čistě nejdražší/nejlevnější čtvrthodiny.
- **Smí běžet od–do** – mimo okno se nic nenaplánuje (může jít přes půlnoc,
  od = do znamená celý den).
- **Nejet při záporné ceně** – vyřadí čtvrthodiny se zápornou cenou.
- **Podle teploty** – počet bloků klesá lineárně od plného počtu (studená nádrž)
  k nule (teplá nádrž); ve 23:50 se zítřek přepočítá s aktuální teplotou.
  **Pojistka max. teploty** blok přeskočí a jednotku nezapne.

Plán na zítřek (00–24) se spočítá, jakmile jsou známé zítřejší ceny, a znovu při každé
změně nastavení. Každou čtvrthodinu integrace jednotku podle plánu zapne; na konci
naplánovaného běhu ji vypne. Ruční běh mimo plán nevypíná. V režimu Vypnuto na jednotku
nesahá. Start/Stop funguje jen v režimu stroje **SEM** nebo **MAN** – v AUT ho jednotka
ignoruje (chyba je vidět v atributu `posledni_chyba` senzoru „Plán dnes“).

Hotový řídicí panel je v [`dashboards/kogenerace.yaml`](dashboards/kogenerace.yaml).

## Přehled energií

Senzor **Vyrobená energie** (kWh, stále rostoucí) lze přidat v *Nastavení → Přehled
energií* jako zdroj výroby (sekce Solární panely / výroba) – HA z něj počítá denní výrobu.

## Typ generátoru

V nastavení integrace (i později přes **Nastavit**) se volí typ generátoru.
Určuje číselník režimů a stavů:

| Typ | Režimy (registr 43204) | Stavy motoru/jističe |
|---|---|---|
| Asynchronní | VYP / SEM / AUT | původní ověřená tabulka |
| Synchronní (např. 584) | VYP / MAN / SEM / AUT | Table#1 z exportu GenConfigu |

## Poznámky k ComAp

- Adresa v Modbus rámci = číslo registru − 40001 (např. otáčky 40021 → 20).
- Po každém cyklu čtení se TCP spojení uzavře – komunikační moduly ComAp mají
  jen málo TCP slotů.
- Registry jsou v `plugin_tedom.py`.
