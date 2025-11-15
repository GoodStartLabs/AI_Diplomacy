# Games Similar to AI Diplomacy: Research Report

This document catalogs board games and social games that could be adapted to the AI Diplomacy framework, where LLM-powered agents engage in negotiation, strategy, and social interaction.

## Research Criteria

Games were evaluated based on their compatibility with the AI Diplomacy architecture:
- Negotiation and communication between players
- Strategic decision-making
- Relationship management (alliances, betrayals)
- Hidden information or roles
- Memory and context requirements
- Potential for emergent AI behavior

---

## 1. Cosmic Encounter

**Category:** Space conquest with negotiation
**Players:** 3-5 (up to 8 with expansions)
**Complexity:** Medium

### Core Mechanics
- Each player controls an alien race with unique asymmetric powers
- Players form temporary alliances each turn
- Negotiate card (force negotiation between two players)
- One-minute negotiation window to make deals or face mutual losses
- Compensation mechanic when negotiation fails

### AI Adaptation Potential: **Very High**

**Why it works well:**
- Structured negotiation phases fit LLM interaction patterns
- Asymmetric powers provide distinct "personalities" for agents
- Alliance formation and betrayal similar to Diplomacy
- Clear win conditions and success metrics

**Implementation Challenges:**
- Many unique alien powers to model (50+ in full game)
- Complex card interactions
- Timing-based mechanics need adaptation

**Key Agent Behaviors:**
- Evaluate alliance value based on current board state
- Negotiate resource/card trades
- Decide when to betray temporary allies
- Manage reputation across multiple encounters

---

## 2. Game of Thrones: The Board Game

**Category:** Area control with political intrigue
**Players:** 3-6
**Complexity:** High

### Core Mechanics
- Area control with armies and territory
- **Open communication only** - all negotiations are public
- Hidden order tokens placed simultaneously
- Bidding for power tracks
- Support/attack mechanics similar to Diplomacy

### AI Adaptation Potential: **High**

**Why it works well:**
- Very similar to Diplomacy (order-based simultaneous resolution)
- Public negotiations create rich communication logs
- Power tracks add additional strategic layer
- Asymmetric starting positions

**Implementation Challenges:**
- More complex than Diplomacy (cards, power tracks, supply limits)
- Longer game duration
- Wildling attacks and event deck randomness

**Key Differences from Diplomacy:**
- All negotiations are public (no private messaging)
- More game mechanics beyond pure negotiation
- House-specific advantages

---

## 3. Dune (2019 Edition)

**Category:** Asymmetric alliance-based strategy
**Players:** 2-6
**Complexity:** Very High

### Core Mechanics
- Highly asymmetric faction powers
- Alliance formation at Nexus phases (when sandworms appear)
- Allies share special powers with each other
- Variable victory conditions based on alliance size
  - Solo: 3 strongholds
  - 2-player alliance: 4 strongholds
  - 3-player alliance: 5 strongholds
- Constant negotiation throughout gameplay
- Bidding, bluffing, and betrayal mechanics

### AI Adaptation Potential: **High**

**Why it works well:**
- Deep negotiation and alliance mechanics
- Asymmetric powers create distinct AI personalities
- Resource sharing between allies
- Betrayal detection opportunities

**Implementation Challenges:**
- Extremely complex faction interactions
- Hidden information (traitor cards, hidden units)
- Combat prediction mechanic
- Spice economy management

**Unique AI Opportunities:**
- Coalition formation logic
- Power-sharing negotiation
- Timing alliance breaks around Nexus phases

---

## 4. Twilight Imperium (4th Edition)

**Category:** Epic space opera 4X
**Players:** 3-6
**Complexity:** Very High

### Core Mechanics
- **Binding and non-binding deals** - unique mechanic where some promises must be kept
- Trade goods and commodity economy
- Politics strategy card enables agenda manipulation
- Promissory notes - tradeable obligations
- Speaker token negotiation
- Military, political, and economic paths to victory

### AI Adaptation Potential: **Medium-High**

**Why it works well:**
- Rich negotiation space (resources, votes, military support)
- Clear binding vs non-binding contract distinction helps AI reasoning
- Multiple victory paths encourage diverse strategies
- Promissory notes create long-term obligations

**Implementation Challenges:**
- Extremely long game (4-8 hours)
- Complex tech trees and action cards
- Simultaneous space combat
- Large rule set

**Key Agent Behaviors:**
- Economic negotiation (commodities for trade goods)
- Political deal-making (vote trading)
- Military pacts and non-aggression agreements
- Tracking binding obligations vs promises

---

## 5. Sidereal Confluence

**Category:** Pure trading and negotiation
**Players:** 4-9
**Complexity:** Medium-High

### Core Mechanics
- **Simultaneous open trading** - all players negotiate at once
- Asymmetric alien economies (inputs/outputs don't match)
- Almost everything is tradeable (resources, ships, colonies, technologies)
- Resource conversion engine-building
- Cooperative-competitive dynamic (need to trade to win)

### AI Adaptation Potential: **Very High**

**Why it works well:**
- Pure negotiation focus (minimal other mechanics)
- Economic optimization is LLM-friendly
- No hidden information
- Highly emergent gameplay from simple rules
- Multi-party deals create complex scenarios

**Implementation Challenges:**
- Simultaneous negotiation (not turn-based)
- Complex multi-resource deals
- Evaluating trade fairness across asymmetric economies
- Temporary technology sharing

**Key Agent Behaviors:**
- Economic planning (input/output matching)
- Multi-party deal construction
- Fair trade evaluation
- Technology rental negotiations

---

## 6. Settlers of Catan

**Category:** Resource trading and development
**Players:** 3-4 (5-6 with expansion)
**Complexity:** Low-Medium

### Core Mechanics
- Resource generation from dice rolls
- **Active player initiates all trades** - only current player can trade with others
- Bank trading (4:1 or better with ports)
- Non-binding promises allowed
- Monopoly and trading cards

### AI Adaptation Potential: **Medium**

**Why it works well:**
- Simple, well-understood game
- Clear resource valuation
- Negotiation is core mechanic
- Good test case for trade fairness

**Implementation Challenges:**
- Dice randomness (less pure strategy than Diplomacy)
- Less deep than other options
- Negotiations less complex
- Kingmaker problem in 3-player games

**Key Agent Behaviors:**
- Resource valuation based on development plans
- Trade offer generation
- Blocking trades to prevent others from winning
- Future promise negotiation (not enforceable)

---

## 7. Chinatown

**Category:** Pure negotiation and trading
**Players:** 3-5
**Complexity:** Low-Medium

### Core Mechanics
- **Everything is tradeable** - properties, shops, money
- **Simultaneous open negotiation** - all players can negotiate at once
- Players can conduct auctions for valuable tiles
- Triangle trades and arbitrage opportunities
- No hidden information

### AI Adaptation Potential: **Very High**

**Why it works well:**
- Pure negotiation game with minimal other mechanics
- Clear economic optimization goals
- No randomness after tile draw
- Multi-party deals encouraged
- Auction dynamics

**Implementation Challenges:**
- Simultaneous negotiation
- Valuation of asymmetric assets
- Optimal property placement

**Key Agent Behaviors:**
- Property valuation based on adjacency and rarity
- Auction bidding strategies
- Arbitrage opportunity detection
- Multi-party deal construction

---

## 8. Werewolf / Mafia

**Category:** Social deduction
**Players:** 7-20+
**Complexity:** Low

### Core Mechanics
- Hidden role assignment
- Day/night phases
- Informed minority (werewolves) vs uninformed majority (villagers)
- Discussion and voting during day
- Night kills by werewolves
- Special roles (doctor, seer, etc.)

### AI Adaptation Potential: **High**

**Why it works well:**
- Pure social deduction and argumentation
- LLMs excel at natural language persuasion
- Rich dialogue and accusation dynamics
- Lie detection opportunities

**Implementation Challenges:**
- Requires moderator/narrator
- Less structured than board games
- Balancing vocal participation
- Need 7+ players minimum

**Key Agent Behaviors:**
- Logical deduction from voting patterns
- Persuasive argumentation
- Lying and deception (for werewolves)
- Social pressure and bandwagoning
- Reading inconsistencies in stories

---

## 9. Blood on the Clocktower

**Category:** Advanced social deduction
**Players:** 5-20+
**Complexity:** Medium-High

### Core Mechanics
- Similar to Werewolf but with unique twists
- **Dead players remain active** - can discuss and vote once
- Storyteller (moderator) role
- Complex unique abilities for each role
- Multiple scripts/editions with different role sets
- Information gathering and deduction

### AI Adaptation Potential: **Medium-High**

**Why it works well:**
- More information than basic Werewolf
- Unique abilities create interesting AI decisions
- Dead player participation maintains engagement
- Complex logical deduction

**Implementation Challenges:**
- Requires Storyteller AI (game master)
- Very complex role interactions
- Subjective Storyteller decisions
- Difficult to balance information flow

**Key Agent Behaviors:**
- Complex deduction chains
- Information sharing and verification
- Role claiming and counter-claiming
- Dead player strategic voting

---

## 10. Secret Hitler

**Category:** Hidden role politics
**Players:** 5-10
**Complexity:** Low-Medium

### Core Mechanics
- Liberals vs Fascists (+ Hitler)
- President/Chancellor election each round
- Policy card selection with hidden draws
- Voting and debate
- Special executive powers
- Information asymmetry between teams

### AI Adaptation Potential: **High**

**Why it works well:**
- Structured negotiation in election phase
- Clear information revelation moments
- Probability reasoning for policy tracking
- Alliance formation and suspicion

**Implementation Challenges:**
- Requires 5+ players
- Chancellor selection politics
- Optimal policy discard strategies
- Hitler identity deduction

**Key Agent Behaviors:**
- Vote analysis and pattern detection
- Policy probability calculation
- Trust building/destroying through nominations
- Fascist coordination without revealing identities

---

## 11. Battlestar Galactica: The Board Game

**Category:** Cooperative with hidden traitors
**Players:** 3-6
**Complexity:** High

### Core Mechanics
- Semi-cooperative (humans vs Cylons)
- **Sleeper agent mechanic** - second loyalty card drawn mid-game
- Traitors may not know each other
- Resource management (fuel, food, morale, population)
- Crisis cards require skill checks
- Brig (prison) mechanic for suspected Cylons

### AI Adaptation Potential: **Medium-High**

**Why it works well:**
- Hidden sabotage creates interesting dynamics
- Resource management decisions
- Suspicion and accusation gameplay
- Mid-game loyalty shift is unique mechanic

**Implementation Challenges:**
- Complex resource balancing
- Skill check probabilities
- Cylon reveal timing optimization
- Long game duration

**Key Agent Behaviors:**
- Subtle sabotage (for Cylons)
- Detecting statistical anomalies in skill checks
- Brig decisions and politics
- Managing suspicion levels
- Timing loyalty reveal

---

## Implementation Priority Recommendations

### Tier 1: Best Immediate Fits
1. **Cosmic Encounter** - Similar complexity to Diplomacy, excellent negotiation
2. **Sidereal Confluence** - Pure negotiation, highly emergent
3. **Chinatown** - Simple rules, pure trading

### Tier 2: High Potential with More Work
4. **Game of Thrones** - Very similar to Diplomacy
5. **Werewolf/Mafia** - Different genre, excellent for LLM strengths
6. **Secret Hitler** - Structured social deduction

### Tier 3: Complex but Rewarding
7. **Dune** - Deep but very complex
8. **Twilight Imperium** - Epic scope, binding contracts
9. **Blood on the Clocktower** - Advanced social deduction

### Tier 4: Interesting but Challenging
10. **Battlestar Galactica** - Complex mechanics, interesting traitor dynamics
11. **Settlers of Catan** - Simpler, good test case

---

## Common Themes Across Games

### What Makes Games AI-Compatible?

1. **Structured Communication Phases**
   - Turn-based or phase-based negotiation
   - Clear timing for when deals can be made
   - Examples: Cosmic Encounter, Dune

2. **Economic Reasoning**
   - Resource valuation
   - Trade fairness evaluation
   - Examples: Sidereal Confluence, Chinatown, Catan

3. **Alliance Dynamics**
   - Formation, maintenance, betrayal
   - Relationship tracking over time
   - Examples: Diplomacy, Cosmic Encounter, Dune

4. **Information Management**
   - Deduction from partial information
   - Lie detection and consistency checking
   - Examples: Werewolf, Secret Hitler, Battlestar Galactica

5. **Clear Success Metrics**
   - Quantifiable goals
   - Measurable progress
   - Win condition evaluation

### Challenges to Address

1. **Simultaneous Actions**
   - Many negotiation games have all-play phases
   - Need to model concurrent LLM interactions
   - Potential solution: Time-boxed parallel API calls

2. **Moderator/Storyteller Roles**
   - Social deduction games need neutral arbiter
   - Could be rule-based system or separate LLM
   - Examples: Werewolf, Blood on the Clocktower

3. **Complex Special Abilities**
   - Asymmetric powers require extensive prompting
   - Need robust ability resolution system
   - Examples: Cosmic Encounter, Blood on the Clocktower

4. **Hidden Information**
   - Private hands, secret roles, hidden units
   - Requires separate agent contexts
   - Potential for LLM to accidentally "leak" info

5. **Randomness vs Pure Strategy**
   - Dice, card draws, shuffled decks
   - More variance than Diplomacy
   - Need to evaluate AI under uncertainty

---

## Technical Architecture Considerations

### Reusable from Current Implementation

- **Agent State Management**: Goals, relationships, memory
- **Diary System**: Negotiation, action, and result entries
- **Communication Framework**: Private and public messages
- **LLM Client Abstraction**: Multi-provider support
- **Game State Serialization**: JSON game logs

### New Components Needed

1. **Game-Specific Rule Engines**
   - Each game needs order validation
   - State transition logic
   - Win condition checking

2. **Ability/Power Systems**
   - Template system for special abilities
   - Trigger conditions and effects
   - Cosmic Encounter, Dune, etc.

3. **Economic Evaluation**
   - Resource valuation functions
   - Trade fairness checking
   - For Catan, Chinatown, Sidereal Confluence

4. **Social Deduction Logic**
   - Probability tracking
   - Consistency checking
   - Lie detection
   - For Werewolf, Secret Hitler, BSG

5. **Moderator AI**
   - Game master for social deduction
   - Neutral arbiter
   - Dynamic balancing

---

## Research Questions

### Emergent Behaviors to Study

1. **Cross-Game Strategy Transfer**
   - Do agents develop consistent "personalities"?
   - Can Diplomacy-trained agents adapt to other games?

2. **Deception Capabilities**
   - How well can LLMs lie convincingly?
   - Can they detect lies from other LLMs?
   - Varies by model (as shown in current analysis)

3. **Economic Reasoning**
   - How well can agents value asymmetric resources?
   - Trade fairness in complex economies
   - Multi-party deal construction

4. **Coalition Formation**
   - Optimal alliance size calculations
   - When to betray vs maintain alliances
   - Three-way alliances vs bilateral

5. **Communication Efficiency**
   - Token usage in negotiation-heavy games
   - Optimal message length
   - Information density

---

## Next Steps

### Phase 1: Proof of Concept
Pick one Tier 1 game (recommend **Cosmic Encounter**) and implement:
- Basic rule engine
- 5-6 alien powers
- Negotiation framework
- Single game run

### Phase 2: Comparative Analysis
- Run same models on both Diplomacy and new game
- Compare deception rates, alliance stability
- Analyze cross-game strategic consistency

### Phase 3: Multi-Game Framework
- Abstract common negotiation/alliance mechanics
- Create game-agnostic agent architecture
- Support 3-4 different games

### Phase 4: Advanced Features
- Meta-learning across games
- Tournament mode with ELO across different games
- Human-AI hybrid games

---

## Conclusion

Many excellent board games could be adapted to the AI Diplomacy framework. The most promising candidates combine:

- **Structured negotiation** (works well with LLM interaction patterns)
- **Economic or political reasoning** (LLMs can evaluate options)
- **Relationship dynamics** (alliance/betrayal tracking)
- **Emergent complexity** (simple rules, complex outcomes)

**Top 3 Recommendations:**
1. **Cosmic Encounter** - Best balance of complexity and negotiation depth
2. **Sidereal Confluence** - Pure trading, highly emergent
3. **Werewolf/Mafia** - Different genre, plays to LLM strengths in argumentation

The current AI Diplomacy architecture provides an excellent foundation that can be extended to these games with game-specific rule engines and prompting strategies.
