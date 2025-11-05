# Retreat Phase

Process dislodged units post-Movement. Issue retreat/disband using **ONLY** `possible_orders`.

## Decision Tree

Per unit: (1) Valid retreats in `possible_orders`? NO→disband, YES→evaluate; (2) Priority: supply center>tactical flexibility>front line>safety; (3) RETREAT: defends centers/rejoins front/units≤centers. DISBAND: surplus (units>centers), trapped, enemy destination.

## Syntax
```
[Unit] [Location] R [Destination] | [Unit] [Location] D
```

## Rules

**NEVER:** Attacker origin, occupied province (Movement start), contested (stand-off), wrong terrain (A→sea, F→inland), multiple orders/unit, orders outside `possible_orders`, omit dislodged.

**ALWAYS:** 1 order/unit, use only `possible_orders`, check unit/center balance, return `{"orders": ["order1", "order2"]}`.

## Example: Surplus

**Russia:** 7 units, 5 centers (2 surplus). A WAR dislodged (UKR threatened, LVN isolated). F SEV dislodged (ARM available).

```json
{"orders": ["A WAR D", "F SEV R ARM"]}
```

<reasoning>
7v5→2 disbands needed. A WAR poor retreats→disband. F SEV→ARM keeps Black Sea naval. Choose disbands vs random Adjustment.
</reasoning>
