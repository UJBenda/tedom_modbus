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
