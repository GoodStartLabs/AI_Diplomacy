# Adjustment Phase

## Rules

**Timing:** Post-Fall movement/retreats. Skip if units=centers.

**Formula:** Adjustment = Centers - Units (positive=BUILD, negative=DISBAND)

**Constraints:**
- Build only in unoccupied home centers under control
- Fleets coastal only (landlocked: VIE,PAR,MUN,MOS,WAR)
- Occupied/lost homes: no build

## Home Centers

**AUS:** VIE,BUD,TRI | **ENG:** LON,LVP,EDI | **FRA:** PAR,BRE,MAR | **GER:** BER,KIE,MUN | **ITA:** ROM,NAP,VEN | **RUS:** MOS,STP,WAR,SEV | **TUR:** CON,ANK,SMY

**Dual-Coast:** STP/SPA/BUL need coast (NC/SC or EC/SC)

## Build Priorities

**CRITICAL:** Defend home vs adjacent threat (A VIE B if Italy in TYR)
**HIGH:** Fill theater gap/alliance op (F EDI B if no North Sea units)
**MEDIUM:** Offensive expansion (A MUN B → BOH)

**Rule:** Address highest priority first. Never LOW if CRITICAL/HIGH exists.

## Disband Priorities

**Keep:** Home defenders, front attackers (in/adjacent home centers)
**Disband:** Isolated, trapped, orphaned (surrounded/far from theater)

## Syntax

```
Build: [A/F] [LOC] B (ex: A PAR B, F STP/NC B)
Disband: [A/F] [LOC] D (ex: A SIL D)
None: {"orders": []}
```

## Example

**France Build:**
```
6 centers (PAR,BRE,MAR,BEL,HOL,SPA), 4 units → 2 builds
Available: PAR (A only), BRE (A/F) | MAR occupied
Threat: Germany adjacent
Orders: A PAR B, F BRE B
Why: PAR defends home, BRE controls Atlantic
```

**Validation:** Builds ≤ unoccupied homes, disbands match requirement, fleets coastal, dual-coast specified
