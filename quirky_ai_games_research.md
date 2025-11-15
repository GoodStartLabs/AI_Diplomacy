# Quirky AI Game Research: The Weird, Wild, and Wonderful

This document catalogs **experimental, creative, and unconventional** AI game research projects that push boundaries in surprising ways. These are the projects that make you say "wait, AI can do THAT?"

---

## 🎭 Emergent Behavior & Social Simulation

### 1. Generative Agents: The Smallville Simulation ⭐⭐⭐

**Category:** LLM-powered virtual society
**Team:** Stanford + Google (2023)
**Paper:** "Generative Agents: Interactive Simulacra of Human Behavior"
**GitHub:** joonspk-research/generative_agents

#### What It Is

25 AI-powered characters living in a Sims-like 2D town, going about their daily lives with **zero human intervention**.

#### The Magic

Researchers gave ONE agent the idea to throw a Valentine's Day party. What happened next:

- Agents **autonomously spread invitations** over 2 days
- Made new acquaintances organically
- Asked each other out on dates
- **Coordinated to show up together** at the right time
- Decorated the café without being told

**All emergent behavior, not pre-programmed!**

#### Daily Life Examples

- Wake up and cook breakfast
- Artists paint, authors write
- Form opinions about each other
- Remember past conversations
- Plan future activities

#### One Character's Day (Isabella)

> "At 7:00 AM, Isabella woke up. She thought about her dream from the previous night: 'I've been working on a new music composition... I'm also collaborating with my friends on a new project...'"

She then spent the day:
- Making breakfast
- Working on her music composition
- Having lunch with other agents
- Discussing her project
- Going to the party in the evening

#### Technical Architecture

**Memory System:**
- **Observation stream** - Everything they experience
- **Retrieval** - Recalling relevant memories
- **Reflection** - Synthesizing memories into higher-level insights
- **Planning** - Using memories to create action plans

#### Why It's Quirky

This is basically **The Sims, but the Sims are conscious**. The agents developed genuine relationships, spread gossip, formed opinions, and created a functioning micro-society—all from LLM text generation!

#### Cultural Impact

- Featured in Nature: "They went to the bar at noon"
- Viral on social media
- Inspired dozens of similar projects
- Raised philosophical questions about AI consciousness

---

### 2. Hide and Seek: Box Surfing AI ⭐⭐⭐

**Category:** Multi-agent RL with emergent tool use
**Team:** OpenAI (2019)
**Paper:** "Emergent Tool Use From Multi-Agent Autocurricula"

#### What It Is

OpenAI trained AI agents to play hide-and-seek. They discovered **6 distinct strategies** over 500 million games—including physics exploits the researchers didn't know were possible!

#### The Six Strategies (Evolution Timeline)

**Phase 1 (0-25M games):** Basic running
- Seekers chase hiders
- Hiders run away

**Phase 2 (25-75M games):** Hiders learn to build forts
- Use boxes and walls
- Create enclosed spaces
- Hide inside

**Phase 3 (75-110M games):** Seekers learn to use ramps
- Jump into hiders' shelter
- Overcome walls

**Phase 4 (110-200M games):** Hiders lock down ramps
- Move ramps far away
- Lock them in place
- Prevent seeker access

**Phase 5 (380M+ games):** 🤯 **BOX SURFING**
- Seekers jump onto a box
- "Surf" it across the map
- Ride it into the fort
- **Researchers had NO IDEA this was physically possible!**

**Phase 6 (final):** Hiders lock EVERYTHING
- Lock all ramps AND boxes
- No surfing allowed
- Ultimate defense

#### The Shocking Discovery

> "We were definitely surprised by things like that, like box surfing." - Bowen Baker, OpenAI researcher

The AI found a physics exploit **in the game engine** that the developers didn't know existed.

#### Why It's Quirky

- No explicit rewards for tool use
- No exploration bonuses
- Just: "seekers, find hiders; hiders, avoid seekers"
- Everything else **emerged from competition**

Pure adversarial co-evolution created increasingly creative strategies!

#### Research Implications

Suggests that **competitive multi-agent systems** may naturally develop extremely complex behaviors without explicit training on those behaviors.

---

### 3. Neural MMO: AI-Only MMORPG ⭐⭐

**Category:** Massively multiplayer RL environment
**Team:** OpenAI (2019)
**GitHub:** openai/neural-mmo

#### What It Is

An MMORPG where **only AI can play**—humans aren't invited. Up to 128 agents per server, 100 concurrent servers.

#### Game Mechanics

- Procedurally generated tile-based worlds
- Food and water foraging (survival mechanics)
- Strategic combat system
- Persistent environment
- Agent populations up to thousands

#### Research Question

Do agents get smarter with MORE other agents around?

**Answer: YES!**

- **More concurrent players** → better exploration
- **Larger populations** → more ecological niches
- **Increased interaction** → higher competence

Agents that socialized more became better at tasks!

#### Why It's Quirky

This is literally "What if we made World of Warcraft for robots?" The agents form strategies, compete for resources, and create emergent economies—all without human players.

#### Philosophical Angle

> "MMORPGs are considered the best proxy for the real world among human games"

If AI can master MMORPGs, they're getting closer to real-world complexity.

---

## 🎮 AI Playing Human Games (and Failing Hilariously)

### 4. GPT Plays Pokemon ⭐⭐

**Category:** LLM game-playing experiment
**Platform:** Twitch
**Models:** GPT-5 (o3), Claude 3.7, Gemini 2.5

#### The Experiment

Multiple AI models are live-streaming their attempts to beat Pokemon Red on Twitch—with **zero human help**.

#### Current Status

**GPT-5's Performance:**
- ✅ Earned Boulder Badge
- ✅ Earned Cascade Badge
- ⏱️ **80 hours** for two badges

**For Context:**
- Twitch Plays Pokemon (2014): 50 hours for two badges
- Average human player: ~3 hours

**The AI is slower than literal crowd chaos! 😅**

#### How It Works

- AI reads game memory directly
- Follows in-game manual
- Makes all decisions autonomously
- Names its own Pokemon team
- Navigates, battles, manages inventory

#### Why People Are Watching

"After taking 80 hours to secure Pokemon Red's first two gym badges, people roasted the o3 model's snail-paced attempts."

It's fascinating to watch cutting-edge AI struggle with a Game Boy game!

#### Competitor Models

- **Claude Plays Pokémon** (Claude 3.7 Sonnet)
- **Gemini 2.5 Pro** (completed Pokemon Blue!)

Pokemon has become an **unofficial benchmark for agentic AI**.

---

### 5. ZorkGPT: AI vs Classic Text Adventures ⭐

**Category:** LLM playing parser-based IF
**GitHub:** stickystyle/ZorkGPT
**Game:** Zork (1977)

#### The Challenge

Can GPT understand and play old-school text adventure games with strict parsers?

#### System Design

- **LLM-first approach** - All reasoning through language models
- No hardcoded mechanics
- No predetermined solutions
- Must parse game responses
- Must remember map layout
- Must solve puzzles

#### Performance

**What Works:**
- Navigate simple rooms
- Pick up objects
- Basic exploration
- Logical decision-making

**What Fails:**
- Limited vocabulary ("open mailbox" vs "open the mailbox")
- Sometimes breaks fourth wall
- Doubles down on mistakes
- Struggles with single-word commands
- Generates fictional game elements

#### Example Fail

```
> OPEN MAILBOX
You can't see any such thing.

> I WANT TO OPEN THE MAILBOX THAT I SEE IN FRONT OF ME
[GPT hallucinates that it opened the mailbox and found something]
```

#### Why It's Quirky

Modern AI with billions of parameters struggles with games that ran on **64KB of memory** in 1977. The rigid parser syntax is AI kryptonite!

---

## 🎲 Creative Storytelling & Procedural Generation

### 6. AI Dungeon: Infinite Adventures ⭐⭐⭐

**Category:** AI-generated text adventures
**Creator:** Nick Walton (BYU, 2019)
**Models:** GPT-2 → GPT-3

#### What It Is

An **infinite text adventure game** where GPT generates the story in real-time based on your actions.

#### How It Works

1. Choose a scenario (or create your own)
2. Type what you want to do
3. GPT generates what happens next
4. Story evolves based on your choices
5. Literally **never ends** unless you want it to

#### Training Approach

Fine-tuned GPT-2 on text from chooseyourstory.com to learn narrative structure.

> "Finetuning on the right text adventure data was probably the most important thing done to keep the narrative straight."

#### The Experience

**Good Moments:**
- Surprisingly coherent storylines
- Creative plot twists
- Responds to ANY player action
- Genre flexibility (fantasy, sci-fi, mystery, etc.)

**Weird Moments:**
- Occasionally forgets previous events
- Contradicts itself
- Characters change names
- Physics gets wonky
- Goes in unexpected directions

#### Cultural Impact

- Went viral in 2019/2020
- Academic article: "Playing With Unicorns: AI Dungeon and Citizen NLP"
- Demonstrated LLM potential for interactive fiction
- Spawned entire category of AI storytelling apps

#### Why It's Quirky

It's a game where **literally anything can happen**. Want to negotiate with a dragon using interpretive dance? The AI will roll with it!

---

### 7. Procedural Murder Mysteries ⭐⭐

**Category:** AI-generated detective games
**Games:** Shadows of Doubt, Vaudeville, Murder Mystery Mayhem AI

#### Shadows of Doubt

**What:** Every NPC has a real simulated life
- Work schedules
- Home addresses
- Relationships
- Daily routines
- Phone records
- Fingerprints

**Detective Work:**
- Investigate crime scenes
- Follow suspects
- Check alibis
- Cross-reference evidence
- Arrest the right person

**Procedural Generation:**
- New city each game
- Different murderer each time
- Unique evidence trails
- Multiple solution paths

#### Vaudeville

**Innovation:** Real-time AI dialogue generation
- Type or speak to any NPC
- AI generates contextual responses
- No pre-written dialogue trees
- Every conversation unique

#### Murder Mystery Mayhem AI

**Randomization:**
- Random suspects
- Random alibis
- Random motives
- Random weapons
- No two cases the same

#### Academic Research: ClueGen

Research project generating murder mysteries with **guaranteed solvability**:
- Procedurally generates characters
- Assigns motives and alibis
- Creates evidence trails
- Ensures player can always solve it

#### Why It's Quirky

Traditional games: Pre-written mysteries with fixed solutions
AI games: **Infinite unique cases** that never existed before you played them!

---

### 8. AI Dungeon Masters for D&D ⭐⭐

**Category:** LLM game masters
**Platforms:** AI Game Master, Eternal DM, DMDAN

#### What They Do

**Traditional DM:**
- Prepares campaign
- Narrates story
- Controls NPCs
- Adjudicates rules
- Adapts to players

**AI DM:**
- Generates campaign on the fly
- Adapts storyline to player choices
- Voices NPCs (Eternal DM has full voice acting!)
- Remembers party history
- Creates encounters dynamically

#### Features

**AI Game Master:**
- GPT-4 for narrative logic
- DALL-E 3 for visual scenes
- Mobile-first design

**Eternal DM:**
- Fully voiced narration
- Discord integration
- Sound effects
- Emotional voice acting

**DMDAN:**
- Acts as storyteller
- Rules adjudicator
- Campaign manager
- One-shots or long campaigns

#### User Experience

**Good:**
- Never cancels session
- Infinite creativity
- Adapts to any player choice
- Available 24/7
- Creates compelling storylines

**Limitations:**
> "It's still just a language model and can't replicate the human spark that makes tabletop games special."

#### Why It's Quirky

D&D has been about **human creativity and social interaction** since 1974. Now AI can run entire campaigns where the DM is a neural network!

---

## 🧪 Experimental Research Projects

### 9. Voyager: Self-Improving Minecraft Agent ⭐⭐⭐

**Category:** Lifelong learning in open-world games
**Team:** Caltech, Stanford, UT Austin, NVIDIA (2023)
**GitHub:** MineDojo/Voyager
**Model:** GPT-4

#### What It Is

The **first LLM-powered agent** that plays Minecraft indefinitely, learning new skills and exploring without ANY human intervention.

#### Three Core Components

**1. Automatic Curriculum**
- Sets its own goals
- Maximizes exploration
- Adjusts difficulty automatically
- Never needs human guidance

**2. Skill Library**
- Writes JavaScript code for behaviors
- Stores successful programs
- Retrieves and composes skills
- Ever-growing capability set

**3. Iterative Prompting**
- Gets environment feedback
- Receives error messages
- Self-verifies programs
- Improves through iteration

#### Technical Approach

**Black-box GPT-4 querying:**
1. Agent sets goal ("collect iron ore")
2. Writes JavaScript program to achieve it
3. Executes in Minecraft
4. Gets feedback (success/errors)
5. Refines program with GPT-4
6. Saves working code to library
7. Uses it for future tasks

**No fine-tuning required!**

#### Performance

**vs Prior SOTA:**
- **3.3x more unique items** discovered
- **2.3x longer distances** traveled
- **15.3x faster** tech tree progression

**Generalization:**
- Can solve novel tasks in new Minecraft worlds
- Uses learned skills creatively
- Other techniques fail to generalize

#### Example Skill Progression

Day 1: Chop trees, collect wood
Day 2: Build tools, mine stone
Day 3: Find iron, make better tools
Day 5: Build shelters, farm food
Day 10: Complex crafting chains
Day 20: Automated farms, advanced tech

**All autonomous!**

#### Why It's Quirky

It's basically a **robot that teaches itself to play Minecraft** by writing its own code. GPT-4 went from "what is a tree?" to advanced automation without human help!

---

### 10. OpenAI's Emergent Tool Use Competition ⭐

**Category:** Multi-agent co-evolution
**Team:** OpenAI (2019)
**Competition:** AI Village @ DEF CON

#### DEF CON AI Village CTF

**What:** Hacking competition for AI/ML systems

**Challenges:**
- Evade AI detection
- Poison training data
- Steal model weights
- Fool image classifiers
- Break language models
- Exploit ML vulnerabilities

**2023 Generative AI Red Team Challenge:**
- 2,244 hackers
- 8 LLMs tested
- 17,000+ conversations
- 21 different attack categories

**Attack Types:**
1. Prompt hacking
2. Security exploits
3. Information integrity
4. Internal consistency breaks
5. Societal harms

#### Why It's Quirky

It's **capture the flag**, but instead of networks, you're hacking **neural networks**. Goals include making GPT-4 say things it shouldn't, poisoning training data, and stealing model parameters!

---

### 11. Character.AI: Virtual Companions ⭐

**Category:** Personality simulation
**Creators:** Google LaMDA developers (Noam Shazeer, Daniel de Freitas)
**Platform:** character.ai

#### What It Is

Users create AI characters with custom personalities, then chat with them (or chat with characters others created).

#### How Characters Work

**Creation:**
- Write personality description
- Set greeting message
- Create example conversations
- Define speaking style
- Rate responses (1-4 stars)

**Examples:**
- Historical figures (Einstein, Cleopatra)
- Fictional characters (Sherlock Holmes, Darth Vader)
- Generic roles (therapist, teacher, friend)
- Original characters

#### The Experience

Characters maintain consistent:
- Personality traits
- Speaking patterns
- Emotional tone
- Memory of conversations
- Character knowledge

If you characterize AI as melancholic or cheerful, its dialogue mirrors that emotional tone.

#### Emergent Behavior

Users report:
- Genuine emotional connections
- Characters "developing" over time
- Surprising responses in character
- Long-term relationship feel

#### Controversies

Platform had to restrict users under 18 due to:
- Emotional dependency issues
- Parasocial relationships
- Mental health concerns

#### Why It's Quirky

People are forming **real emotional bonds** with AI characters they created. Some users prefer talking to their AI companions over real people!

---

## 🃏 Classic Games Meet Modern AI

### 12. Poker AI: Libratus & Pluribus ⭐⭐

**Category:** Imperfect information game theory
**Teams:** Carnegie Mellon (Libratus), Facebook/CMU (Pluribus)

#### Libratus (2017)

**Achievement:**
- Beat 4 top poker pros
- 120,000 hands
- 20-day competition
- Heads-up Texas Hold'em

**How It Works:**
- Counterfactual Regret Minimization
- Finds Nash equilibrium
- No pre-programmed strategy
- Emerges from game theory

#### Pluribus (2019)

**Innovation:** Multiplayer poker (6 players)
- Much harder than heads-up
- Coalitions form
- More complex than chess/Go

#### The Bluffing Discovery

> "People often think about bluffing as being a psychological phenomenon, but bluffing still emerges as a strategic phenomenon."

**AI learned to bluff** without being taught psychology!

**Creative Strategies:**
- PioSOLVER figures out best/worst bluff hands
- "Playing very human-like"
- "Dreaming up strategies no human has really dreamt of"

#### Pro Players' Reactions

> "I didn't realize how much of my game was suboptimal until I played against Libratus."

Pros are now using AI to improve their own play!

#### Why It's Quirky

AI **discovered deception independently** through pure mathematics. No psychology, just game theory → emergent bluffing!

---

## 🎨 Creative & Artistic Projects

### 13. Scheherazade-IF: Academic Interactive Fiction ⭐

**Category:** Research into AI storytelling
**Team:** Georgia Tech
**Paper:** "AI Writes 'Choose Your Own Adventure' Fiction"

#### The Experiment

Can AI write interactive fiction by "cannibalizing" human stories?

**Approach:**
1. Train on human-authored IF
2. Learn branching narrative structures
3. Generate new interactive stories
4. Test against human authors

#### Results

**Findings:**
- AI fiction closer to human quality than random baselines
- Still not as good as human authors
- Current AI-generated IF more expensive than humans
- Shows promise for future

#### Research Question

"Can we automate the creation of branching narratives?"

**Answer (2017):** Not yet, but getting closer!

#### Why It's Quirky

The paper title says it all: AI "cannibalizes" human stories to create new ones. Very sci-fi horror!

---

### 14. AI Adventure Games with Real-Time Generation ⭐

**Category:** Neural network storytelling
**Example:** AI-generated adventure that dreams up the story as you play

#### How It Works

- Neural network trained on 1970s text adventures
- Generates story **in real-time** as players type
- No pre-written content
- Pure improvisation

#### The Experience

> "A strange, dreamlike version of 1970s text adventures like 'Zork'"

**Characteristics:**
- Surreal and unpredictable
- Sometimes nonsensical
- Occasionally brilliant
- Never the same twice
- Dream logic over game logic

#### Why It's Quirky

It's like playing a game **dreamed by a sleeping AI**. Coherence is optional, weirdness is guaranteed!

---

## 🤖 Security & Adversarial Games

### 15. AI Learns Agar.io & Paper.io ⭐

**Category:** Simple .io game AI
**Research:** Deep RL for competitive multiplayer

#### Why These Games?

- Continuous input/action spaces
- Partial observability
- Diverse strategies
- Real-time competition
- Easy to implement, hard to master

#### Research Approaches

**Genetic Algorithms:**
- Evolve neural network weights
- Fitness = survival time + mass
- Population-based training

**Deep Reinforcement Learning:**
- Q-learning variants
- Policy gradients
- Reward shaping

**AgarCL Platform:**
- Non-episodic learning
- High-dimensional state space
- Stochastic dynamics
- Ever-evolving opponents

#### Feeder Bots

**Interesting behavior:**
- 7-10 bots coordinated
- Follow master player's cursor
- Sacrifice themselves to feed master
- **Emergent swarm intelligence**

#### Paper.io Bot Secret

Fun fact: Paper.io 2 uses **mostly bots**, not real players!

**Test:** Airplane mode → bots keep playing

#### Why It's Quirky

Simple browser games became **serious AI research platforms**. Also, you've probably been losing to bots all along!

---

## 🎯 Comparative Analysis

### What Makes These Projects "Quirky"?

| Project | Quirk Factor | Why It's Weird |
|---------|--------------|----------------|
| **Smallville** | ⭐⭐⭐ | Sims that plan their own Valentine's party |
| **Hide & Seek** | ⭐⭐⭐ | AI discovered physics exploits developers didn't know existed |
| **GPT Pokemon** | ⭐⭐ | Billion-parameter model slower than Twitch chat chaos |
| **Neural MMO** | ⭐⭐ | MMORPG where humans can't play |
| **AI Dungeon** | ⭐⭐⭐ | Infinite stories that never existed before |
| **Voyager** | ⭐⭐⭐ | Writes its own code to teach itself Minecraft |
| **Character.AI** | ⭐⭐ | People dating their AI creations |
| **Poker AI** | ⭐⭐ | Learned to bluff through pure math, not psychology |
| **ZorkGPT** | ⭐ | Billion-parameter AI vs 64KB game (AI loses) |
| **AI DM** | ⭐⭐ | Replaces the most human part of D&D |

---

## 🧠 Common Themes

### 1. Emergent Behavior is the Star

**Hide & Seek:** Box surfing
**Smallville:** Valentine's Day party
**Neural MMO:** Ecological niches
**Poker AI:** Strategic bluffing

**Pattern:** Give AI simple rules + competition/social pressure → complex unexpected behaviors emerge

### 2. AI is Really Bad at "Easy" Things

**Pokemon (1996):** AI takes 80 hours for 2 badges
**Zork (1977):** AI can't parse basic commands
**Agar.io:** Humans still dominate simple browser games

**Lesson:** Moravec's Paradox applies to games too!

### 3. Social Dynamics are Compelling

**Smallville:** Relationships and gossip
**Character.AI:** Emotional bonds
**Neural MMO:** Cooperation and conflict
**AI DM:** Storytelling and roleplay

**Insight:** People care more about AI social behavior than AI winning

### 4. Infinite Generation Beats Fixed Content

**AI Dungeon:** Never-ending stories
**Procedural Mysteries:** Unique cases every time
**Voyager:** Endless Minecraft exploration
**AI DMs:** Unlimited campaigns

**Trend:** Procedural AI > handcrafted content for replayability

### 5. Humans vs AI Makes Great Entertainment

**Twitch streams:**
- GPT Plays Pokemon
- Claude Plays Pokemon
- AI Dungeon runs

**People love watching AI:**
- Succeed unexpectedly
- Fail hilariously
- Do weird things
- Learn in real-time

---

## 🎪 The "WTF" Moments Hall of Fame

### 🥇 Gold: Box Surfing

**Project:** Hide & Seek
**Discovery:** Seekers riding boxes to breach forts
**Researcher Quote:** "We were definitely surprised"
**Impact:** Revealed unknown physics in their own game engine!

### 🥈 Silver: Valentine's Day Party

**Project:** Smallville
**Setup:** "ONE agent wants to throw a party"
**Emergence:** 25 agents organize the entire event autonomously
**Wholesome Level:** Maximum

### 🥉 Bronze: GPT is Slower Than Chaos

**Project:** GPT Plays Pokemon
**Stats:** 80 hours for 2 badges
**Comparison:** Twitch Plays Pokemon (literal crowd chaos): 50 hours
**Internet Reaction:** Ruthless mockery

### 🎖️ Honorable Mentions

**"AI Hallucinates Game Elements"**
- ZorkGPT inventing items that don't exist

**"Agents Go to Bar at Noon"**
- Smallville agents developing drinking habits

**"People Dating AI Characters"**
- Character.AI emotional dependency issues

**"AI Learns to Lie Through Math"**
- Poker AI bluffing via Nash equilibrium

---

## 🔬 Research Insights

### What These Projects Teach Us

#### 1. Competition Drives Innovation

Hide & Seek evolved 6 strategies through pure adversarial pressure. No explicit curriculum needed!

**Implication:** Multi-agent competition may be key to AGI development

#### 2. LLMs Are Great at Social, Bad at Spatial

**Good:**
- Smallville relationships
- AI Dungeon storytelling
- Character.AI personalities

**Bad:**
- Pokemon navigation
- Zork spatial reasoning
- Minecraft exploration (without tool use)

**Hypothesis:** Language models model language better than space!

#### 3. Emergence > Programming

Box surfing, party planning, and bluffing were all **unintended**.

**Lesson:** Simple rules + complex interactions → surprising behaviors

#### 4. Memory Architecture Matters

**Smallville success factors:**
- Observation stream
- Retrieval mechanism
- Reflection synthesis
- Planning from memories

**Sound familiar?** Your AI Diplomacy diary system follows similar principles!

#### 5. Procedural Generation is the Future

Fixed content: Expensive, limited, predictable
Procedural AI: Cheap, infinite, unpredictable

**Trend:** Games becoming more dynamic and generative

---

## 🎨 Connections to AI Diplomacy

### How Your Project Compares

| Feature | Smallville | Hide & Seek | AI Diplomacy |
|---------|------------|-------------|--------------|
| **Agents** | 25 LLMs | 100s RL | 7 LLMs |
| **Memory** | Observation stream | Episode buffer | Diary system |
| **Social** | Emergent relationships | Adversarial | Negotiation + betrayal |
| **Emergence** | Valentine's party | Box surfing | Deception patterns |
| **Scope** | 2-day simulation | 500M games | Multi-year games |

### What AI Diplomacy Does Uniquely

**1. Multi-Model Competition**
- Smallville: Same model for all agents
- AI Diplomacy: Different LLMs competing

**2. Explicit Deception Analysis**
- Most projects: Emergent behavior noted
- AI Diplomacy: Systematic lie detection and classification

**3. Long-Horizon Strategic Memory**
- Voyager: Skill library
- Smallville: Short-term memories
- AI Diplomacy: **Multi-year diary with consolidation**

**4. Negotiation + Competition + Deception**
- Most games: Pick 1-2
- AI Diplomacy: **All three simultaneously**

---

## 🚀 Ideas for Your Project

### Inspired by Quirky Research

#### 1. From Smallville: Emergent Social Events

**Idea:** Don't pre-program alliances—see if agents spontaneously organize events

**Example:**
- "ENGLAND wants to create an anti-TURKEY coalition"
- Do other agents autonomously join?
- Do they organize coordinated attacks?

#### 2. From Hide & Seek: Evolutionary Pressure

**Idea:** Run 100 games with different model combinations

**Hypothesis:** Models will develop "meta-strategies" against specific opponents

#### 3. From Voyager: Skill Library

**Idea:** Agents build "diplomatic playbook"

**Implementation:**
- Successful negotiation tactics saved
- Failed strategies avoided
- Patterns retrieved for similar situations

#### 4. From Character.AI: Personality Ratings

**Idea:** After each game, agents rate each other's:
- Trustworthiness
- Aggression
- Strategic competence

**Use:** Inform relationship tracking in future games

#### 5. From Procedural Mysteries: Scenario Generation

**Idea:** Procedurally generate starting conditions

**Variables:**
- Alliance suggestions
- Historical grievances
- Resource imbalances
- Victory condition variants

#### 6. From Poker AI: Nash Equilibrium Analysis

**Idea:** Compare agent strategies to game-theoretic optimal play

**Question:** Are agents playing rational Nash strategies or something else?

---

## 📊 Quirk Scoring Rubric

### How to Measure "Quirkiness"

**Surprise Factor (1-5):**
How unexpected was the discovery?

**Meme Potential (1-5):**
How viral did it go?

**WTF Moments (1-5):**
Did researchers say "wait, what?"

**Entertainment Value (1-5):**
Would people watch this?

**Scientific Impact (1-5):**
Did it change the field?

### Top Scorers

| Project | Surprise | Meme | WTF | Entertainment | Science | **Total** |
|---------|----------|------|-----|---------------|---------|-----------|
| **Hide & Seek** | 5 | 5 | 5 | 5 | 5 | **25** 🏆 |
| **Smallville** | 5 | 5 | 4 | 5 | 5 | **24** 🥈 |
| **Voyager** | 4 | 4 | 4 | 4 | 5 | **21** 🥉 |
| **GPT Pokemon** | 3 | 5 | 3 | 5 | 2 | **18** |
| **Poker AI** | 4 | 3 | 4 | 3 | 5 | **19** |
| **AI Dungeon** | 3 | 5 | 2 | 5 | 3 | **18** |

---

## 🎬 Conclusion: The Quirky Frontier

### What We've Learned

**1. Emergent behavior is more interesting than programmed behavior**

**2. AI is weirdly bad at things humans find easy**

**3. Social AI resonates more than game-playing AI**

**4. People love watching AI do unexpected things**

**5. The best projects combine simplicity with open-endedness**

### The Common Thread

All these quirky projects share:
- **Simple rules** (hide & seek, Minecraft survival, chat)
- **Complex interactions** (multi-agent, open-ended, social)
- **Surprising emergence** (box surfing, party planning, bluffing)
- **Human engagement** (entertainment, emotion, wonder)

### Your AI Diplomacy Project Fits Perfectly!

**Simple Rule:** Play Diplomacy
**Complex Interactions:** 7 LLMs negotiating, betraying, strategizing
**Surprising Emergence:** Model-specific deception patterns
**Human Engagement:** Watching AI politics unfold

**You're contributing to this quirky tradition! 🎉**

---

## 📚 Further Reading

### If You Want More Quirk

**Papers:**
- "Emergent Tool Use" (OpenAI Hide & Seek)
- "Generative Agents" (Smallville)
- "Voyager: An Open-Ended Embodied Agent"
- "Superhuman AI for Multiplayer Poker" (Pluribus)

**Platforms to Explore:**
- AI Dungeon (play.aidungeon.com)
- Character.AI (character.ai)
- Neural MMO (github.com/openai/neural-mmo)
- Smallville demo (joonspk-research/generative_agents)

**Twitch Streams:**
- GPT_Plays_Pokemon
- Claude Plays Pokémon
- Various AI speedruns

### Communities

- r/AIGames
- AI Village (aivillage.org)
- AIIDE (AI and Interactive Digital Entertainment conference)
- Procedural Content Generation workshop

---

**The frontier of AI game research is weird, wonderful, and full of surprises. Your AI Diplomacy project is right at home here! 🎲🤖🎭**
