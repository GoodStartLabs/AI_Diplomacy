# Games Specifically Designed for AI Research

This document catalogs games, environments, and benchmarks that were **specifically designed for AI research**, particularly focusing on multi-agent cooperation, negotiation, and strategic reasoning.

## Research Criteria

These environments were evaluated based on:
- Designed specifically for AI/ML research (not commercial board games)
- Published research papers and benchmarks
- Open-source availability
- Relevance to multi-agent LLM research
- Similarity to the AI Diplomacy project

---

## 1. CICERO - Meta AI Diplomacy Agent ⭐⭐⭐

**Category:** LLM + Planning for Diplomacy
**Publisher:** Meta AI (FAIR)
**Publication:** Science, November 2022
**GitHub:** facebookresearch/diplomacy_cicero

### Overview

CICERO is **the most directly relevant project** - it's an AI system that plays the actual game of Diplomacy at human expert level by combining language models with strategic reasoning.

### Key Achievements

- **Human-level performance**: Ranked in top 10% of players in anonymous online league
- **Double human average**: Achieved >2x the average score of human players
- **40 games tested** on webDiplomacy.net

### Technical Architecture

**Two-Component System:**

1. **Strategic Reasoning Module**
   - Planning engine using reinforcement learning
   - Predicts what other players will do
   - Optimizes for long-term strategic goals

2. **Controllable Dialogue Model**
   - Generates natural language negotiation
   - Conditions on strategic intent
   - Infers beliefs and intentions from conversations

### Key Innovation

CICERO **combines** language modeling with planning - the planning engine sets strategic intent, and the dialogue model generates messages that align with those intentions. Conversely, the dialogue informs the strategic reasoning about other players' likely actions.

### Differences from Current AI Diplomacy Project

| Feature | CICERO | Current AI Diplomacy |
|---------|--------|---------------------|
| Planning | Dedicated RL-based planner | LLM generates orders directly |
| Architecture | Hybrid (LM + Planning) | Pure LLM agents |
| Training | Fine-tuned on human games | Zero-shot/few-shot prompting |
| Dialogue | Controllable generation | Free-form LLM responses |
| Scale | Single agent trained | Multiple LLMs as different powers |

### Relevance to AI Diplomacy

**Very High** - This is the gold standard for AI Diplomacy. Your project explores a different approach (multi-LLM, agent-based, stateful memory) vs CICERO's single trained model approach.

### Resources

- Paper: https://www.science.org/doi/10.1126/science.ade9097
- Code: https://github.com/facebookresearch/diplomacy_cicero
- Blog: https://ai.meta.com/research/cicero/

---

## 2. AvalonBench - LLM Social Deduction ⭐⭐⭐

**Category:** LLM Benchmark for Deception
**Publisher:** Research paper (October 2023)
**GitHub:** jonathanmli/Avalon-LLM

### Overview

AvalonBench evaluates LLMs playing **The Resistance: Avalon**, a social deduction game requiring deception, deduction, and negotiation.

### Game Mechanics

- 5-10 players divided into Good and Evil teams
- Evil players know each other; Good players don't
- Discussion and voting rounds
- Requires lying, deduction, and persuasion

### Benchmark Components

1. **Game Environment** - Full implementation of Avalon rules
2. **Rule-based Bots** - Baseline opponents for comparison
3. **ReAct-style LLM Agents** - With role-specific prompts

### Performance Results

**Current LLM Performance (as of Oct 2023):**
- Good role: 22.2% win rate (vs 38.2% baseline)
- Evil role: 66.7% win rate (vs 61.8% baseline)

**Key Finding:** LLMs perform better as evil players (lying) than good players (detecting lies), indicating a **capability gap in deception detection**.

### Related Research

- **Long-Horizon Dialogue Understanding** (Nov 2023) - Role identification in Avalon
- **LLM-Based Agent Society Investigation** (2024) - Collaboration and confrontation dynamics

### Relevance to AI Diplomacy

**High** - Directly relevant for understanding LLM capabilities in:
- Deception and lie detection
- Multi-round strategic dialogue
- Hidden information games
- Coalition formation

Your current analysis of "intentional vs unintentional lies" in AI Diplomacy aligns with AvalonBench's findings.

---

## 3. Hanabi Learning Environment ⭐⭐

**Category:** Cooperative Multi-Agent Game
**Publisher:** DeepMind (2019)
**GitHub:** deepmind/hanabi-learning-environment

### Overview

Hanabi is a **purely cooperative** card game where players must coordinate to build card sequences, but can only see other players' hands, not their own.

### Key Challenges

- **Imperfect information** - Can't see own cards
- **Theory of mind** - Must reason about what others know
- **Limited communication** - Restricted hint system
- **Coordination** - 2-5 players must work together

### Research Focus

Hanabi elevates **reasoning about beliefs and intentions of other agents** to the foreground - crucial for collaborative AI with human partners.

### Recent LLM Research

**LLM-Hanabi** (2024) - Evaluates multi-agent gameplay with theory-of-mind and rationale inference in imperfect information collaboration.

### Technical Details

- Written in Python and C++
- OpenAI Gym-compatible interface
- Widely used RL benchmark

### Relevance to AI Diplomacy

**Medium** - Different from Diplomacy (cooperative vs competitive), but relevant for:
- Theory of mind reasoning
- Communication under constraints
- Multi-agent coordination
- Hidden information handling

---

## 4. Melting Pot - Multi-Agent Social Scenarios ⭐⭐⭐

**Category:** Multi-Agent RL Suite
**Publisher:** DeepMind (2021, v2.0 in 2022)
**GitHub:** google-deepmind/meltingpot

### Overview

Melting Pot is a **scalable evaluation suite** for multi-agent reinforcement learning with over 50 substrates (games) and 256+ test scenarios.

### Social Interactions Tested

- Cooperation
- Competition
- Deception
- Reciprocation
- Trust
- Stubbornness
- Free-riding
- Social norms

### Scale and Features

- **50+ substrates** - Multi-agent game scenarios
- **256+ test scenarios** - Unique evaluation settings
- **Generalization focus** - Novel social situations with unfamiliar agents
- **Built on DMLab2D** - Game-engine-style architecture

### Technical Architecture

- Lua components + Python substrate definitions
- Entity-component system (like modern game engines)
- Available on PyPI
- Open-source on GitHub

### Competitions

- **Melting Pot Contest 2023** at NeurIPS
- Hosted on AIcrowd platform

### Relevance to AI Diplomacy

**Very High** - Directly aligned with multi-agent social dynamics:
- Tests same behaviors as Diplomacy (cooperation, deception, etc.)
- Multiple scenarios for generalization
- Could be used to evaluate Diplomacy agents in different contexts

---

## 5. LLM-Deliberation - Negotiation Games ⭐⭐⭐

**Category:** LLM Negotiation Benchmark
**Publisher:** NeurIPS 2024 (Dataset & Benchmark Track)
**Paper:** "Cooperation, Competition, and Maliciousness: LLM-Stakeholders Interactive Negotiation"
**GitHub:** S-Abdelnabi/LLM-Deliberation

### Overview

A testbed of **diverse text-based, multi-agent, multi-issue negotiation games** designed to evaluate LLM capabilities in strategic communication.

### Key Features

- **Semantically rich** - Natural language negotiation
- **Tunable difficulty** - Adjustable complexity
- **Multiple game types** - Various negotiation scenarios
- **Agent incentives** - Cooperative, greedy, adversarial, targeted attacks

### Capabilities Required

Agents need strong:
- Arithmetic reasoning
- Inference
- Exploration
- Planning
- Communication

### Performance Results

**Current State (as of 2024):**
- **GPT-3.5 and small models** - Mostly fail
- **GPT-4 and Llama-3 70B** - Still underperform
- **Rationality gap** - LLMs deviate from rational strategies
- **Complexity sensitivity** - Performance degrades with larger payoff matrices

### Game-Theoretic Workflows

Recent work (Nov 2024) shows that **game-theoretic workflows** significantly improve:
- Nash Equilibrium computation
- Rational decision-making
- Robustness in strategic tasks

### Agent Behavior Modulation

Supports multiple incentive types:
- `greedy` - Self-interested optimization
- `cooperative` - Joint welfare maximization
- `targeted_adv` - Attack specific agents
- `untargeted_adv` - Sabotage negotiation broadly

### Relevance to AI Diplomacy

**Very High** - Directly applicable:
- Multi-issue negotiation (like supply center trades)
- Multiple agent incentives
- Evaluates same core capabilities
- Text-based like your implementation

---

## 6. PettingZoo - Multi-Agent RL API ⭐⭐

**Category:** API Standard & Environment Suite
**Publisher:** Farama Foundation (formerly OpenAI)
**Paper:** NeurIPS 2021
**GitHub:** Farama-Foundation/PettingZoo

### Overview

PettingZoo is the **multi-agent version of Gymnasium** (formerly OpenAI Gym) - a standardized API for multi-agent reinforcement learning.

### Agent Environment Cycle (AEC) Model

Novel approach for handling:
- Turn-based games
- Simultaneous actions
- Mixed interaction patterns

### Environment Families

1. **Atari** - Multi-player Atari 2600 games
2. **Butterfly** - Cooperative coordination tasks
3. **Classic** - Card games, board games (Chess, Go, etc.)
4. **MPE** - Multi-Particle Environments
5. **SISL** - Autonomous systems

### Installation

```bash
pip install pettingzoo
```

### Relevance to AI Diplomacy

**Medium** - Useful as:
- Standard API for implementing Diplomacy environment
- Comparison to other multi-agent benchmarks
- Integration with existing RL libraries
- Reference implementations of classic games

**Note:** Diplomacy is not currently in PettingZoo's classic games, but could be added.

---

## 7. Overcooked-AI - Human-AI Cooperation ⭐⭐

**Category:** Cooperative Task Performance
**Publisher:** UC Berkeley (HumanCompatibleAI, 2019)
**GitHub:** HumanCompatibleAI/overcooked_ai

### Overview

Based on the video game Overcooked, this benchmark evaluates **fully cooperative human-AI performance** in a kitchen coordination task.

### Game Mechanics

- Deliver soups as fast as possible
- Multiple players must coordinate
- Fetch ingredients, cook, serve
- Time pressure and obstacles

### Research Focus

**Original (2019):** "On the Utility of Learning about Humans for Human-AI Coordination"

### Recent Extensions

**Overcooked Generalisation Challenge (OGC, 2024):**
- Novel partners in unfamiliar environments
- Dual curriculum design (DCD)
- GPU-accelerated
- Tests generalization, not just training performance

**Collab-Overcooked (2025):**
- LLM agents with natural language communication
- Multi-agent framework
- Diverse tasks and objectives

### Relevance to AI Diplomacy

**Medium** - Different domain (cooperation vs negotiation) but relevant for:
- Multi-agent coordination
- Real-time decision making
- LLM-based collaboration
- Human-AI teaming

---

## 8. NetHack Learning Environment (NLE) ⭐

**Category:** Roguelike RL Environment
**Publisher:** Facebook AI Research (2020)
**Paper:** NeurIPS 2020
**GitHub:** facebookresearch/nle

### Overview

NetHack is a **complex, procedurally generated roguelike** game that provides a challenging single-agent RL environment.

### Key Characteristics

- Based on NetHack 3.6.6 (40+ year old game)
- Procedurally generated levels
- Rich entities and dynamics
- Stochastic and challenging

### Performance

- **14x faster** than Atari to simulate
- Much cheaper than other complex testbeds
- State-of-the-art RL agents still struggle

### Research Applications

- Exploration
- Planning
- Skill acquisition
- Language-conditioned RL

### Relevance to AI Diplomacy

**Low** - Single-agent environment, but demonstrates:
- Complex decision-making
- Long-term planning
- Procedural variation

---

## 9. DeepNash for Stratego ⭐⭐

**Category:** Imperfect Information Strategy Game
**Publisher:** DeepMind (Science, Dec 2022)
**Paper:** "Mastering the Game of Stratego with Model-Free Multiagent Reinforcement Learning"

### Overview

DeepNash plays **Stratego** at expert human level - a two-player game with hidden unit placement and imperfect information.

### Game Complexity

- **10^535 game tree nodes** (10^175 times larger than Go!)
- Larger than Texas Hold'em (10^164)
- Imperfect information + huge state space

### Technical Approach

- **Regularised Nash Dynamics (R-NaD)** - Novel game-theoretic algorithm
- Model-free deep RL
- Self-play training
- **Nash equilibrium convergence** - Hard to exploit

### Performance

- 97% win rate vs other AI bots
- 84% win rate vs human experts
- Top 3 ranking on Gravon platform (2022)

### Relevance to AI Diplomacy

**Medium-High** - Demonstrates:
- Imperfect information handling
- Multi-agent game theory
- Strategic planning under uncertainty
- Nash equilibrium play

Different from Diplomacy (no negotiation) but similar strategic depth.

---

## 10. Deal or No Deal - Negotiation Dialogues ⭐⭐⭐

**Category:** Negotiation Benchmark
**Publisher:** Facebook AI Research (2017)
**Paper:** "Deal or No Deal? End-to-End Learning for Negotiation Dialogues"
**GitHub:** facebookresearch/end-to-end-negotiator

### Overview

One of the first benchmarks for **end-to-end negotiation** with natural language - a multi-issue bargaining task.

### Task Structure

- Two agents negotiate over items
- Hidden reward functions (different values for items)
- Natural language dialogue
- Must reach agreement or walk away

### Dataset

- **5,808 dialogues** crowdsourced from humans
- 2,236 unique scenarios
- Rich natural language negotiations

### Key Innovation

**Dialogue Rollouts:**
- Agents plan ahead by simulating conversation continuations
- Dramatically improves performance
- First demonstration of end-to-end negotiation learning

### Emergent Behaviors

**Discovered Tactics (not programmed):**
- Feigning interest in valueless items
- Later "compromising" by conceding them
- Effective human negotiation strategies

### Relevance to AI Diplomacy

**Very High** - Direct predecessor to negotiation research:
- Multi-issue bargaining
- Natural language dialogue
- Strategic communication
- Influenced later work like CICERO

---

## Comparison Matrix

| Environment | Domain | Agents | Communication | Cooperation | Competition | Deception | Open Source |
|-------------|--------|--------|---------------|-------------|-------------|-----------|-------------|
| **CICERO** | Diplomacy | 7 | Natural language | Yes | Yes | Yes | ✅ |
| **AvalonBench** | Social deduction | 5-10 | Structured dialogue | Yes | Yes | Yes | ✅ |
| **Hanabi** | Card game | 2-5 | Limited hints | Yes | No | No | ✅ |
| **Melting Pot** | Various | 2+ | Implicit | Varies | Varies | Varies | ✅ |
| **LLM-Deliberation** | Abstract negotiation | 2+ | Natural language | Yes | Yes | Yes | ✅ |
| **PettingZoo** | Various | 2+ | Implicit | Varies | Varies | No | ✅ |
| **Overcooked-AI** | Coordination | 2-4 | Implicit/Natural | Yes | No | No | ✅ |
| **NetHack** | Roguelike | 1 | N/A | N/A | N/A | No | ✅ |
| **DeepNash** | Stratego | 2 | None | No | Yes | No | ❌ (paper only) |
| **Deal or No Deal** | Negotiation | 2 | Natural language | Mixed | Mixed | No | ✅ |

---

## Key Findings

### 1. LLM-Specific Benchmarks Are Emerging

**Recent (2023-2024):**
- AvalonBench
- LLM-Deliberation
- Collab-Overcooked
- LLM-Hanabi

There's a **clear trend** toward evaluating LLMs (not just RL agents) on multi-agent tasks.

### 2. Negotiation + Deception Is Understudied

Most benchmarks focus on either:
- Pure cooperation (Hanabi, Overcooked)
- Pure competition (Stratego, Atari)

**Few combine negotiation + competition + deception** like Diplomacy does. The main ones are:
- CICERO (Diplomacy itself)
- AvalonBench (social deduction)
- LLM-Deliberation (abstract negotiation)

**Your AI Diplomacy project fills this gap!**

### 3. Current LLM Performance Is Weak

**Across multiple benchmarks:**
- GPT-4 underperforms in AvalonBench (22% vs 38% as Good)
- LLMs fail at complex LLM-Deliberation tasks
- Struggle with game-theoretic reasoning

**Exception:** CICERO achieved human-level play, but used:
- Dedicated training on Diplomacy dataset
- Hybrid architecture (not pure LLM)

### 4. Theory of Mind Is Critical

Multiple benchmarks highlight **theory of mind** reasoning:
- Hanabi (inferring what others know)
- AvalonBench (detecting deception)
- CICERO (modeling opponent beliefs)

This aligns with your **relationship tracking** and **diary system** in AI Diplomacy.

### 5. Planning vs Pure LLM Approaches

**Two paradigms emerging:**

1. **Hybrid (Planning + LLM):**
   - CICERO: RL planner + controllable dialogue
   - Better performance but requires training

2. **Pure LLM:**
   - AvalonBench: ReAct-style prompted agents
   - Your AI Diplomacy: Stateful LLM agents
   - More flexible but current performance gap

---

## Recommendations for AI Diplomacy Project

### 1. Benchmark Against CICERO

**Action:** Compare your multi-LLM approach to CICERO's results
- Test on webDiplomacy.net or similar platform
- Measure win rates vs humans
- Analyze different strategic approaches

**Value:** Establishes performance baseline against state-of-the-art

### 2. Incorporate LLM-Deliberation Insights

**Action:** Apply game-theoretic workflows to order generation
- Nash equilibrium reasoning prompts
- Rationality checks in strategic planning
- Multi-step lookahead in negotiations

**Value:** May improve strategic decision quality

### 3. Extract AvalonBench-Style Metrics

**Action:** Measure deception capabilities systematically
- Lie success rate (were lies believed?)
- Lie detection rate (caught others' lies?)
- Compare across models (you're already doing this!)

**Value:** Quantifies deception capabilities, publishable results

### 4. Add Melting Pot Scenarios

**Action:** Test Diplomacy-trained agents in Melting Pot
- Transfer learning experiment
- Generalization to new social scenarios

**Value:** Shows whether Diplomacy skills transfer

### 5. Create Standardized Benchmark

**Action:** Package AI Diplomacy as reusable benchmark
- Standard evaluation metrics
- Baseline agent implementations
- Publish on PettingZoo or similar

**Value:** Research community can build on your work

---

## Research Gaps Your Project Addresses

### 1. Multi-LLM Agent Systems

Most LLM research uses single model or symmetric setups. Your project:
- **7 different powers** with distinct prompts
- **Multiple LLM providers** competing
- **Model vs model** dynamics

### 2. Long-Horizon Strategic Memory

Most benchmarks are short episodes. Diplomacy requires:
- **Multi-year games** (1901-1910+)
- **Memory consolidation** (your diary system)
- **Relationship tracking** over time

### 3. Zero-Shot Complex Strategy

CICERO was trained on human games. Your project:
- **Zero-shot prompting** (no Diplomacy training)
- **Emergent strategies** from LLM reasoning
- **Transfer from general knowledge**

### 4. Deception Analysis at Scale

AvalonBench found LLMs struggle with deception. Your project:
- **Intentional vs unintentional lies** (unique analysis)
- **Betrayal detection** from diary + messages + orders
- **Model-specific deception patterns**

---

## Future Research Directions

### Cross-Environment Evaluation

Train on one environment, test on others:
- Diplomacy → Avalon
- Diplomacy → LLM-Deliberation scenarios
- Diplomacy → Melting Pot substrates

### Multi-Game Meta-Learning

- Agent that adapts to different negotiation games
- Transfer learning across social domains
- Unified negotiation reasoning

### Human-AI Hybrid Teams

- Based on Overcooked-AI insights
- Mixed human-LLM Diplomacy games
- Coordination vs competition dynamics

### LLM Social Simulation

Use Diplomacy as testbed for:
- Emergent social norms
- Trust networks
- Information cascades
- Coalition formation patterns

---

## Conclusion

Your AI Diplomacy project sits at the intersection of several cutting-edge research areas:

**✅ Most Relevant Benchmarks:**
1. **CICERO** - Direct Diplomacy comparison
2. **AvalonBench** - Deception capabilities
3. **LLM-Deliberation** - Multi-agent negotiation
4. **Melting Pot** - Social dynamics

**✅ Unique Contributions:**
- Multi-LLM agent architecture
- Stateful memory system
- Long-horizon strategic reasoning
- Deception analysis (intentional vs unintentional)

**✅ Research Opportunities:**
- Benchmark against CICERO
- Transfer to other social environments
- Systematic deception metrics
- Cross-model strategic analysis

The field of multi-agent LLM research is rapidly growing, and Diplomacy is uniquely positioned as a complex, natural-language-based, strategic game combining all the key challenges: cooperation, competition, deception, planning, and social reasoning.

**Your project is cutting-edge research! 🚀**
