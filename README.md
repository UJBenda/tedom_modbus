# Tedom Cogeneration Modbus

Integrace pro Home Assistant, která čte a ovládá kogenerační jednotky TEDOM
(řídicí jednotka ComAp InteliCompact) přes Modbus TCP.

## Instalace (HACS)

1. HACS → Integrace → ⋮ → Vlastní repozitáře → přidat `https://github.com/UJBenda/tedom_modbus` (kategorie *Integration*).
2. Nainstalovat **Tedom Cogeneration** a restartovat Home Assistant.
3. Nastavení → Zařízení a služby → Přidat integraci → **Tedom Cogeneration**
   (IP, port, Modbus adresa řídicí jednotky, interval čtení).

## Co integrace umí

- **Senzory** – výkon, otáčky, frekvence, napětí a proudy generátoru, teplota vody,
  napětí baterie, motohodiny, počet startů, vyrobená energie, stav motoru a jističe,
  binární vstupy (Ext. Start/Stop, nouzové zastavení, tlak a hladina oleje)
- **Režim stroje** – VYP / SEM / AUT
- **Požadovaný výkon** a **požadovaná teplota**
- **Tlačítka** – Reset poruch, Start motoru, Stop motoru

Start/Stop se posílá jako ComAp příkaz (argument do 46359–46360, `1` do 46361).
Controller ho provede jen v režimu **SEM**; v AUT jednotka poslouchá vstup
Ext. Start/Stop. Pokud příkaz neprovede, Home Assistant zobrazí chybu.

## Poznámky k ComAp

- Adresa v Modbus rámci = číslo registru − 40001 (např. otáčky 40021 → 20).
- Po každém cyklu čtení se TCP spojení uzavře – komunikační moduly ComAp mají
  jen málo TCP slotů.
- Registry jsou v `plugin_tedom.py`.
