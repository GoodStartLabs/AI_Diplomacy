# ORDER NOTATION REFERENCE
**CRITICAL: Wrong notation = void order. One char wrong → order void → unit holds.**

## FORMAT: `[A/F] [3CODE] [ACTION] [TARGET]`
**Spacing**: Single spaces. ✓ `A PAR - BUR` ✗ `A PAR-BUR`
**Codes**: 3 uppercase. ✓ `PAR` ✗ `Paris`/`par`
**Units**: `A`(Army) `F`(Fleet) prefix required
**Actions**: `-`(move) `S`(support) `C`(convoy) `H`(hold) `B`(build) `D`(disband) `R`(retreat)

## ALL ORDER SYNTAX
```
Move:         A PAR - BUR
Hold:         A PAR H
Support Hold: A PAR S A MAR
Support Move: A PAR S A MAR - BUR
Convoy Army:  A PAR - LON VIA
Convoy Fleet: F ENG C A PAR - LON
Build:        A PAR B | F STP/NC B
Disband:      A PAR D
Retreat:      A BUD R GAL
```

## COAST NOTATION
**Dual-Coast**: STP(NC/SC), SPA(NC/SC), BUL(EC/SC)
**Format**: `F [PROV]/[COAST]` - Use `/` not `-`/`_`
**Adjacency**:
- STP/NC: BAR,NWY,FIN | STP/SC: GOB,FIN,LVN
- SPA/NC: MAO,GAS,POR | SPA/SC: WES,LYO,MAR
- BUL/EC: BLA,CON,RUM | BUL/SC: AEG,GRE,CON

```
F STP/NC - BAR | F GOB - STP/SC | F STP/NC B
```

## COMMON ERRORS
| Wrong | Right | Issue |
|-------|-------|-------|
| `A PAR- BUR` | `A PAR - BUR` | Missing spaces |
| `PAR - BUR` | `A PAR - BUR` | Missing unit |
| `A Paris - Bur` | `A PAR - BUR` | Use 3-letter codes |
| `A PAR HOLD` | `A PAR H` | Use single letter |
| `A PAR S MAR - BUR` | `A PAR S A MAR - BUR` | Missing unit in support |
| `A PAR - LON` | `A PAR - LON VIA` | Missing VIA |
| `F ENG CONVOY A PAR` | `F ENG C A PAR - LON` | Use C, include dest |
| `F STP B` | `F STP/NC B` | Coast required |

## HOME CENTERS
**Austria**: VIE(A), BUD(A), TRI(A/F) | **England**: LON(A/F), LVP(A/F), EDI(A/F) | **France**: PAR(A), MAR(A/F), BRE(A/F) | **Germany**: BER(A/F), KIE(A/F), MUN(A) | **Italy**: ROM(A/F), VEN(A/F), NAP(A/F) | **Russia**: MOS(A), STP(A/F), SEV(A/F), WAR(A) | **Turkey**: CON(A/F), ANK(A/F), SMY(A/F)

## VALIDATION
Before submitting:
- [ ] Format: `[A/F] [3CODE] [ACTION] [TARGET]` with single spaces
- [ ] Unit type matches terrain (A=land, F=coastal/sea)
- [ ] FROM/TO adjacent
- [ ] Support matches exact move+coast
- [ ] Convoy: army has VIA, fleet has `C A FROM - TO`, chain complete

## CRITICAL EXAMPLES

**Convoy (ALWAYS use VIA)**:
```
F BRE C A PAR - LON    (fleet convoys)
F ENG C A PAR - LON    (fleet convoys)
A PAR - LON VIA        (army MUST use VIA)
NEVER: A PAR - LON     (invalid without VIA → VOID)
```
Both fleets convoy same route; army MUST include VIA.

**Support with coast**:
```
F BRE S F MAO - SPA/NC
F MAO - SPA/NC
```
Support must match exact destination+coast.

**Coordinated attack**:
```
France: A MAR - BUR | A PAR S A MAR - BUR  (strength 2)
Germany: A BUR H                            (strength 1)
Result: France wins, takes BUR
```
Support adds strength; must match exact move.

## NEVER
- Omit spaces around separators
- Use full names or lowercase
- Forget VIA on convoyed armies
- Support without matching exact destination
- Build in non-home/occupied centers
- Use `-` for coast (use `/`)
- Move armies to seas or fleets to landlocked

**ONE CHAR WRONG = ORDER VOID**
