# Unit Types

## Army vs Fleet
|Property|Army (A)|Fleet (F)|
|-|-|-|
|Terrain|Land+Coast|Water+Coast|
|Cannot Enter|Water (unless convoyed)|Landlocked|
|Coast Notation|NEVER|MUST for SPA/STP/BUL|
|Role|Inland centers|Sea control+Convoy|

## Coast Rules
**Multi-coast:** SPA, STP, BUL (2 coasts each)
- Fleets MUST specify: `F MAO - SPA/NC`✓|`F MAO - SPA`✗
- No coast-switching: `F SPA/NC - SPA/SC`✗
- Armies ignore coasts: `A SPA`
- Support must specify: `F GAS S F MAO - SPA/NC`✓

<example>F STP/NC can convoy A MOS - NWY<reasoning>North coast borders Barents Sea, enabling convoy</reasoning></example>

## Validation
- Unit type valid? (A: not water|F: not landlocked)
- Coast specified for F→SPA/STP/BUL?
- Convoy: All fleets issue C orders?
