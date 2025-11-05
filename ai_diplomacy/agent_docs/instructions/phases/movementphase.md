# Movement Phase Instructions

## PHASE OBJECTIVE
Issue orders maximizing territorial control and supply center gains. Orders execute simultaneously. Spring/Fall twice yearly; builds only in Adjustment Phase.

## ORDER TYPES
Hold (H): `A PAR H` - +1 defense auto. Use when defending.

Move (-): `A PAR - BUR` - Adjacency required (armies: land; fleets: coast/sea). Strength = 1 + supports. Attack > Defense = success; equal = bounce.

Support (S): `A MAR S A PAR - BUR` (move) or `F NTH S F LON` (hold)
- Adjacent to DESTINATION (not origin)
- CUT if: Enemy moves to supporter OR supporter dislodged (except unit being supported against)
- Must EXACTLY match supported order

Convoy (C): `F ENG C A LON - BRE` - Multi-zone: ALL fleets must convoy same army. Fails if ANY fleet dislodged.

Dual-Coast: STP/SPA/BUL - ALWAYS specify NC/SC/EC: `F STP/NC - NWY`

## RESOLUTION
Simultaneity: All orders resolve at once. Equal strength = bounce; higher = dislodge.

Strength: 1 + supports (uncut); Hold gets +1 auto.

Support Cutting: Enemy moving to supporter = CUT (except against supported unit; dislodged attackers don't cut).

Beleaguered Garrison: Attacks from different origins don't combine.

## CRITICAL EXAMPLES

Example: Multi-Fleet Convoy
England LON-BEL: `A LON - BEL`, `F NTH C A LON - BEL`, `F ENG C A LON - BEL`
Reasoning: ALL fleets must convoy same army to same destination. If ANY fleet dislodged, convoy fails. Verify each fleet adjacent to route.
End

Example: Support Cut
France: `A PIC - BEL` + `A BUR S A PIC - BEL` (2v1). Germany: `A RUH - BUR` (cuts). Result: 1v1 bounce.
Reasoning: Attacking supporter cuts support, reducing 2v1 to 1v1. Often more effective than attacking target.
End

Example: Head-to-Head with Support
Austria: `A VIE - GAL` + `A BOH S A VIE - GAL` (2). Russia: `A GAL - VIE` (1). Result: Austria takes GAL.
Reasoning: 2v1 beats 1v1 in head-to-head. Without support would bounce (1v1). Support makes difference.
End

Example: Beleaguered Garrison
Belgium: `F BEL H` + `F NTH S F BEL` (2). Attackers: `A PIC - BEL` (1) + `A HOL - BEL` (1). Result: BEL holds.
Reasoning: Attacks from different origins don't combine. Defender compares strength against each individually (2>1 each).
End

Example: Support Validation
Germany: `A MUN - VIE`. Russia: `A WAR S A MUN - VIE` (valid: WAR adjacent to VIE) + `A GAL - BOH` (cuts Austrian support).
Reasoning: Supporter adjacent to destination (VIE), not origin (MUN). Third unit cuts enemy support vs overkill 3v1.
End

## STRATEGY
Per-Unit: Threatened? = move/hold with support. Can capture? = 2v1 if defended. Critical support? = ally attack/defend. Else reposition.

Risk: Low = neutral/2+ supports. Medium = 2v1/contested. High = unsupported vs defended/unconfirmed ally/undefended home.

Mitigation: Confirm ally orders; redundant supports; fallback plans.

Stage: Early: capture neutrals. Mid: 10-12 centers. Late: 14+ = 18; <8 = survive.

## VALIDATION
Format: `[A/F] [PROVINCE] [H/-/S/C] [DESTINATION]`; dual-coast `/NC`/`/SC`/`/EC`; supports match EXACTLY

Legality: Adjacent only; no fleets landlocked, no armies to sea (unless convoy); one order per unit; from possible_orders

Strategy: Home centers defended; critical moves confirmed; high-risk with fallbacks

Submit: `{"orders": ["A PAR - BUR", "A MAR S A PAR - BUR"]}`

## MAXIMS
1. Support is king - most attacks need it
2. Defend home centers - need for builds
3. 2v1 beats 1v1 - usually sufficient
4. Cut support when can't win direct
5. Convoys fragile - ANY fleet dislodged = fails
6. Simultaneous means simultaneous
7. Trust but verify - written confirmation

## RULES
ALWAYS: Use possible_orders; validate syntax; confirm ally supports; plan simultaneous; defend home centers

NEVER: Order units you don't control; rely on unconfirmed ally support; leave all home centers undefended; multiple orders per unit; assume sequential

Execute precisely, coordinate carefully, validate thoroughly.
