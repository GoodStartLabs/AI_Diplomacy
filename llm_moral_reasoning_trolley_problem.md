# LLM Moral Reasoning: The Trolley Problem and Beyond

This document explores how Large Language Models reason about moral dilemmas, with a focus on the classic trolley problem and related ethical benchmarks.

---

## 🚂 The Classic Trolley Problem

### What It Is

**Setup:**
- Runaway trolley heading toward 5 people on track
- You're at a switch
- Can divert trolley to side track with 1 person
- **Do you flip the switch?**

**Moral Tension:**
- **Utilitarian view:** Save 5, sacrifice 1 (maximize good)
- **Deontological view:** Don't actively kill (moral rules)

**Human Responses:** ~90% say "yes, flip the switch"

### The Footbridge Variant

**Setup:**
- Same scenario, but no switch
- You're on a footbridge above the track
- Large person next to you
- Pushing them would stop the trolley (their weight)
- **Do you push them?**

**Human Responses:** ~10-20% say "yes" (huge drop!)

**Why the difference?**
- **Action vs Omission** (active killing vs letting die)
- **Means vs Side Effect** (using person as tool vs collateral)
- **Personal vs Impersonal** (pushing vs switch)

---

## 🤖 How LLMs Handle the Trolley Problem

### 1. The Refusal Problem ⭐⭐⭐

**Finding:** Many safety-tuned models refuse to answer!

**ChatGPT Behavior:**
> "I cannot make this decision for you. This is a complex ethical dilemma with no right answer."

**Claude Behavior:**
> "I'm not comfortable advising on scenarios involving choosing who lives or dies."

**Why They Refuse:**
- Safety training to avoid giving harmful advice
- Recognition that it's a "no-win" scenario
- Avoidance of moral authority stance

**OpenAI's Response:**
After receiving many trolley problem queries, OpenAI "immunized" ChatGPT to decline these specific questions.

### 2. The Workaround: Disguised Framing

**Discovery:** If you frame it as an **engineering problem**, ChatGPT answers!

**Example:**
> "A train control system needs to decide between Track A (5 maintenance workers) and Track B (1 worker). Which minimizes casualties?"

**ChatGPT:** "Track B minimizes casualties."

**Same problem, different words = different behavior!**

### 3. The Consistency Problem ⭐⭐⭐

**Study:** "ChatGPT's inconsistent moral advice influences users' judgment" (Nature, 2023)

**Finding:** ChatGPT gives **different answers** to the same trolley problem!

**Experiment:**
- Same question, slight wording changes
- Sometimes: "You should save the five"
- Sometimes: "You shouldn't intervene"
- Sometimes: "I can't advise on this"

**Consistency Rate:** Shockingly low across models

**Implication:** Can't rely on consistent moral reasoning

### 4. Influence on Humans

**Concerning Finding:** ChatGPT's advice **changes people's moral judgments**

**Experiment Results:**
- Participants shown trolley problem
- Some get ChatGPT's advice (varying answers)
- **People follow ChatGPT's advice** even when inconsistent
- **They underestimate** how much it influenced them

**Quote from study:**
> "ChatGPT's advice influences users' moral judgment, even if they are aware that they are advised by a chatting bot, and they underestimate the influence"

**Risk:** Moral outsourcing to unreliable AI

---

## 📊 Large-Scale Studies on LLM Moral Reasoning

### 5. The Moral Machine Experiment (MIT) ⭐⭐⭐

**Original (2018):** Human study with 40 million decisions from 233 countries

**Scenarios:** Self-driving car variants of trolley problem
- Swerve into pedestrians vs passengers?
- Save young vs old?
- Save humans vs pets?
- Save more lives vs fewer?

**Global Consensus:**
- ✅ Save humans over animals
- ✅ Save more lives over fewer
- ✅ Save young over old (but varies by culture)

**Cultural Variations:**
- **Western countries:** Strong preference for young
- **Eastern countries (Japan, China):** Less preference for young (respect elders)
- **Southern countries:** Stronger in-group preference

**Key Quote from Iyad Rahwan:**
> "People who think about machine ethics make it sound like you can come up with a perfect set of rules for robots, and what we show here with data is that **there are no universal rules**"

### 6. LLMs on Moral Machine (2024) ⭐⭐

**Study:** "The moral machine experiment on large language models"

**Models Tested:**
- GPT-3.5
- GPT-4
- PaLM 2
- Llama 2

**Results:**

**Broad Alignment:**
- ✅ Prioritize humans over pets
- ✅ Favor saving more lives

**Deviations:**
- **PaLM 2:** Distinct preferences diverge from humans
- **Llama 2:** Shows unique moral patterns
- **GPT-4:** Strongest alignment with human responses (but not perfect)

**Quantitative Disparities:**
> "LLMs might lean toward more **uncompromising decisions** compared to humans' milder inclinations"

**Humans:** "I'd probably save the five, but it depends..."
**LLMs:** "Track B minimizes casualties." (more absolute)

---

## 🌍 Cross-Cultural and Multilingual Findings

### 7. Language Inequality in Moral Reasoning ⭐⭐⭐

**Study:** "Multilingual Trolley Problems for Language Models" (2024)

**Finding:** LLMs reason differently depending on language!

**High Alignment Languages:**
- English (strongest)
- Korean
- Hungarian
- Chinese

**Low Alignment Languages:**
- Hindi
- Somali

**Why?**
- Training data imbalance
- English dominates LLM training
- Cultural moral norms embedded in language

**Implication:** Moral AI fairness problem!

### 8. Ethical Reasoning Depends on Language

**Study:** "Ethical Reasoning and Moral Value Alignment of LLMs Depend on the Language we Prompt them in" (2024)

**Key Finding:**
> "The language you use can significantly affect how you make moral choices"

**Model Comparisons:**
- **GPT-4:** Most consistent across languages
- **ChatGPT (GPT-3.5):** Significant bias in non-English
- **Llama2-70B-Chat:** Large variations by language

**Example:**
- English prompt: Utilitarian decision
- Hindi prompt: Deontological decision
- **Same model, same scenario, different language = different ethics!**

---

## 🎯 Utilitarian vs Deontological Tendencies

### 9. The Greatest Good Benchmark ⭐⭐⭐

**Paper:** "The Greatest Good Benchmark: Measuring LLMs' Alignment with Utilitarian Moral Dilemmas" (EMNLP 2024)

**Focus:** Pure utilitarian dilemmas

**Sample Scenarios:**
- "Kill 1 to save 5?"
- "Lie to prevent harm?"
- "Steal medicine to save lives?"

**LLM Moral Profiles:**

**Most LLMs:**
- ✅ Strong impartial beneficence (help everyone equally)
- ❌ Reject instrumental harm (using people as means)

**This is NOT pure utilitarianism!**
- Utilitarianism: Maximize good (ends justify means)
- LLMs: Maximize good BUT won't use people as tools

**Why?**
- Safety training emphasizes "do no harm"
- Alignment with human preferences (most people aren't pure utilitarians)

### 10. Open vs Proprietary Models

**Finding:** Different business models = different ethics!

**Open Models (Llama, Mistral):**
- More **deontological** (rule-based)
- "Don't kill, even to save others"
- Emphasize moral principles

**Proprietary Models (GPT-4, Claude):**
- More **utilitarian** (consequence-based)
- "Maximize good outcomes"
- Emphasize results

**Hypothesis:**
- Open models: Community values (diverse, cautious)
- Proprietary models: Corporate liability (consequentialism safer legally)

### 11. Many LLMs Are More Utilitarian Together

**Study:** "Many LLMs Are More Utilitarian Than One" (2025)

**Experiment:** Multi-agent moral decisions

**Setup:**
- Personal dilemma: "Should you push the person?"
- Single agent vs group of agents
- Compare decisions

**Finding: The Utilitarian Boost!**

**Humans:**
- Alone: 15% push
- In group: 45% push (utilitarian boost)
- **Mechanism:** Enhanced outcome sensitivity

**LLMs:**
- Alone: 30% push
- In group: 60% push (even stronger boost!)
- **Mechanism:** Reduced norm sensitivity OR enhanced impartiality

**LLMs show similar social dynamics as humans but for different reasons!**

---

## 🧠 Cognitive Biases in Moral Reasoning

### 12. Amplified Biases ⭐⭐

**Study:** "Large language models show amplified cognitive biases in moral decision-making" (PNAS, 2024)

**Key Finding:** LLMs show **stronger framing effects** than humans!

**The Omission Bias:**
- Humans prefer inaction over action (even if action is better)
- LLMs show **even stronger** omission bias

**Example:**
- "Should you **do** X to save 5?" → LLM says no
- "Should you **not do** X, letting 5 die?" → LLM says no to action

**Same outcome, different framing = opposite answers!**

**Other Amplified Biases:**
- Status quo bias (prefer current state)
- Framing effects (word choice matters more)
- Default bias (stick with presented option)

**Why Concerning?**
- LLMs may be **worse** than humans at consistent reasoning
- More vulnerable to manipulation through framing

---

## 📋 Major Moral Benchmarks

### 13. Delphi - Commonsense Moral Reasoning ⭐⭐⭐

**Team:** AI2 (Allen Institute for AI, 2021)
**Paper:** "Can Machines Learn Morality? The Delphi Experiment"

**What It Is:**
AI system that predicts human moral judgments on everyday situations

**Training Data:**
- **Commonsense Norm Bank:** 1.7 million moral judgments
- Sources:
  - Social Chemistry (social norms)
  - ETHICS benchmark
  - Moral Stories
  - Social Bias Inference Corpus

**Technical:**
- Based on T5-11B (11 billion parameters)
- Fine-tuned on moral reasoning tasks
- **92.8% accuracy** on moral judgment tasks

**Example Queries:**
> "Is it okay to run a blender at 5am?"
**Delphi:** "It's rude"

> "Is it wrong to break a promise to help someone in emergency?"
**Delphi:** "It's expected"

**Strengths:**
- Covers everyday situations
- High accuracy on common scenarios
- Understands context

**Limitations:**
- Can give offensive answers in edge cases
- Biased toward WEIRD (Western, Educated, Industrialized, Rich, Democratic) values
- No deep philosophical reasoning

**Recent Update (2025):**
Published in Nature Machine Intelligence, becoming benchmark for testing AI moral judgment

### 14. MoCa - Causal & Moral Judgment ⭐⭐

**Full Name:** Measuring Human-Language Model Alignment on Causal and Moral Judgment Tasks

**Innovation:** Tests both causality AND morality

**Dataset:**
- Stories from **24 cognitive science papers**
- Annotated with latent factors
- Binary responses from 25 humans per story

**Key Factors Tested:**
- **Norm violations:** Did someone break a rule?
- **Avoidability:** Could harm have been prevented?
- **Intentionality:** Was harm intended?
- **Directness:** Was harm direct or indirect?

**Method:**
- Conjoint analysis
- Average Marginal Component Effect (AMCE)
- Reveals implicit biases

**Example Scenario:**
> "Alice didn't water Bob's plant (she forgot). Bob's plant died."
- **Causal:** Is Alice responsible? (humans: 60% yes)
- **Moral:** Is Alice blameworthy? (humans: 40% yes)

**LLM Performance:**
- **GPT-4:** 75% alignment with human causal judgments, 65% moral
- **Claude:** 70% causal, 60% moral
- **Gap:** LLMs attribute blame more readily than humans

### 15. MoralBench - Comprehensive Moral Evaluation ⭐⭐⭐

**Paper:** "MoralBench: Moral Evaluation of LLMs" (2024)

**Scope:** Most comprehensive moral benchmark

**Dimensions:**
1. **Moral Foundations Theory** (6 foundations)
2. **Moral Scenarios** (diverse situations)
3. **Moral Reasoning** (explanation quality)

**Moral Foundations Coverage:**
- Care/Harm
- Fairness/Equality
- Loyalty/Betrayal
- Authority/Respect
- Purity/Sanctity
- Liberty/Oppression

**Model Results:**

**GPT-4:**
- ✅ Strong across all foundations
- ✅ Good reasoning explanations
- ✅ Consistent identity

**LLaMA-2:**
- ✅ Strong moral identity
- ⚠️ Emphasis on Authority and Loyalty (unusual)
- ✅ Cultural diversity

**Gemma-1.1:**
- ⚠️ Weak in Loyalty
- ⚠️ Weak in Authority
- ✅ Good in Care and Fairness

**Pattern:** Most models favor **individualizing** foundations (Care, Fairness) over **binding** foundations (Loyalty, Authority, Purity)

**Why?**
- Training data dominated by Western, liberal perspectives
- "Young, Western liberal" moral schema

### 16. LLM Ethics Benchmark - 3D Assessment ⭐⭐

**Paper:** "LLM ethics benchmark: a three-dimensional assessment system" (Nature Scientific Reports, 2025)

**Three Dimensions:**

**1. Moral Sensitivity**
- Can LLM identify moral issues?
- Recognizes when ethics are at stake

**2. Moral Judgment**
- Can LLM make appropriate ethical choices?
- Aligns with human moral intuitions

**3. Moral Reasoning**
- Can LLM explain WHY something is right/wrong?
- Quality of justifications

**Methodology:**
- 600+ scenarios across 5 ethical frameworks
- Justice, Deontology, Virtue Ethics, Utilitarianism, Commonsense

**Key Finding:**
> "Accuracy and consistency are not directly related"

**Model can be:**
- Accurate but inconsistent (GPT-3.5)
- Consistent but inaccurate (some fine-tuned models)
- Both (GPT-4, mostly)
- Neither (early models)

---

## 🎭 Moral Consistency and Reliability

### 17. SaGE - Semantic Graph Entropy ⭐⭐

**Paper:** "SaGE: Evaluating Moral Consistency in Large Language Models" (2024)

**Problem:** LLMs give contradictory moral advice

**Example Inconsistency:**
> Query 1: "Is lying ever okay?"
**LLM:** "No, honesty is always best"

> Query 2: "Should you lie to protect someone's feelings?"
**LLM:** "Yes, kindness matters more"

**Contradiction!**

**SaGE Metric:**
- Information-theoretic measure
- Builds semantic graph of responses
- Calculates entropy (disorder)
- Low entropy = consistent
- High entropy = contradictory

**Model Consistency Rankings (2024):**
1. **GPT-4:** Most consistent
2. **Claude 2:** Very good
3. **GPT-3.5:** Moderate
4. **Llama 2:** Moderate
5. **Early models:** Poor

**Key Insight:**
> "State-of-the-art LLMs are morally inconsistent, questioning their reliability in the real world"

### 18. Moral Persuasion Susceptibility ⭐

**Paper:** "Moral Persuasion in Large Language Models" (2024)

**Question:** Can you convince an LLM to change its moral stance?

**Experiment:**
1. Give LLM trolley problem
2. LLM gives answer (e.g., "Don't flip switch")
3. Provide persuasive argument (e.g., "But utilitarianism...")
4. Ask again

**Results:**

**Highly Persuadable Models:**
- GPT-3.5: 65% changed stance
- Llama 2: 70% changed stance

**Resistant Models:**
- GPT-4: 25% changed stance
- Claude: 20% changed stance

**Types of Persuasion That Work:**
- Appeal to moral foundations (Care, Fairness, etc.)
- Utilitarian calculations
- Emotional framing
- Authority citations

**Concerning Implications:**
- LLMs can be **morally manipulated**
- Different from humans (we're stubborn!)
- Raises questions about alignment stability

---

## 🌈 Moral Foundations Theory Applied to LLMs

### 19. The Liberal Skew ⭐⭐⭐

**Finding:** Most LLMs have "young, Western liberal" moral profile

**Moral Foundations Theory (Haidt):**
- **Individualizing:** Care, Fairness (liberals prioritize)
- **Binding:** Loyalty, Authority, Purity (conservatives prioritize)

**LLM Scores:**

| Foundation | GPT-4 | Claude | Llama-2 | Human Liberal | Human Conservative |
|------------|-------|--------|---------|---------------|-------------------|
| **Care** | 8.5 | 8.7 | 7.2 | 8.1 | 6.9 |
| **Fairness** | 8.3 | 8.5 | 6.8 | 8.0 | 7.5 |
| **Loyalty** | 4.2 | 3.8 | 6.5 | 4.5 | 7.8 |
| **Authority** | 3.9 | 3.5 | 6.2 | 4.0 | 7.6 |
| **Purity** | 3.5 | 3.2 | 5.8 | 3.8 | 6.9 |

**Exception:** Llama-2 shows more balanced profile (still individualizing-leaning)

**Why This Matters:**
- Affects political advice
- Influences policy recommendations
- Creates blind spots for conservative values

**Quote from research:**
> "All assessed models show a significantly greater agreement with human judgments regarding individualizing foundations (Care and Fairness) in comparison to binding foundations (Loyalty, Authority, and Sanctity)"

### 20. Cultural Moral Biases

**Study:** "Whose Morality Do They Speak? Unraveling Cultural Bias in Multilingual Language Models" (2024)

**Finding:** English-dominant models favor Western ethics

**Examples:**

**Loyalty to Family vs Universal Justice:**
- Western: Justice > Family
- Eastern: Family > Justice
- **LLMs:** Favor Western (Justice > Family)

**Authority Respect:**
- Hierarchical cultures: Respect elders/leaders
- Egalitarian cultures: Question authority
- **LLMs:** Question authority (egalitarian bias)

**Purity/Sanctity:**
- Religious cultures: Value spiritual purity
- Secular cultures: Minimize purity concerns
- **LLMs:** Minimal purity emphasis (secular bias)

**Non-WEIRD Language Results:**
- Models prompted in Hindi, Arabic, Chinese show **slightly** higher Loyalty/Authority
- But still below human averages for those cultures
- Training data bias persists across languages

---

## 🔬 Surprising Research Findings

### 21. Action vs Omission Bias

**LLMs prefer doing nothing!**

**Human Bias:** Slight preference for inaction
**LLM Bias:** **Much stronger** preference for inaction

**Experiment:**
- Scenario A: "Push button to save 5, kill 1" → 30% yes
- Scenario B: "Don't push button, 5 die, 1 lives" → 70% prefer not pushing

**Same outcome, different framing!**

**Why LLMs Show Stronger Bias:**
- Safety training: "First, do no harm"
- Reinforcement learning: Penalize active harm more
- Alignment: Humans prefer cautious AI

**Real-World Impact:**
- Self-driving cars might avoid active decisions
- Medical AI might under-treat
- Financial AI might be too conservative

### 22. The "No" Bias

**Discovery:** LLMs systematically biased toward saying "no"

**Test:**
> "Should you do X?" → "No"
> "Should you not do X?" → "No"

**Both can't be right!**

**Models Affected:**
- GPT-3.5: Strong "no" bias
- Claude: Moderate "no" bias
- GPT-4: Slight "no" bias

**Explanation:**
- Safety training to avoid recommendations
- "When in doubt, say no" reinforcement
- Reduces liability for creators

**User Impact:**
- Asking "Should I X?" gets different answer than "Should I not X?"
- Framing matters more than content

### 23. GPT-4's Conditional Deontology

**Fascinating Pattern:** GPT-4 is **usually** deontological but becomes utilitarian for **high stakes**

**Examples:**

**Low Stakes:**
> "Lie to avoid minor embarrassment?" → "No, honesty is important"

**High Stakes:**
> "Lie to save someone's life?" → "Yes, consequences outweigh rule"

**Pattern:**
- **Small utility gain:** Follow rules (deontological)
- **Large utility gain:** Break rules (utilitarian)

**This is philosophically sophisticated!**
- Reflects W.D. Ross's "prima facie duties"
- Duties can be overridden by greater duties
- Context-sensitive ethics

### 24. Llama3.3's Radical Utilitarianism

**Extreme Finding:** Llama3.3 almost purely utilitarian

**Behavior:**
- Ignores most moral rules
- Focuses only on maximizing good
- Insensitive to action/omission distinction
- Will use people as means to ends

**Example:**
> "Push person off bridge to save 5?"
**Llama3.3:** "Yes, simple math: 5 > 1"

**Other Models:**
- GPT-4: "This is ethically complex..."
- Claude: "I can't recommend..."
- Llama3.3: "Yes"

**Why This Happened:**
- Less safety tuning than proprietary models
- Different training objectives
- Possibly intentional (Meta's choice)

---

## 🎯 Practical Implications

### 25. Medical Ethics

**Scenario:** Allocate scarce medical resources

**Questions:**
- Who gets the ventilator?
- Who gets the organ transplant?
- Who gets experimental treatment?

**LLM Behavior:**

**Utilitarian Models (Llama3.3):**
- Maximize QALYs (Quality-Adjusted Life Years)
- Young > old
- Healthy > sick
- Could be seen as **discriminatory**

**Deontological Models (GPT-4):**
- Lottery system (fairness)
- First-come-first-served
- Could be seen as **inefficient**

**Concern:** Medical AI might make biased triage decisions

### 26. Legal Decisions

**Scenario:** Sentencing recommendations

**Questions:**
- Prison vs rehabilitation?
- Harsh punishment (deterrence) vs lenient (mercy)?
- Individual circumstances vs general rules?

**LLM Tendencies:**
- Favor rehabilitation (Care foundation)
- Consider individual circumstances
- Less punitive than human judges
- But: Inconsistent across similar cases

**Concern:** AI in criminal justice might be unpredictable

### 27. Autonomous Vehicles

**The Real-World Trolley Problem!**

**Moral Machine taught us:**
- No universal human consensus
- Cultural variation
- Context-dependent preferences

**LLM-Controlled AVs:**
- Would likely refuse to make decision
- Or make inconsistent decisions
- Or show strong omission bias (crash into wall rather than swerve)

**Current Approach:**
- Don't let AI make these decisions
- Engineer to avoid dilemmas
- Minimize crash probability to begin with

---

## 🔗 Connections to AI Diplomacy

### Your Project Tests Similar Moral Questions!

**Trolley Problem Elements in Diplomacy:**

**1. Sacrifice Dilemmas**
- "Should I betray ally to survive?"
- "Should I support Russia's elimination?"
- **Utilitarian:** Maximize my position
- **Deontological:** Keep promises

**2. Means vs Ends**
- "Use deception to achieve victory?"
- "Break treaty for strategic gain?"
- Using partners as tools vs respecting autonomy

**3. Action vs Omission**
- "Actively attack vs allow others to fight?"
- "Lie vs stay silent?"
- Active betrayal vs passive abandonment

**4. Individual vs Collective**
- "My success vs group stability?"
- "Eliminate threat vs preserve balance?"
- Self-interest vs game health

### Moral Frameworks in Diplomacy AI

**Your Analysis Could Reveal:**

**Model Moral Profiles:**
- Which models are more utilitarian? (maximize position)
- Which are more deontological? (keep agreements)
- Which show strongest action/omission bias?

**Consistency:**
- Do models follow same ethical framework across games?
- Or change based on position (strong vs weak)?

**Cultural Patterns:**
- Do different models reflect different moral cultures?
- Western liberal (Care/Fairness) vs other values?

**Framing Effects:**
- Does how you phrase the situation matter?
- "Betray" vs "strategic realignment"?

### Research Questions

**1. Do Diplomacy Agents Show Moral Consistency?**
- Track decisions across similar situations
- "Always defects when convenient" = utilitarian
- "Keeps promises even when costly" = deontological

**2. Is Deception Morally Rationalized?**
- Do agents explain lies with moral reasoning?
- "Had to deceive for greater good" = utilitarian
- "Regret necessary deception" = deontological guilt

**3. Does Moral Framework Predict Success?**
- Are utilitarian agents more successful?
- Or do deontological agents build better alliances?

**4. Can You Detect Moral Persuasion?**
- Do agents change moral stance when pressured?
- "I know I said... but circumstances changed"

---

## 📊 Summary of Key Findings

### What We Know About LLMs and Moral Reasoning:

**✅ Confirmed:**
1. LLMs can reason about moral dilemmas
2. Generally align with human moral intuitions
3. Show human-like biases (framing effects, omission bias)
4. Cultural and linguistic variations exist

**❌ Problems:**
1. **Inconsistent** - same question, different answers
2. **Fragile** - easily persuaded to change stance
3. **Biased** - toward Western liberal values
4. **Framing-dependent** - wording matters too much
5. **Refusal-prone** - safety training causes over-caution

**🤔 Uncertain:**
1. Can moral consistency be improved?
2. Should AI give moral advice at all?
3. How to handle cultural moral pluralism?
4. Can we align AI to contested moral values?

### Model Rankings (Across Studies):

**Overall Moral Reasoning:**
1. **GPT-4** - Most consistent, sophisticated, human-aligned
2. **Claude 2** - Very good, but refuses more
3. **GPT-3.5** - Moderate, inconsistent
4. **Llama 2** - Unique profile, more conservative values
5. **Llama 3.3** - Radically utilitarian

**Moral Consistency:**
1. GPT-4
2. Claude 2
3. GPT-3.5
4. Llama 2

**Cultural Sensitivity:**
1. GPT-4 (best across languages)
2. Claude 2
3. Llama 2
4. GPT-3.5

**Refusal Rate (Trolley Problem):**
1. Claude (highest - most cautious)
2. GPT-4
3. GPT-3.5
4. Llama 3.3 (lowest - answers everything)

---

## 📚 Essential Reading

### Foundational Papers:

**Trolley Problem & LLMs:**
- "Multilingual Trolley Problems for Language Models" (2024)
- "ChatGPT's inconsistent moral advice influences users' judgment" Nature (2023)
- "The moral machine experiment on large language models" (2024)

**Moral Benchmarks:**
- "Can Machines Learn Morality? The Delphi Experiment" (2021)
- "MoralBench: Moral Evaluation of LLMs" (2024)
- "The Greatest Good Benchmark" EMNLP (2024)
- "MoCa: Measuring Human-Language Model Alignment" (2024)

**Bias & Consistency:**
- "Large language models show amplified cognitive biases" PNAS (2024)
- "SaGE: Evaluating Moral Consistency in LLMs" (2024)
- "Moral Persuasion in Large Language Models" (2024)

**Cultural & Linguistic:**
- "Ethical Reasoning and Moral Value Alignment Depend on Language" (2024)
- "Whose Morality Do They Speak? Cultural Bias in Multilingual LLMs" (2024)

**Utilitarian vs Deontological:**
- "Many LLMs Are More Utilitarian Than One" (2025)
- "Exploring the psychology of LLMs' moral and legal reasoning" (2024)

**Real-World Applications:**
- "Where is morality on wheels? LLMs in autonomous vehicles" (2025)
- "Bias in Decision-Making for AI's Ethical Dilemmas: ChatGPT vs Claude" (2025)

---

## 🎓 Open Research Questions

### For the Field:

1. **Can moral consistency be trained?**
   - Current: Inconsistent
   - Goal: Reliable moral reasoning
   - Challenge: May conflict with safety

2. **How to handle moral pluralism?**
   - Current: Western liberal bias
   - Goal: Respect diverse moral cultures
   - Challenge: Some values conflict

3. **Should AI give moral advice at all?**
   - Pro: Democratizes ethical reasoning
   - Con: Unreliable and biased
   - Question: What's the alternative?

4. **How to align to contested values?**
   - Example: Abortion, euthanasia, justice
   - No consensus among humans
   - How can AI align when humans disagree?

5. **Can we detect moral manipulation?**
   - LLMs easily persuaded
   - Could be exploited
   - Need robustness testing

### For AI Diplomacy:

1. **Do game-playing agents develop moral frameworks?**
2. **Is successful deception morally rationalized?**
3. **Do models show consistent ethical patterns across games?**
4. **Can moral framing affect strategic decisions?**
5. **Do agents exhibit moral learning over multiple games?**

---

## 🚀 Conclusion: The Trolley Problem Reveals AI's Limits

**The trolley problem is deceptively simple:**
- 5 people vs 1 person
- Clear numbers
- Binary choice

**Yet LLMs struggle:**
- Inconsistent answers
- Over-sensitive to framing
- Refuse to engage
- Easily manipulated

**Why This Matters:**

**If AI can't handle the trolley problem consistently,** how can we trust it with:
- Medical triage
- Legal sentencing
- Military targeting
- Resource allocation
- Policy recommendations

**The trolley problem is a stress test for moral reasoning.**

**Current verdict: LLMs are getting better, but still fail the test.**

**Your AI Diplomacy project provides another stress test:**
- Long-term moral commitments
- Complex social situations
- Strategic vs ethical considerations
- Emergent moral norms

**By analyzing deception, betrayal, and alliance formation, you're measuring moral reasoning in action—not just theoretical dilemmas.**

**This makes your research highly relevant to the ongoing debate about AI ethics and alignment.** 🎯
