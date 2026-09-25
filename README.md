# Tedom Cogeneration Modbus

Integrace pro Home Assistant, která čte data z kogeneračních jednotek TEDOM
(řídicí jednotka ComAp InteliCompact) přes Modbus TCP.

## Instalace (HACS)

1. HACS → Integrace → ⋮ → Vlastní repozitáře → přidat `https://github.com/UJBenda/tedom_modbus` (kategorie *Integration*).
2. Nainstalovat **Tedom Cogeneration Modbus** a restartovat Home Assistant.
3. Nastavení → Zařízení a služby → Přidat integraci → **Tedom Cogeneration Modbus**.

## Senzory (plugin InteliCompact)

Mapa registrů vychází z exportu GenConfigu `584-generator.TXT`, ~43 senzorů:

- **Generátor** – fázová a sdružená napětí, proudy L1–L3, frekvence, činný (celkem i po fázích), jalový a zdánlivý výkon, účiník, žádaný výkon
- **Síť** – napětí L1–L3, frekvence, výkon ze sítě, výkon zátěže
- **Motor** – otáčky, teplota vody / sekundární vody, teploty SEKCE 1/2, lambda
- **Stavy** – stav motoru, stav stykače (text dle Table#1), časovač
- **Statistika** – motohodiny, čas do servisu, počet startů, činná a jalová energie, počty stopů

## Ovládání

- **Tlačítka** – Start motoru, Stop motoru, Reset poruch, Reset houkačky
  (ComAp příkaz: argument do 46359–46360 a `1` do 46361 jedním zápisem;
  po provedení controller vrátí potvrzení, jinak HA zobrazí chybu)
- **Výběr** – Režim řídicího systému (VYP / MAN / SEM / AUT, registr 43204)
- **Číslo** – Konstantní výkon (43020), limity podle Min. výkonu paralelně a Jmenovitého výkonu

⚠️ Start/Stop funguje jen v režimu **MAN**. V AUT jednotka poslouchá vstup
`Ext.Start/Stop` a příkaz z Modbusu ignoruje. Pokud jsou v GenConfigu
příkazy nebo setpointy chráněné heslem, controller zápis odmítne.

Registry jsou v pluginu zapsané stejně jako v tabulce (např. `40021`). Adresa
v Modbus rámci je `registr − 40001` (`REGISTER_BASE` v pluginu). Pokud by
hodnoty vypadaly posunuté o jeden registr, stačí `REGISTER_BASE` změnit na `40000`.
Pokud by 32bitové hodnoty (motohodiny, energie) byly nesmyslně velké, změňte
`WORD_ORDER` na `"little"`.

Další typy jednotek lze přidat jako nový soubor `plugin_*.py` s `PLUGIN_MAP`
a jeho zápisem do `AVAILABLE_PLUGINS` v `const.py`.
