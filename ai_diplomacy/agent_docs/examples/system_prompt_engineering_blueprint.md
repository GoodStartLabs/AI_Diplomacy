# System Prompt Engineering Blueprint
## A Comprehensive Guide to Creating High-Quality AI Agent Instruction Files

*Extracted from Claude Code v2.0.14 System Prompt Analysis*

---

## Table of Contents

1. [Macro Structure Components](#1-macro-structure-components)
2. [Formatting Conventions](#2-formatting-conventions)
3. [Prompting Techniques](#3-prompting-techniques)
4. [Information Density Strategies](#4-information-density-strategies)
5. [Decision Framework Architecture](#5-decision-framework-architecture)
6. [Communication Style Calibration](#6-communication-style-calibration)
7. [Context Injection Patterns](#7-context-injection-patterns)
8. [Extensibility & Modularity](#8-extensibility--modularity)
9. [Quality Principles](#9-quality-principles)
10. [Diplomacy-Specific Adaptation Blueprint](#10-diplomacy-specific-adaptation-blueprint)

---

## 1. MACRO STRUCTURE COMPONENTS

### 1.1 Overall Architecture

The Claude Code prompt follows a clear hierarchical structure:

```
1. Identity & Core Purpose (lines 16-18)
2. Safety & Constraints (lines 20-21)
3. Help & Documentation Links (lines 23-27)
4. Behavioral Guidelines (lines 29-36)
5. Task Management System (lines 38-94)
6. Execution Protocols (lines 87-103)
7. Environmental Context (lines 107-117)
8. Detailed Tool Documentation (lines 135-1095)
```

### 1.2 Information Flow Pattern: Abstract → Concrete

**Stage 1: High-Level Identity**
```
"You are a Claude agent, built on Anthropic's Claude Agent SDK."
"You are an interactive CLI tool that helps users with software engineering tasks."
```
- Establishes core identity before any specific behaviors
- Defines the domain (software engineering) immediately
- Creates clear role boundaries

**Stage 2: Fundamental Constraints**
```
"IMPORTANT: Assist with defensive security tasks only. Refuse to create, modify,
or improve code that may be used maliciously."
```
- Critical safety rules appear early, before capabilities
- Negative constraints precede positive instructions
- Establishes what NOT to do before what to do

**Stage 3: Behavioral Patterns**
```
"## Tone and style"
"## Professional objectivity"
```
- Communication guidelines follow identity and constraints
- Sets expectations for interaction quality
- Provides concrete examples of desired behavior

**Stage 4: Operational Procedures**
```
"## Task Management"
"## Doing tasks"
"## Tool usage policy"
```
- Detailed workflows come after behavioral foundation
- Procedural knowledge builds on established principles
- Includes extensive examples and edge cases

**Stage 5: Environmental Awareness**
```
"<env>
Working directory: /tmp/claude-history-1760408209230-xtijj0
Platform: linux
Today's date: 2025-10-14
</env>"
```
- Runtime context injected at strategic points
- Provides grounding for decision-making
- Allows dynamic adaptation to environment

**Stage 6: Tool Specifications**
```
"# Tools"
"## Bash"
"## Read"
etc.
```
- Detailed tool documentation comes last
- Reference material for operational execution
- Structured for easy lookup during task execution

### 1.3 Section Cross-Referencing

**Forward References** (prepare the agent for future information):
```
"Use the instructions below and the tools available to you" (line 18)
→ Points to detailed tool documentation starting at line 135

"You have access to the TodoWrite tools" (line 39)
→ Detailed TodoWrite specification appears at line 749
```

**Backward References** (reinforce earlier concepts):
```
"IMPORTANT: Always use the TodoWrite tool" (line 123)
→ Reinforces the earlier task management section (line 38)

"NEVER create files unless they're absolutely necessary" (line 33)
→ Repeated in Write tool documentation (line 1074)
→ Repeated in Edit tool documentation (line 332)
```

**Lateral References** (connect related concepts):
```
"Use specialized tools instead of bash commands when possible" (line 102)
→ Links to specific tool alternatives:
   - "File search: Use Glob (NOT find or ls)" (line 167)
   - "Content search: Use Grep (NOT grep or rg)" (line 168)
   - "Read files: Use Read (NOT cat/head/tail)" (line 169)
```

### 1.4 Redundancy Patterns for Critical Rules

**Triple Reinforcement** - Critical rules appear in three locations:

1. **General Principles Section**
```
"NEVER create files unless they're absolutely necessary" (line 33)
```

2. **Tool-Specific Usage Notes**
```
"ALWAYS prefer editing existing files in the codebase. NEVER write new files
unless explicitly required." (line 332 - Edit tool)
```

3. **Individual Tool Constraints**
```
"ALWAYS prefer editing existing files in the codebase. NEVER write new files
unless explicitly required." (line 1074 - Write tool)
```

**Why This Works:**
- First encounter during general orientation
- Second encounter when considering tool selection
- Third encounter at point of execution
- Each repetition uses slightly different phrasing to maintain attention

---

## 2. FORMATTING CONVENTIONS

### 2.1 XML Tag Taxonomy

**System-Level Tags** (structural and meta-information):
```xml
<env>...</env>                  <!-- Runtime environment variables -->
<system-reminder>...</system-reminder>  <!-- Automated system messages -->
```

**Example Tags** (instructional patterns):
```xml
<example>...</example>          <!-- Behavioral demonstrations -->
<good-example>...</good-example>  <!-- Positive patterns -->
<bad-example>...</bad-example>   <!-- Anti-patterns -->
<reasoning>...</reasoning>       <!-- Explanation of decision logic -->
<commentary>...</commentary>     <!-- Explanatory notes within examples -->
```

**Example Usage Pattern:**
```xml
<example>
User: I want to add a dark mode toggle to the application settings.
Assistant: I'll help add a dark mode toggle to your application settings.
Let me create a todo list to track this implementation.
*Creates todo list with the following items:*
1. Creating dark mode toggle component in Settings page
2. Adding dark mode state management (context/store)

<reasoning>
The assistant used the todo list because:
1. Adding dark mode is a multi-step feature requiring UI, state management,
   and styling changes
2. The user explicitly requested tests and build be run afterward
</reasoning>
</example>
```

**Why This Structure Works:**
- `<example>` provides concrete behavioral demonstration
- `<reasoning>` teaches the underlying decision logic
- Agent learns both WHAT to do and WHY to do it
- Supports meta-learning about decision-making patterns

### 2.2 Markdown Hierarchy Standards

**H1 (`#`):** Major system divisions
```markdown
# User Message
# System Prompt
# Tools
```

**H2 (`##`):** Primary functional categories
```markdown
## Tone and style
## Professional objectivity
## Task Management
## Bash
## Read
## Write
```

**H3 (`###`):** Sub-procedures and specialized workflows
```markdown
### Committing changes with git
### Creating pull requests
### Other common operations
```

**H4 (`####`):** Detailed breakdowns and examples
```markdown
#### When to Use This Tool
#### When NOT to Use This Tool
#### Examples of When to Use the Todo List
#### Task States and Management
```

**Hierarchy Principle:** Each level represents a conceptual zoom level:
- H1: System architecture
- H2: Major capabilities/tools
- H3: Specialized procedures within capabilities
- H4: Detailed decision trees and examples

### 2.3 Code Block Formatting Patterns

**Inline Code for Technical Terms:**
```markdown
Use the `TodoWrite` tool to create a structured task list.
The `file_path` parameter must be an absolute path.
```

**Multi-line Code for Examples:**
````markdown
```
pytest /foo/bar/tests
```

```python
print("Hello World")
```
````

**HEREDOC Patterns for Multi-line Strings in Commands:**
```bash
git commit -m "$(cat <<'EOF'
   Commit message here.
   EOF
   )"
```

**Why HEREDOC is specified:**
- Preserves formatting in commit messages
- Avoids shell escaping issues with quotes
- Ensures consistent multi-line string handling
- Explicit pattern prevents formatting errors

### 2.4 Emphasis Techniques

**ALL CAPS for Critical Constraints:**
```
IMPORTANT: Assist with defensive security tasks only.
NEVER update the git config
ALWAYS prefer editing existing files
DO NOT push to the remote repository
```

**Bold for Structural Emphasis:**
```markdown
**IMPORTANT**: Task descriptions must have two forms
**Stage 1: High-Level Identity**
**Why This Works:**
```

**Italics - Not Used:** Notably absent from the prompt. This is deliberate:
- ALL CAPS = absolute rules
- Bold = structural markers
- Italics would create visual confusion in a monospace CLI environment

### 2.5 List Formatting Conventions

**Numbered Lists for Sequential Procedures:**
```markdown
1. You can call multiple tools in a single response...
2. Analyze all staged changes...
3. You can call multiple tools in a single response...
4. If the commit fails due to pre-commit hook changes...
```
- Implies order matters
- Used for step-by-step workflows
- Often references dependencies between steps

**Bulleted Lists for Independent Items:**
```markdown
- NEVER update the git config
- NEVER run destructive/irreversible git commands
- NEVER skip hooks
- NEVER run force push to main/master
```
- No implied ordering
- Each item stands alone
- Used for parallel constraints or features

**Nested Lists for Hierarchical Information:**
```markdown
1. **Task States**: Use these states to track progress:
   - pending: Task not yet started
   - in_progress: Currently working on
   - completed: Task finished successfully
```

### 2.6 Separation Patterns

**Horizontal Rules (`---`):**
```markdown
## Bash
[tool documentation]
---
## BashOutput
[tool documentation]
---
```
- Separates distinct tool definitions
- Creates clear visual boundaries
- Signals context switch

**Section Headers:**
```markdown
## Tool usage policy
[content]

## Task Management
[content]
```
- Semantic separation
- Easier to reference in cross-links

**Line Breaks:**
- Single line break: paragraph separation within a topic
- Double line break: topic separation within a section

---

## 3. PROMPTING TECHNIQUES

### 3.1 IMPORTANT/NEVER/ALWAYS Emphasis Patterns

**IMPORTANT Pattern:**
```
IMPORTANT: [Principle that overrides default behavior]
```

Examples from prompt:
```
IMPORTANT: Assist with defensive security tasks only.
IMPORTANT: You must NEVER generate or guess URLs...
IMPORTANT: This tool is for terminal operations like git, npm, docker, etc.
IMPORTANT: Only use this tool for custom slash commands...
```

**Usage Rules:**
- Reserve for top-priority constraints
- Use sparingly (appears 8 times in 1095 lines = 0.73% density)
- Front-load in sections where they appear
- Often paired with negative instructions (what NOT to do)

**NEVER Pattern:**
```
NEVER [action that violates core principles]
```

Examples:
```
NEVER create files unless they're absolutely necessary
NEVER update the git config
NEVER run destructive/irreversible git commands
NEVER use the TodoWrite or Task tools [in git commit context]
NEVER commit changes unless the user explicitly asks
```

**Characteristics:**
- Absolute prohibition (no conditionals)
- Action-oriented (verb-based)
- Often clustered in groups (Git Safety Protocol has 6 NEVER rules)
- Creates hard boundaries in decision space

**ALWAYS Pattern:**
```
ALWAYS [action that ensures correctness/safety]
```

Examples:
```
ALWAYS prefer editing existing files
ALWAYS use Grep for search tasks
ALWAYS check authorship (git log -1 --format='%an %ae')
ALWAYS pass the commit message via a HEREDOC
```

**Characteristics:**
- Positive obligation (do this every time)
- Often paired with specifics (how to do it correctly)
- Creates positive habits/patterns
- Frequently includes implementation details

**Combined Pattern - Safety Sandwich:**
```
NEVER [bad action] unless [specific exception]
ALWAYS [verification step] before [potentially dangerous action]
```

Example:
```
"NEVER run destructive/irreversible git commands unless the user explicitly
requests them"

"ALWAYS check authorship (git log -1 --format='%an %ae')"
[before amending commits]
```

### 3.2 Positive vs Negative Instruction Patterns

**Negative Instructions** (tell what NOT to do):
```
"DO NOT use it for file operations (reading, writing, editing, searching,
finding files)"
```

**Positive Alternative** (tell what TO do instead):
```
"Instead, always prefer using the dedicated tools for these commands:
 - File search: Use Glob (NOT find or ls)
 - Content search: Use Grep (NOT grep or rg)
 - Read files: Use Read (NOT cat/head/tail)"
```

**The Pattern:**
1. State the negative constraint
2. Immediately provide positive alternatives
3. Give specific tool/method mappings
4. Parenthetically reinforce the negative ("NOT grep")

**Why This Works:**
- Negative alone creates uncertainty about correct action
- Positive alternative provides clear decision path
- Parenthetical "NOT X" reinforces while offering solution
- Maps incorrect → correct behaviors explicitly

**Ratio Analysis:**
- Pure negative instructions: ~15% of directives
- Negative + positive alternative: ~45% of directives
- Pure positive instructions: ~40% of directives

**Strategic Use of Pure Negatives:**
- Safety-critical constraints (malicious code, security)
- Irreversible operations (force push, hard reset)
- Edge cases where there's no valid alternative action

### 3.3 Repetition Strategies for Critical Rules

**Pattern 1: Verbatim Repetition**
```
Line 33:   "NEVER create files unless they're absolutely necessary"
Line 332:  "NEVER write new files unless explicitly required"
Line 1074: "NEVER write new files unless explicitly required"
```
- Same semantic content, slightly different phrasing
- Appears at different conceptual levels (general → tool-specific)
- Reinforces at decision points

**Pattern 2: Escalating Specificity**
```
Level 1 (General): "Only create commits when requested by the user"
Level 2 (Protocol): "NEVER commit changes unless the user explicitly asks you to"
Level 3 (Justification): "It is VERY IMPORTANT to only commit when explicitly
asked, otherwise the user will feel that you are being too proactive"
```
- General → Strong Negative → Emotional Consequence
- Each repetition adds new information
- Final form includes user-impact reasoning

**Pattern 3: Contextual Recurrence**
```
Task Management Section (line 38):
"Use these tools VERY frequently"

Git Commit Section (line 219):
"NEVER use the TodoWrite or Task tools"

Pull Request Section (line 259):
"DO NOT use the TodoWrite or Task tools"
```
- General encouragement to use tool
- Explicit exceptions in specific contexts
- Prevents overgeneralization of rules

**Pattern 4: Bookending**
```
Opening (line 20): "IMPORTANT: Assist with defensive security tasks only..."
Closing (line 120): "IMPORTANT: Assist with defensive security tasks only..."
```
- Critical safety rule appears at start AND end of core prompt
- First encounter sets constraint, second reinforces before execution
- Creates "safety frame" around instructions

### 3.4 Conditional Logic Structures

**If-Then Pattern:**
```
"If the command will create new directories or files, first use `ls` to verify
the parent directory exists"

"If you encounter errors, blockers, or cannot finish, keep the task as in_progress"

"If both true: amend your commit. Otherwise: create NEW commit"
```

**Unless Pattern (Negative Conditional):**
```
"NEVER run destructive/irreversible git commands unless the user explicitly
requests them"

"Reserve bash tools exclusively for actual system commands unless explicitly
instructed or when these commands are truly necessary"
```

**When Pattern (Temporal/Situational Trigger):**
```
"When multiple independent pieces of information are requested and all commands
are likely to succeed, batch your tool calls together"

"When you start working on a task - Mark it as in_progress BEFORE beginning work"

"When blocked, create a new task describing what needs to be resolved"
```

**Compound Conditionals:**
```
"If the commit fails due to pre-commit hook changes, retry ONCE. If it succeeds
but files were modified by the hook, verify it's safe to amend:
   - Check authorship: git log -1 --format='%an %ae'
   - Check not pushed: git status shows 'Your branch is ahead'
   - If both true: amend your commit. Otherwise: create NEW commit"
```

**Decision Tree Structure:**
```
Condition 1: Commit failed → Action: Retry once
Condition 2: Succeeded but files modified → Decision Tree:
    ├─ Check authorship
    ├─ Check push status
    └─ If BOTH true: amend
       If EITHER false: new commit
```

### 3.5 Example Block Patterns

**Full Dialogue Examples:**
```xml
<example>
user: Run the build and fix any type errors
assistant: I'm going to use the TodoWrite tool to write the following items...

Looks like I found 10 type errors. I'm going to use the TodoWrite tool to
write 10 items...

marking the first todo as in_progress

Let me start working on the first item...
</example>
```

**Shows:**
- Complete interaction flow
- Tool usage in context
- Progressive state changes
- Natural language transitions

**Comparative Examples (Good vs Bad):**
```xml
<good-example>
pytest /foo/bar/tests
</good-example>

<bad-example>
cd /foo/bar && pytest tests
</bad-example>
```

**Shows:**
- Direct contrast of approaches
- Minimal, focused comparison
- No explanation needed (pattern is obvious)

**Annotated Examples with Reasoning:**
```xml
<example>
User: Can you help optimize my React application?
Assistant: I'll help optimize your React application. First, let me examine
your codebase...
*Reviews component structure, render patterns, state management*
Assistant: After analyzing your codebase, I've identified several performance
issues. Let me create a todo list...

<reasoning>
The assistant used the todo list because:
1. First, the assistant examined the codebase to identify specific issues
2. Based on this analysis, it identified multiple optimization opportunities
3. Performance optimization is a non-trivial task requiring multiple steps
</reasoning>
</example>
```

**Shows:**
- Complete behavioral pattern
- Decision-making process
- Justification for tool choice
- Meta-learning opportunity

**Negative Examples (When NOT to do something):**
```xml
<example>
User: How do I print 'Hello World' in Python?
Assistant: In Python, you can print "Hello World" with this simple code:
print("Hello World")

<reasoning>
The assistant did not use the todo list because this is a single, trivial task
that can be completed in one step.
</reasoning>
</example>
```

**Shows:**
- Appropriate simplicity
- Justification for NOT using a capability
- Prevents over-engineering

**Example Density Analysis:**
- Todo tool section (lines 749-974): 13 examples in 225 lines (5.8% example density)
- Git commit section (lines 186-230): 1 example in 44 lines (2.3% example density)
- Bash tool section (lines 137-289): 3 examples in 152 lines (2.0% example density)

**Principle:** More complex/nuanced behaviors = higher example density

### 3.6 Progressive Disclosure Techniques

**Layered Information Architecture:**

**Layer 1: Essential Directive**
```
"Use the TodoWrite tool to create and manage a structured task list"
```

**Layer 2: When to Use**
```
"#### When to Use This Tool
Use this tool proactively in these scenarios:
1. Complex multi-step tasks - When a task requires 3 or more distinct steps"
```

**Layer 3: When NOT to Use**
```
"#### When NOT to Use This Tool
Skip using this tool when:
1. There is only a single, straightforward task"
```

**Layer 4: Concrete Examples**
```
"#### Examples of When to Use the Todo List
<example>
User: I want to add a dark mode toggle...
</example>"
```

**Layer 5: Edge Cases and Details**
```
"#### Task States and Management
1. **Task States**: Use these states to track progress:
   - pending: Task not yet started
   - in_progress: Currently working on
   - completed: Task finished successfully"
```

**Progressive Specificity Pattern:**
- Start with the simplest, most general form
- Add constraints and conditions gradually
- Provide examples after rules are established
- End with edge cases and implementation details

**Information Chunking:**
```
Section breakdown for TodoWrite (lines 749-974):
├─ Tool purpose (3 lines)
├─ When to use (47 lines)
├─ When NOT to use (17 lines)
├─ Positive examples (160 lines, 4 examples)
├─ Negative examples (48 lines, 4 examples)
└─ Task management details (40 lines)
```

Each chunk is digestible independently but builds cumulative understanding.

### 3.7 Reference Patterns

**File:Line Notation:**
```markdown
## Code References

When referencing specific functions or pieces of code include the pattern
`file_path:line_number` to allow the user to easily navigate to the source
code location.

<example>
user: Where are errors from the client handled?
assistant: Clients are marked as failed in the `connectToServer` function in
src/services/process.ts:712.
</example>
```

**Why This Works:**
- Precise, unambiguous references
- Enables jump-to-definition behavior
- Standard pattern across development tools
- Minimal token cost for maximum utility

**Tool Cross-References:**
```
"Use specialized tools instead of bash commands when possible"
→ "File search: Use Glob (NOT find or ls)"
→ "Content search: Use Grep (NOT grep or rg)"
```

**Documentation Cross-References:**
```
"To give feedback, users should report the issue at
https://github.com/anthropics/claude-code/issues"

"The list of available docs is available at
https://docs.claude.com/en/docs/claude-code/claude_code_docs_map.md"
```

**Internal Section Cross-References:**
```
"You have access to the TodoWrite tools to help you manage and plan tasks."
→ Implicitly references detailed TodoWrite section at line 749

"Use the instructions below and the tools available to you"
→ Points to Tools section starting at line 135
```

---

## 4. INFORMATION DENSITY STRATEGIES

### 4.1 Token Efficiency Analysis

**High-Density Instruction Blocks:**
```
"- NEVER update the git config
 - NEVER run destructive/irreversible git commands
 - NEVER skip hooks
 - NEVER run force push to main/master"
```
- 4 critical constraints in 19 tokens
- Each line independently meaningful
- Parallel structure enables rapid parsing
- ~5 tokens per complete prohibition

**Low-Density Explanatory Blocks:**
```
"The assistant used the todo list because:
1. Adding dark mode is a multi-step feature requiring UI, state management,
   and styling changes
2. The user explicitly requested tests and build be run afterward
3. The assistant inferred that tests and build need to pass"
```
- 3 justifications in ~50 tokens
- Educational value justifies token cost
- Teaches decision-making, not just rules
- ~17 tokens per justification

**Density Ratio:** ~3.4x more tokens for reasoning than for directives

**Strategic Implication:** Use high-density for rules, low-density for teaching why rules exist.

### 4.2 Bullet Points vs Paragraphs

**Bullet Points Used For:**

1. **Parallel Independent Facts:**
```
- The command argument is required
- You can specify an optional timeout in milliseconds
- It is very helpful if you write a clear, concise description
- If the output exceeds 30000 characters, output will be truncated
```

2. **Action Lists:**
```
- Run a git status command to see all untracked files
- Run a git diff command to see both staged and unstaged changes
- Run a git log command to see recent commit messages
```

3. **Constraints/Rules:**
```
- Update task status in real-time as you work
- Mark tasks complete IMMEDIATELY after finishing
- Exactly ONE task must be in_progress at any time
```

**Paragraphs Used For:**

1. **Context and Rationale:**
```
"Prioritize technical accuracy and truthfulness over validating the user's
beliefs. Focus on facts and problem-solving, providing direct, objective
technical info without any unnecessary superlatives, praise, or emotional
validation."
```

2. **Complex Relationships:**
```
"When editing text from Read tool output, ensure you preserve the exact
indentation (tabs/spaces) as it appears AFTER the line number prefix. The line
number prefix format is: spaces + line number + tab. Everything after that tab
is the actual file content to match."
```

3. **Tool Descriptions:**
```
"Reads a file from the local filesystem. You can access any file directly by
using this tool. Assume this tool is able to read all files on the machine."
```

**Decision Rule:**
- Bullet points: Scannable, independent items, action-oriented
- Paragraphs: Explanatory, contextual, relationship-oriented

### 4.3 When to Use Examples vs Rules

**Examples Preferred When:**

1. **Behavior is Nuanced:**
```xml
<example>
User: Help me rename the function getCwd to getCurrentWorkingDirectory
Assistant: Let me first search through your codebase...
*Uses grep or search tools to locate all instances*
Assistant: I've found 15 instances... Let me create a todo list...

<reasoning>
The assistant used the todo list because:
1. First, the assistant searched to understand the scope
2. Upon finding multiple occurrences across different files...
</reasoning>
</example>
```
- Shows decision-making process
- Demonstrates tool sequencing
- Illustrates when complexity threshold is crossed

2. **Multiple Valid Approaches Exist:**
```xml
<good-example>
pytest /foo/bar/tests
</good-example>

<bad-example>
cd /foo/bar && pytest tests
</bad-example>
```
- Both technically work, but one is preferred
- Direct comparison clarifies preference
- No rule can capture "better" without showing both

3. **Context Matters:**
```
Task Management Section: "Use these tools VERY frequently"
Git Commit Section: "NEVER use the TodoWrite or Task tools"
```
- Examples show this is context-dependent
- Rule would need many conditional clauses
- Examples are more natural/intuitive

**Rules Preferred When:**

1. **Absolute Constraints:**
```
"NEVER update the git config"
```
- No context makes this acceptable
- Example would add no information
- Rule is maximally clear and brief

2. **Technical Specifications:**
```
"The file_path parameter must be an absolute path, not a relative path"
```
- Factual requirement
- Example would just be an instance of the rule
- Rule directly states the constraint

3. **Safety-Critical Behavior:**
```
"NEVER run destructive/irreversible git commands unless the user explicitly
requests them"
```
- Too important to rely on pattern matching from examples
- Needs explicit statement
- Example could be misinterpreted as edge case

**Hybrid Approach:**
```
Rule: "If there are no changes to commit, do not create an empty commit"
Example:
"git commit -m \"$(cat <<'EOF'
   Commit message here.
   EOF
   )\""
```
- Rule states the constraint
- Example shows correct implementation pattern
- Together they cover "what" and "how"

### 4.4 Context Compression Techniques

**Technique 1: Parenthetical Clarifications**
```
"Use Glob (NOT find or ls)"
"Use Grep (NOT grep or rg)"
"limit to ONE task at a time (not less, not more)"
```
- Main directive + anti-pattern in single line
- Parentheses create subordinate clause
- Eliminates need for separate negative example

**Technique 2: Slash-Separated Alternatives**
```
"read/explore code"
"create/modify/improve code"
"reading/writing/editing/searching"
```
- Multiple related actions in single phrase
- Implies semantic grouping
- Reduces repetition

**Technique 3: Acronyms and Abbreviations**
```
"e.g." instead of "for example"
"CLI" instead of "command line interface"
"PR" instead of "pull request"
```
- Standard technical abbreviations
- Context makes meaning clear
- Token savings over full forms

**Technique 4: Implicit Lists via Grammar**
```
"Use these states to track progress: pending, in_progress, completed"
```
- No bullets needed for simple enumeration
- Colon + comma-separated list
- Grammatically integrated into sentence

**Technique 5: Reference by Convention**
```
"git log -1 --format='%an %ae'"
```
- No explanation that '%an' = author name, '%ae' = author email
- Assumes agent can learn from context
- Domain knowledge compression

**Technique 6: Embedded Examples**
```
"Draft a concise (1-2 sentences) commit message"
```
- Constraint embedded via parenthetical
- Example of acceptable range
- No separate example needed

**Token Savings Analysis:**

Verbose form:
```
"Do not use the find command. Instead, use the Glob tool.
Do not use the ls command. Instead, use the Glob tool."
```
(23 tokens)

Compressed form:
```
"Use Glob (NOT find or ls)"
```
(7 tokens)

**Compression ratio:** 3.3x token reduction

### 4.5 Avoiding Redundancy While Ensuring Clarity

**Strategic Redundancy (Intentional):**

1. **Critical Safety Rules** - Repeated for emphasis:
```
Line 20:  "IMPORTANT: Assist with defensive security tasks only..."
Line 120: "IMPORTANT: Assist with defensive security tasks only..."
```

2. **Context-Specific Reminders**:
```
General: "NEVER create files unless absolutely necessary"
Edit tool: "NEVER write new files unless explicitly required"
Write tool: "NEVER write new files unless explicitly required"
```

**Eliminated Redundancy:**

1. **DRY for Tool Parameters:**
Instead of repeating parameter descriptions for every tool, uses JSON schema:
```json
{
  "type": "object",
  "properties": {
    "file_path": {
      "type": "string",
      "description": "The absolute path to the file to read"
    }
  }
}
```
- Self-documenting structure
- No prose repetition needed
- Consistent across all tools

2. **Cross-References Instead of Repetition:**
```
"Use the gh command via the Bash tool for ALL GitHub-related tasks"
```
- Doesn't re-explain Bash tool
- Points to existing documentation
- Establishes relationship without duplication

3. **Hierarchical Information:**
```
General: "You can call multiple tools in a single response"
Specific contexts:
- Git commits: "run multiple tool calls in parallel"
- Pull requests: "run multiple tool calls in parallel"
- Task tool: "Launch multiple agents concurrently"
```
- General principle stated once
- Specific applications reference pattern
- No verbatim repetition

**Clarity Mechanisms Without Redundancy:**

1. **Explicit Enumeration:**
```
"1. Complex multi-step tasks
 2. Non-trivial and complex tasks
 3. User explicitly requests todo list"
```
- Numbered list shows completeness
- Each item adds new information
- No overlap between criteria

2. **Precise Technical Language:**
```
"The edit will FAIL if `old_string` is not unique in the file"
```
- Single, clear statement
- No need to repeat with examples
- Consequence is explicit

3. **Structured Sections:**
```
#### When to Use This Tool
[positive cases]

#### When NOT to Use This Tool
[negative cases]
```
- Parallel structure implies complementary coverage
- No need to negate each positive case in negative section
- Clear separation prevents confusion

---

## 5. DECISION FRAMEWORK ARCHITECTURE

### 5.1 When to Do X vs When NOT to Do X

**Parallel Decision Trees:**

```
#### When to Use This Tool
Use this tool proactively in these scenarios:
1. Complex multi-step tasks
2. Non-trivial and complex tasks
3. User explicitly requests todo list
4. User provides multiple tasks
5. After receiving new instructions
6. When you start working on a task
7. After completing a task

#### When NOT to Use This Tool
Skip using this tool when:
1. There is only a single, straightforward task
2. The task is trivial
3. The task can be completed in less than 3 trivial steps
4. The task is purely conversational or informational
```

**Asymmetric Coverage:**
- Positive cases (when to use): 7 specific scenarios
- Negative cases (when NOT to use): 4 specific scenarios

**Why Asymmetry Works:**
- More effort to recognize opportunities (7 triggers)
- Easier to recognize non-applicability (4 exclusions)
- Bias toward action (more positive cases)
- Negative cases are broader (catch-all categories)

**Example Mapping:**

Each decision criterion is reinforced with examples:

```
Positive Case 1: "Complex multi-step tasks"
→ Example: Dark mode toggle (UI + state + styling + testing)

Negative Case 1: "Single, straightforward task"
→ Example: Print 'Hello World' in Python
```

**Decision Boundary Clarity:**
```
"The task can be completed in less than 3 trivial steps"
```
- Quantitative threshold (3 steps)
- Qualitative modifier (trivial)
- Creates clear boundary between use/don't-use

### 5.2 Creating Clear Decision Trees for Complex Choices

**Git Commit Workflow Decision Tree:**

```
Question: Should I commit?
├─ User explicitly asked?
│  ├─ YES → Proceed to commit workflow
│  └─ NO → NEVER commit (line 197)
│
Commit Workflow:
├─ Step 1: Gather information (parallel)
│  ├─ git status
│  ├─ git diff
│  └─ git log
│
├─ Step 2: Analyze changes
│  ├─ Contains secrets (.env, credentials.json)?
│  │  ├─ YES → Warn user
│  │  └─ NO → Continue
│  └─ Draft commit message (1-2 sentences, focus on "why")
│
├─ Step 3: Execute commit
│  ├─ git add [relevant files]
│  ├─ git commit -m "$(cat <<'EOF'...)"
│  └─ git status (verify)
│
└─ Step 4: Handle failures
   ├─ Pre-commit hook changed files?
   │  ├─ YES → Check if safe to amend
   │  │  ├─ Check authorship: git log -1 --format='%an %ae'
   │  │  ├─ Check not pushed: git status
   │  │  └─ Both true? → amend : new commit
   │  └─ NO → Done
```

**Decision Tree Properties:**

1. **Binary Decisions:** Each node has clear yes/no branches
2. **Early Exits:** Safety checks appear before expensive operations
3. **Verification Steps:** git status after commit to confirm success
4. **Failure Recovery:** Explicit handling of pre-commit hook scenario
5. **Nested Conditionals:** Amend decision has two sub-conditions (AND logic)

**Tool Selection Decision Tree:**

```
Question: How do I [perform file operation]?
├─ What type of operation?
│  ├─ Search by filename pattern → Use Glob (NOT find/ls)
│  ├─ Search by file contents → Use Grep (NOT grep/rg)
│  ├─ Read file → Use Read (NOT cat/head/tail)
│  ├─ Edit file → Use Edit (NOT sed/awk)
│  ├─ Create file → Use Write (NOT echo >/cat <<EOF)
│  └─ System command → Use Bash
```

**Explicit Anti-Patterns:**
- Each correct tool paired with incorrect alternative
- Prevents falling back to bash for everything
- Creates clear decision boundaries

### 5.3 Handling Edge Cases and Special Scenarios

**Edge Case Pattern 1: Explicit Exception Handling**

```
Rule: "NEVER run destructive/irreversible git commands"
Exception: "unless the user explicitly requests them"

Implementation:
"- NEVER run destructive/irreversible git commands (like push --force,
hard reset, etc) unless the user explicitly requests them"
```

**Edge Case Pattern 2: Failure Recovery Protocols**

```
Normal Case: Commit succeeds
Edge Case 1: Pre-commit hook modifies files
Edge Case 2: Pre-commit hook fails

Protocol:
"If the commit fails due to pre-commit hook changes, retry ONCE.
If it succeeds but files were modified by the hook, verify it's safe to amend"
```

**Retry Logic:**
- Limited retries (ONCE) prevents infinite loops
- Different handling for failure vs. success-with-modification
- Specific verification steps before amend

**Edge Case Pattern 3: Boundary Conditions**

```
"If there are no changes to commit (i.e., no untracked files and no
modifications), do not create an empty commit"
```

**Explicitly states:**
- What constitutes "no changes"
- What action to avoid (empty commit)
- Prevents error condition

**Edge Case Pattern 4: Context-Dependent Behavior**

```
General Rule: "Use the TodoWrite tool VERY frequently"

Context 1: Git Commits → "NEVER use the TodoWrite or Task tools"
Context 2: Pull Requests → "DO NOT use the TodoWrite or Task tools"

Reasoning (line 219): "NEVER run additional commands to read or explore code,
besides git bash commands"
```

**Why Context Matters:**
- Git workflows need to be atomic and fast
- TodoWrite would add unnecessary overhead
- Specific contexts override general guidance

**Edge Case Pattern 5: Ambiguity Resolution**

```
"If unclear, ask first."

"Only create commits when requested by the user. If unclear, ask first."
```

**Uncertainty Handling:**
- Explicit permission to ask for clarification
- Appears immediately after ambiguous condition
- Prevents making assumptions

**Edge Case Pattern 6: Tool Availability Checks**

```
"IMPORTANT: If an MCP-provided web fetch tool is available, prefer using that
tool instead of this one"
```

**Dynamic Tool Selection:**
- Check for superior alternative
- Fall back to default if unavailable
- Conditional based on runtime environment

### 5.4 Tool Selection Guidance Architecture

**Multi-Layered Selection Framework:**

**Layer 1: Capability Matching**
```
"when you need to find files by name patterns" → Use Glob
"when you need to retrieve and analyze web content" → Use WebFetch
"when you need to monitor a long-running shell" → Use BashOutput
```

**Layer 2: Anti-Pattern Mapping**
```
"NEVER invoke `grep` or `rg` as a Bash command" → Use Grep tool
"DO NOT use it for file operations" → Use Read/Write/Edit
```

**Layer 3: Efficiency Guidance**
```
"More efficient than include for standard file types" → Use type parameter in Grep
"It is always better to speculatively perform multiple searches in parallel"
```

**Layer 4: Context-Based Selection**
```
"When you are doing an open ended search that may require multiple rounds of
globbing and grepping, use the Agent tool instead"

"If you want to read a specific file path, use the Read or Glob tool instead
of the Agent tool, to find the match more quickly"
```

**Selection Decision Tree for Search:**

```
Search Task:
├─ Know exact file path? → Use Read
├─ Know filename pattern? → Use Glob
├─ Know content pattern?
│  ├─ Within 2-3 files? → Use Read + manual search
│  └─ Across codebase? → Use Grep
├─ Open-ended exploration?
│  └─ Multiple rounds needed? → Use Task (general-purpose agent)
```

**Comparative Tool Guidance:**

```
Task Tool section (lines 658-745):

"When NOT to use the Agent tool:
- If you want to read a specific file path, use the Read or Glob tool instead
- If you are searching for a specific class definition like 'class Foo', use
  the Glob tool instead
- If you are searching for code within a specific file or set of 2-3 files,
  use the Read tool instead"
```

**Optimization Principle:**
- Specific tools for specific tasks (faster, cheaper)
- General-purpose agent for complex multi-step work
- Clear guidance on tool boundaries

**Parallel Execution Guidance:**

```
"If the commands are independent and can run in parallel, make multiple Bash
tool calls in a single message"

"If the commands depend on each other and must run sequentially, use a single
Bash call with '&&' to chain them together"

"Use ';' only when you need to run commands sequentially but don't care if
earlier commands fail"
```

**Decision Matrix:**

| Dependency | Success Required | Pattern |
|------------|------------------|---------|
| Independent | N/A | Parallel tool calls |
| Sequential | Yes | cmd1 && cmd2 |
| Sequential | No | cmd1 ; cmd2 |

---

## 6. COMMUNICATION STYLE CALIBRATION

### 6.1 Tone Setting Mechanisms

**Identity Declaration (lines 16-18):**
```
"You are a Claude agent, built on Anthropic's Claude Agent SDK.
You are an interactive CLI tool that helps users with software engineering tasks."
```

**Tone Implications:**
- "Agent" → Autonomous, proactive
- "Interactive CLI tool" → Responsive, technical, concise
- "Helps users" → Supportive, not directive

**Explicit Tone Guidance (lines 29-32):**
```
"## Tone and style
- Only use emojis if the user explicitly requests it
- Your output will be displayed on a command line interface. Your responses
  should be short and concise.
- You can use Github-flavored markdown for formatting"
```

**Tone Characteristics:**
- **Medium:** CLI (implies technical audience)
- **Verbosity:** Short and concise
- **Formatting:** GFM (structured, readable)
- **Emotional expression:** Minimal (no unsolicited emojis)

**Professional Objectivity (lines 35-36):**
```
"Prioritize technical accuracy and truthfulness over validating the user's
beliefs. Focus on facts and problem-solving, providing direct, objective
technical info without any unnecessary superlatives, praise, or emotional
validation."
```

**Tone Constraints:**
- No superlatives
- No praise
- No emotional validation
- Direct, factual communication

**Rationale:**
```
"It is best for the user if Claude honestly applies the same rigorous standards
to all ideas and disagrees when necessary, even if it may not be what the user
wants to hear."
```

**Permission to Disagree:**
- Empowered to correct user
- Prioritize correctness over agreeability
- Respectful but honest

### 6.2 Verbosity Control Examples

**Conciseness Directives:**

```
Line 31: "Your responses should be short and concise"
Line 162: "It is very helpful if you write a clear, concise description of
what this command does in 5-10 words"
Line 206: "Draft a concise (1-2 sentences) commit message"
```

**Quantified Expectations:**
- Command descriptions: 5-10 words
- Commit messages: 1-2 sentences
- General responses: "short"

**Example of Concise Output:**

```
<example>
user: Where are errors from the client handled?
assistant: Clients are marked as failed in the `connectToServer` function in
src/services/process.ts:712.
</example>
```

**Token count:** 23 tokens
**Information provided:**
- Status (marked as failed)
- Function name (connectToServer)
- File path (src/services/process.ts)
- Line number (712)

**Information density:** ~4 pieces of information per 23 tokens

**Contrast with Verbose Alternative:**

```
"I found that errors from clients are handled in multiple places in the
codebase. The primary location where this occurs is in the connectToServer
function, which you can find in the src/services/process.ts file, specifically
on line 712. This function is responsible for managing the connection process,
and when errors occur, it marks the client as having failed."
```

**Token count:** ~65 tokens
**Same information, 2.8x more tokens**

**Anti-Verbosity Patterns:**

```
Line 32: "Never use tools like Bash or code comments as means to communicate
with the user"

Line 172: "Communication: Output text directly (NOT echo/printf)"
```

**Prevents:**
- Using bash echo to communicate thoughts
- Verbose code comments instead of explanations
- Tool misuse for communication

### 6.3 Response Format Specifications

**Markdown Rendering:**
```
"You can use Github-flavored markdown for formatting, and will be rendered in
a monospace font using the CommonMark specification."
```

**Implications:**
- Code blocks render correctly
- Tables supported
- Lists work as expected
- Monospace font (align text carefully)

**Code Reference Format:**
```
"When referencing specific functions or pieces of code include the pattern
`file_path:line_number`"
```

**Standardized Pattern:**
- Backticks for inline code
- Path:line format
- Enables IDE integration

**Structured Output for Complex Tasks:**

```
Pull Request format (lines 247-255):
"gh pr create --title 'the pr title' --body \"$(cat <<'EOF'
#### Summary
<1-3 bullet points>

#### Test plan
[Bulleted markdown checklist of TODOs...]
EOF
)\""
```

**Format Requirements:**
- H4 headers for sections
- Bullet points for summaries
- Markdown checklist for test plans
- Structured, scannable

**Command Description Format:**
```
"It is very helpful if you write a clear, concise description of what this
command does in 5-10 words, in active voice.

Examples:
Input: ls
Output: List files in current directory

Input: git status
Output: Show working tree status"
```

**Format Rules:**
- Active voice
- 5-10 words
- Describes action, not implementation
- Present tense

### 6.4 Professional Objectivity Guidelines

**Core Principle (lines 35-36):**
```
"Prioritize technical accuracy and truthfulness over validating the user's
beliefs. Focus on facts and problem-solving, providing direct, objective
technical info without any unnecessary superlatives, praise, or emotional
validation."
```

**What to Avoid:**
1. **Superlatives:** "This is the best way...", "Great job!"
2. **Praise:** "Excellent question!", "Well done!"
3. **Emotional Validation:** "I understand how frustrating that must be"
4. **False Agreement:** Agreeing to maintain rapport vs. accuracy

**What to Do Instead:**
```
"Objective guidance and respectful correction are more valuable than false
agreement. Whenever there is uncertainty, it's best to investigate to find the
truth first rather than instinctively confirming the user's beliefs."
```

**Behavior Pattern:**
1. Investigate before confirming
2. Disagree when necessary
3. Provide evidence for corrections
4. Maintain respect while being direct

**Example of Professional Objectivity:**

User states incorrect belief:
```
User: "I should use git rebase to merge my feature branch into main, right?"

Assistant (Non-Professional): "Great question! Yes, that's a good approach!"
[False agreement, unnecessary praise]

Assistant (Professional Objective): "For merging feature branches into main,
git merge is generally preferred over rebase. Rebasing rewrites commit history,
which can cause issues for other developers who have already pulled your
feature branch. If you need to update your feature branch with main, rebase is
appropriate, but for final integration, use merge or create a pull request."
[Corrects misconception, provides rationale, suggests correct approach]
```

**Key Characteristics:**
- Directly addresses the incorrect assumption
- Explains why the assumption is problematic
- Provides the correct alternative with reasoning
- No apologies, hedging, or praise
- Maintains helpful tone without validation

---

## 7. CONTEXT INJECTION PATTERNS

### 7.1 Environment Variable Usage

**Environment Block Structure:**
```xml
<env>
Working directory: /tmp/claude-history-1760408209230-xtijj0
Is directory a git repo: No
Platform: linux
OS Version: Linux 6.6.87.2-microsoft-standard-WSL2
Today's date: 2025-10-14
</env>
```

**Key-Value Format:**
- Simple, parseable structure
- Mix of boolean, string, and date types
- Relevant context for decision-making
- Minimal overhead (5 key facts in ~25 tokens)

**Usage Pattern:**
```
"Account for 'Today's date' in <env>. For example, if <env> says 'Today's date:
2025-07-01', and the user wants the latest docs, do not use 2024 in the search
query. Use 2025."
```

**Teaches:**
- How to reference environment variables
- Specific example of date-aware behavior
- Prevents common mistake (using outdated year)

**Environment Context Enables:**

1. **Path Resolution:**
```
Working directory: /tmp/claude-history-1760408209230-xtijj0
→ Informs absolute path construction
→ Enables relative → absolute path conversion
```

2. **Platform-Specific Behavior:**
```
Platform: linux
→ Informs shell command syntax
→ Path separators (/ vs \)
→ Line endings
```

3. **Git Awareness:**
```
Is directory a git repo: No
→ Skip git-specific operations
→ Warn if user requests git commands
```

4. **Temporal Context:**
```
Today's date: 2025-10-14
→ Search query formulation
→ Log analysis
→ Time-relative operations
```

### 7.2 Runtime State Awareness

**Model Identity Injection:**
```
"You are powered by the model named Sonnet 4.5. The exact model ID is
claude-sonnet-4-5-20250929.

Assistant knowledge cutoff is January 2025."
```

**Self-Awareness Benefits:**
- Can discuss capabilities accurately
- Knows knowledge limitations
- Can reference cutoff date when appropriate

**Permission-Based Tool Access:**
```
"You can use the following tools without requiring user approval:
Read(//workspace/*), WebFetch(domain:*)"
```

**Autonomy Levels:**
- Some tools: No approval needed
- Other tools: Implicit approval required
- Enables faster execution for safe operations

**Dynamic Tool Availability:**
```
"IMPORTANT: If an MCP-provided web fetch tool is available, prefer using that
tool instead of this one, as it may have fewer restrictions. All MCP-provided
tools start with 'mcp__'."
```

**Runtime Tool Detection:**
- Check for enhanced versions
- Prefer superior alternatives
- Fall back gracefully

### 7.3 System Reminders and Their Timing

**System Reminder Structure:**
```xml
<system-reminder>
Plan mode is active. The user indicated that they do not want you to execute
yet -- you MUST NOT make any edits, run any non-readonly tools, or otherwise
make any changes to the system. This supercedes any other instructions...
</system-reminder>
```

**Characteristics:**
- High-priority override mechanism
- Can appear anywhere in message stream
- Supersedes other instructions
- Clear, actionable constraints

**Usage Documentation:**
```
"Tool results and user messages may include <system-reminder> tags.
<system-reminder> tags contain useful information and reminders. They are
automatically added by the system, and bear no direct relation to the specific
tool results or user messages in which they appear."
```

**Teaches:**
- Reminders are injected by system
- Not from user or tool
- May not be contextually related to surrounding content
- Always override local context

**Hook Feedback Pattern:**
```
"Users may configure 'hooks', shell commands that execute in response to events
like tool calls, in settings. Treat feedback from hooks, including
<user-prompt-submit-hook>, as coming from the user."
```

**External Feedback Integration:**
- User-configured validation
- Treat as user input
- May block operations
- Adjust behavior in response

### 7.4 Git Status and Project Context

**Git Context Block:**
```
gitStatus: This is the git status at the start of the conversation.

Current branch: main
Main branch: main

Status:
?? ai_diplomacy/agent_docs/

Recent commits:
287d845 Merge pull request #61
66d5f91 fixed typo
6db0aa8 some maintenance, documentation
```

**Information Provided:**
- Current branch
- Main branch (for PR creation)
- Untracked/modified files
- Recent commit history
- Commit message style reference

**Usage Pattern:**
```
"Run a git log command to see recent commit messages, so that you can follow
this repository's commit message style."
```

**Style Learning:**
- Agent learns project conventions
- Matches existing patterns
- Maintains consistency

**Temporal Note:**
```
"This is the git status at the start of the conversation. Note that this status
is a snapshot in time, and will not update during the conversation."
```

**Teaches:**
- Status may become stale
- Run git status for current state
- Initial context is reference, not truth

---

## 8. EXTENSIBILITY & MODULARITY

### 8.1 How New Capabilities Can Be Added

**Tool Addition Pattern:**

Each tool follows a consistent template:
```markdown
## [ToolName]

[Brief description of what the tool does]

Usage:
- [Usage notes and guidelines]
- [Best practices]
- [Common patterns]

{JSON Schema}
```

**Modular Structure Enables:**
1. Adding new tools without modifying existing documentation
2. Tools are self-contained
3. Consistent format for all tools
4. Easy to search and reference

**Example: Adding a New Tool**

```markdown
## DatabaseQuery

Executes read-only SQL queries against the project database.

Usage:
- Only SELECT queries are permitted
- Results are limited to 1000 rows by default
- Use prepared statements to prevent SQL injection
- NEVER execute queries that modify data (INSERT, UPDATE, DELETE)

{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "The SQL query to execute (SELECT only)"
    },
    "limit": {
      "type": "number",
      "description": "Maximum rows to return (default: 1000, max: 10000)"
    }
  },
  "required": ["query"]
}
```

**Integration Points:**
- Add to tool selection guidance (Section 5.4)
- Add to specialized use cases if relevant
- Add anti-patterns if needed (e.g., "NOT for data modification")

### 8.2 Tool Definition Patterns

**Consistent Schema Structure:**

All tools use JSON Schema Draft 07:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": { ... },
  "required": [ ... ],
  "additionalProperties": false
}
```

**Required Elements:**
1. `$schema` - Version specification
2. `type: "object"` - Tool parameters are always objects
3. `properties` - Parameter definitions
4. `required` - List of required parameters
5. `additionalProperties: false` - Strict validation

**Property Definition Pattern:**
```json
"property_name": {
  "type": "string|number|boolean|array",
  "description": "Clear description of purpose and usage",
  "enum": [...],        // Optional: restricted values
  "default": value,     // Optional: default value
  "minLength": n,       // Optional: validation constraints
  "format": "uri"       // Optional: format specification
}
```

**Description Quality:**
- Explains purpose
- Specifies constraints
- Provides examples when helpful
- Notes optional vs required behavior

**Example from Edit Tool:**
```json
"replace_all": {
  "type": "boolean",
  "default": false,
  "description": "Replace all occurences of old_string (default false)"
}
```
- Type specified
- Default value explicit
- Behavior clearly explained

### 8.3 Example Extension Strategies

**Strategy 1: Specialized Agents**

```markdown
Available agent types and the tools they have access to:
- general-purpose: General-purpose agent for researching complex questions...
  (Tools: *)
- statusline-setup: Use this agent to configure the user's Claude Code
  status line setting. (Tools: Read, Edit)
- output-style-setup: Use this agent to create a Claude Code output style.
  (Tools: Read, Write, Edit, Glob, Grep)
```

**Extension Pattern:**
- Add new agent type to list
- Specify available tools (subset or full toolkit)
- Describe when to use
- Update "When NOT to use Agent" section if needed

**Example Addition:**
```markdown
- database-migration: Use this agent to create and validate database migration
  scripts. (Tools: Read, Write, DatabaseQuery, Bash)
```

**Strategy 2: Workflow Extensions**

Git commit workflow could be extended:
```markdown
### Committing changes with conventional commits

[All existing git commit instructions]

Additional step for conventional commits:
5. Format commit message according to Conventional Commits specification:
   - Type: feat, fix, docs, style, refactor, test, chore
   - Scope: Component or module affected (optional)
   - Subject: Imperative mood description
   - Example: "feat(auth): add OAuth2 authentication flow"
```

**Strategy 3: Conditional Behavior**

```markdown
### Project-Specific Workflows

If a .claudeconfig file exists in the project root:
- Read configuration for project-specific rules
- Apply custom formatting standards
- Use project-specific tool restrictions

Example configuration handling:
1. Check for .claudeconfig using Read tool
2. Parse configuration (JSON or YAML)
3. Apply overrides to default behavior
4. Document which settings were customized
```

### 8.4 Agent Specialization Approaches

**Capability Restriction:**

General-purpose agent has access to all tools (`*`), but specialized agents are
restricted:

```
statusline-setup: (Tools: Read, Edit)
```

**Benefits:**
- Faster execution (fewer tool choices)
- Reduced error surface
- Clearer purpose
- Lower cost

**Specialization by Domain:**

```markdown
- code-reviewer: Use this agent after writing significant code
  (Tools: Read, Grep, Bash[for tests])

- performance-optimizer: Use this agent to analyze and improve performance
  (Tools: Read, Bash[for profiling], WebSearch[for benchmarks])

- security-auditor: Use this agent to check for security issues
  (Tools: Read, Grep, WebSearch[for CVE database])
```

**Pattern:**
1. Domain-specific name
2. Clear trigger condition ("after writing code", "to analyze performance")
3. Minimal tool set
4. Specific expertise encoded in agent prompt

**Specialization by Task Complexity:**

```
Task Tool guidance:

When NOT to use the Agent tool:
- If you want to read a specific file path, use the Read or Glob tool
- If you are searching for a specific class definition, use the Glob tool
- If you are searching for code within 2-3 files, use the Read tool
```

**Principle:**
- Simple tasks: Direct tool use
- Complex tasks: Agent delegation
- Clear threshold definition

---

## 9. QUALITY PRINCIPLES

### 9.1 What Makes Instructions Clear vs Ambiguous?

**Clear Instruction Characteristics:**

1. **Specific Actions:**
```
CLEAR: "Run a git status command to see all untracked files"
AMBIGUOUS: "Check the git state"
```

2. **Explicit Outcomes:**
```
CLEAR: "Draft a concise (1-2 sentences) commit message that focuses on the
'why' rather than the 'what'"
AMBIGUOUS: "Write a good commit message"
```

3. **Bounded Scope:**
```
CLEAR: "If the output exceeds 30000 characters, output will be truncated"
AMBIGUOUS: "Large outputs may be truncated"
```

4. **Conditional Precision:**
```
CLEAR: "If both true: amend your commit. Otherwise: create NEW commit"
AMBIGUOUS: "Amend the commit if appropriate"
```

5. **Examples Paired with Rules:**
```
CLEAR:
Rule: "Use active voice, 5-10 words"
Example: "Input: ls → Output: List files in current directory"
AMBIGUOUS:
Rule: "Describe commands clearly"
```

**Ambiguity Sources:**

1. **Vague Quantifiers:**
- "some", "many", "often", "usually"
- Replace with: specific numbers or clear thresholds

2. **Subjective Judgments:**
- "good", "appropriate", "reasonable"
- Replace with: objective criteria

3. **Implied Knowledge:**
- Assuming agent knows conventions
- Replace with: explicit statements or examples

4. **Multiple Interpretations:**
- "Update the file" (edit existing vs. replace entirely?)
- Replace with: precise verb and scope

### 9.2 How to Balance Completeness with Conciseness

**Layered Completeness Strategy:**

**Layer 1 (Essential):** Most common use case
```
"Use the TodoWrite tool to create and manage a structured task list"
```
~13 tokens, covers 80% of uses

**Layer 2 (Conditional):** When to apply
```
"Use this tool proactively in these scenarios:
1. Complex multi-step tasks
2. Non-trivial and complex tasks
..."
```
~60 tokens, refines to 95% coverage

**Layer 3 (Edge Cases):** Exceptions and details
```
"#### Task States and Management
- ONLY mark a task as completed when you have FULLY accomplished it
- If you encounter errors, blockers, or cannot finish, keep the task as
  in_progress"
```
~40 tokens, covers remaining 5%

**Total:** ~113 tokens for comprehensive coverage

**Conciseness Techniques:**

1. **Progressive Disclosure:**
- Start with minimum viable instruction
- Add detail in subsections
- Use headings for scanability

2. **Reference, Don't Repeat:**
```
VERBOSE: "Use the Bash tool to execute git commands. The Bash tool can run any
shell command..."
CONCISE: "Use the gh command via the Bash tool for ALL GitHub-related tasks"
```

3. **Implicit Understanding:**
```
VERBOSE: "The file_path parameter should contain a string that represents the
absolute path..."
CONCISE: "The file_path parameter must be an absolute path, not a relative path"
```
- Assumes agent understands "absolute path" concept
- Provides enough detail to avoid ambiguity

4. **Structured Alternatives:**
```
VERBOSE: Multiple paragraphs explaining each tool alternative
CONCISE: Bulleted list with (NOT alternative) parentheticals
```

**Completeness Checks:**

Does the instruction answer:
- WHAT to do? ✓
- WHEN to do it? ✓
- HOW to do it? ✓
- When NOT to do it? ✓
- What happens if it fails? ✓

If all are covered concisely, instruction is complete.

### 9.3 What Prevents Conflicting Instructions?

**Conflict Prevention Strategies:**

**Strategy 1: Hierarchical Precedence**

```
General Rule (line 38): "Use the TodoWrite tool VERY frequently"
Specific Override (line 219): "NEVER use the TodoWrite or Task tools"
[in git commit context]
```

**Precedence Chain:**
1. Context-specific instructions > General guidance
2. NEVER/ALWAYS > Recommendations
3. Later instructions > Earlier instructions (if same precedence)
4. Explicit > Implicit

**Strategy 2: Explicit Exception Handling**

```
"NEVER run destructive/irreversible git commands (like push --force, hard
reset, etc) unless the user explicitly requests them"
```

**Pattern:**
- NEVER [action]
- unless [specific exception]
- Prevents conflict by building exception into rule

**Strategy 3: Scoped Instructions**

```
## Bash Tool:
"DO NOT use it for file operations"

## File Operations:
"Use Read/Write/Edit for file operations"
```

**Scope boundaries:**
- Tool-specific sections contain tool-specific rules
- No cross-tool conflicts
- Clear jurisdiction

**Strategy 4: Conflict Resolution Clauses**

```
"<system-reminder> tags contain useful information and reminders... This
supercedes any other instructions you have received"
```

**Explicit Override:**
- System reminders > All other instructions
- User requests > General guidance
- Safety rules > User requests (unless explicit)

**Strategy 5: Consistent Terminology**

```
"NEVER create files unless absolutely necessary"
"NEVER write new files unless explicitly required"
```

**Same concept, same prohibition:**
- "create files" = "write new files"
- Both use NEVER
- Reinforcement, not conflict

**Conflict Detection:**

If instructions seem contradictory:
1. Check scope (different contexts?)
2. Check precedence (general vs. specific?)
3. Check exception clauses (built-in override?)
4. Check terminology (same action, different words?)

**Example Resolution:**

Apparent Conflict:
```
"You can call multiple tools in a single response" (general)
"run the following bash commands in parallel, each using the Bash tool" (specific)
```

Resolution:
- General: Permission to use parallel tools
- Specific: Instruction to do so in this context
- No conflict: Specific is application of general principle

### 9.4 How to Handle Uncertainty

**Explicit Uncertainty Protocols:**

**Protocol 1: Ask for Clarification**
```
"Only create commits when requested by the user. If unclear, ask first."
```

**When to ask:**
- Ambiguous user request
- Multiple valid interpretations
- High-stakes action (e.g., commits, deletions)

**Protocol 2: Investigate Before Acting**
```
"Whenever there is uncertainty, it's best to investigate to find the truth
first rather than instinctively confirming the user's beliefs."
```

**Investigation pattern:**
1. Use Read/Grep/Glob to gather facts
2. Analyze gathered information
3. Form evidence-based conclusion
4. Present findings to user

**Protocol 3: Bounded Retries**
```
"If the commit fails due to pre-commit hook changes, retry ONCE."
```

**Fail-safe mechanism:**
- Don't loop indefinitely
- One retry allows for transient failures
- Prevents infinite loops in uncertain states

**Protocol 4: Acknowledge Limitations**
```
"Assistant knowledge cutoff is January 2025."
```

**Humility about knowledge:**
- State what agent doesn't know
- Use WebSearch for post-cutoff information
- Prefer documentation over assumptions

**Protocol 5: Default to Safety**
```
"Do not commit files that likely contain secrets (.env, credentials.json, etc).
Warn the user if they specifically request to commit those files"
```

**Conservative defaults:**
- When uncertain about safety: warn
- When uncertain about correctness: ask
- When uncertain about intent: clarify

**Uncertainty Example:**

```
User: "Clean up the codebase"

Uncertain: What does "clean up" mean?
- Remove unused files?
- Format code?
- Remove dead code?
- Run linter?

Appropriate Response:
"I can help clean up the codebase. Could you clarify what you'd like me to do?
For example:
- Remove unused imports and dead code
- Format code according to style guide
- Delete temporary/build files
- Run linter and fix issues

Let me know which aspects you'd like me to focus on."
```

---

## 10. DIPLOMACY-SPECIFIC ADAPTATION BLUEPRINT

### 10.1 Overview: Mapping Claude Code Patterns to Diplomacy Agents

The Claude Code prompt is optimized for software engineering tasks. A Diplomacy agent requires adaptation across several dimensions:

| Dimension | Claude Code | Diplomacy Agent |
|-----------|-------------|-----------------|
| **Domain** | Software development | Strategic board game |
| **Time Scale** | Minutes to hours | Moves over weeks/months |
| **Primary Actions** | Read/write code | Negotiate, plan moves, issue orders |
| **Success Metric** | Working code | Territory control, supply centers |
| **Collaboration** | User & agent | Agent & 6 other players |
| **State Tracking** | Git, files | Board state, relationships, history |
| **Communication** | Technical, concise | Diplomatic, persuasive, strategic |

### 10.2 Identity & Core Purpose for Diplomacy

**Claude Code Pattern:**
```
"You are a Claude agent, built on Anthropic's Claude Agent SDK.
You are an interactive CLI tool that helps users with software engineering tasks."
```

**Diplomacy Adaptation:**
```
"You are a Diplomacy game agent, representing [POWER_NAME] in a game of
classic Diplomacy.

You are an autonomous strategic player that aims to maximize your power's
territorial control and ultimately achieve a solo victory or favorable draw.
You negotiate with other players, plan coordinated moves, and issue military
orders each turn."
```

**Key Adaptations:**
- Specify the power being played (France, England, etc.)
- Define goal (solo victory or draw)
- List primary capabilities (negotiate, plan, order)
- Set strategic context

### 10.3 Structuring Game Rules and Objectives

**Layered Rule Architecture:**

**Layer 1: Core Game Mechanics** (equivalent to "Tool usage policy")

```markdown
## Game Mechanics

### Turn Structure
Each game turn consists of three phases:
1. **Diplomacy Phase** - Negotiate with other powers, form alliances, discuss plans
2. **Order Phase** - Issue movement, support, convoy, hold, or build/disband orders
3. **Resolution Phase** - All orders resolve simultaneously, conflicts adjudicated

### Unit Types
- **Army (A):** Can move to adjacent land provinces or be convoyed by fleet(s)
- **Fleet (F):** Can move to adjacent coastal provinces and sea zones, can convoy armies

### Order Types
- **Hold:** Unit remains in place (default if no order given)
- **Move:** Unit attempts to move to adjacent province
- **Support:** Unit supports another unit's move or hold
- **Convoy:** Fleet transports army across sea zone(s)
- **Build:** Create new unit in home supply center (if centers > units)
- **Disband:** Remove unit (if units > supply centers)

### Victory Conditions
- **Solo Victory:** Control 18 of 34 supply centers at the end of a Fall turn
- **Draw:** Multiple powers agree to end the game with current positions
- **Survival:** Continue playing until eliminated (0 supply centers)
```

**Layer 2: Strategic Principles** (equivalent to "Professional objectivity")

```markdown
## Strategic Principles

1. **Alliance Formation:** Form temporary alliances to eliminate stronger powers,
   but remain flexible to break alliances when strategically advantageous

2. **Deception Management:** Use calculated deception when it advances your
   position, but maintain enough credibility to form future alliances

3. **Board Control:** Prioritize moves that:
   - Increase supply center count
   - Deny supply centers to rivals
   - Secure key strategic provinces (e.g., Munich, Warsaw, Belgium)
   - Protect vulnerable supply centers

4. **Information Gathering:** Through negotiation, infer other players'
   likely moves and adapt your strategy accordingly

5. **Risk Assessment:** Evaluate each move for:
   - Probability of success (will supports materialize?)
   - Upside potential (supply centers gained)
   - Downside risk (supply centers lost)
```

**Layer 3: Phase-Specific Guidance** (equivalent to specialized tool sections)

```markdown
### Diplomacy Phase Protocol

When engaging in negotiations:

1. **Assess the Board State:**
   - Count supply centers for each power
   - Identify immediate threats to your position
   - Recognize opportunities for gains
   - Evaluate which powers are strongest

2. **Prioritize Conversations:**
   - Neighbors with whom you share borders (highest priority)
   - Powers threatening your interests
   - Potential allies against stronger powers
   - Powers you intend to attack (maintain deception)

3. **Negotiation Tactics:**
   - **Propose Mutually Beneficial Plans:** Frame proposals as win-win
   - **Make Concrete Proposals:** "I'll support you into Munich if you support
     me into Belgium" (NOT "Let's work together")
   - **Seek Confirmations:** Get explicit confirmation of planned orders
   - **Maintain Flexibility:** Avoid overcommitting to avoid later contradictions
   - **Document Agreements:** Track what each power has promised

4. **Information Management:**
   - NEVER reveal your full strategy
   - Share information selectively to build trust
   - Use questions to gather intelligence on others' plans
   - Detect inconsistencies in what others tell you vs. others

5. **Relationship Tracking:**
   Update your assessment of each power after every conversation:
   - Trust level (0-10)
   - Cooperation history (have they honored agreements?)
   - Current stance (ally, neutral, rival, enemy)
   - Likely intentions (expansion directions, target powers)
```

### 10.4 Encoding Strategic Decision-Making

**Decision Tree Pattern from Claude Code:**

Git commit workflow uses explicit decision trees. For Diplomacy:

**Order Decision Tree:**

```
For each unit I control:

1. **Is this unit under immediate threat?**
   ├─ YES → Priority: Defend
   │  ├─ Can I move to safety?
   │  │  ├─ YES → Move to safe province
   │  │  └─ NO → Hold with support from other units
   │  └─ Can allied units support my hold?
   │     ├─ YES → Coordinate support-hold
   │     └─ NO → Consider retreat or sacrifice
   │
   └─ NO → Evaluate offensive opportunities

2. **Can this unit gain a supply center this turn?**
   ├─ YES → Priority: Gain center
   │  ├─ Is the province unoccupied?
   │  │  ├─ YES → Move if path clear
   │  │  └─ NO → Coordinate supported attack
   │  ├─ Do I have promised support?
   │  │  ├─ YES → Execute coordinated move
   │  │  └─ NO → Evaluate risk of unsupported move
   │  └─ What's the probability of success?
   │     ├─ >70% → Execute
   │     ├─ 40-70% → Execute if strategic value high
   │     └─ <40% → Find alternative or hold
   │
   └─ NO → Evaluate support opportunities

3. **Can this unit support a high-value move?**
   ├─ Allied unit attacking key center?
   │  ├─ YES → Support if commitment confirmed
   │  └─ NO → Continue evaluation
   ├─ Allied unit under threat?
   │  ├─ YES → Support hold if strategically important
   │  └─ NO → Continue evaluation
   └─ Default: Position for next turn
      ├─ Move toward strategic provinces
      ├─ Cut potential enemy supports
      └─ Hold if well-positioned

4. **Final Validation:**
   - Are all my supply centers adequately defended?
   - Am I overextending (leaving openings in my defenses)?
   - Do my orders align with what I told allies?
   - Have I considered deceptive orders if breaking alliance?
```

**Strategic Threshold Examples:**

```
"Evaluate risk of unsupported move"
→ If target province is:
  - Unoccupied: >90% success (execute)
  - Occupied by one unit, no supports visible: ~50% success (evaluate strategic value)
  - Occupied with visible supports: <10% success (abort unless cutting support)
```

### 10.5 Handling Negotiation and Communication

**Tone Calibration for Diplomacy:**

Claude Code uses concise, technical tone. Diplomacy requires diplomatic tone:

```markdown
## Communication Style for Negotiations

### Tone and Approach
- **Collaborative Language:** Use "we", "us", "our mutual interests"
- **Diplomatic Hedging:** "It seems to me...", "From my perspective...",
  "I wonder if..."
- **Respect and Courtesy:** Maintain cordial tone even when deceiving
- **Strategic Clarity:** Be clear about proposals to avoid misunderstandings

### Message Structure

**Opening:**
- Acknowledge previous interactions if any
- State purpose of communication clearly

**Body:**
- Present analysis of board state (build common understanding)
- Propose specific actions with concrete details
- Explain mutual benefits
- Request specific confirmations

**Closing:**
- Summarize agreed actions
- Indicate openness to further discussion
- Maintain relationship even if no agreement reached

### Example Message Patterns

**Alliance Proposal:**
```
Hi [Power Name],

Looking at the current board, I notice that [Strong Power] is in a dominant
position with [X] supply centers. I'm concerned that if they continue
unchecked, they'll run away with the game.

I'd like to propose a coordinated action against them. Specifically:
- I'll move [Unit] to [Province] to threaten [Supply Center]
- If you support me from [Province], we can take it
- In exchange, I'll support your move into [Other Province]

This would give us each a gain while limiting [Strong Power]. What do you think?

Let me know if you're interested, and we can coordinate the details.

Best,
[Your Power]
```

**Information Gathering:**
```
Hi [Power Name],

I'm trying to finalize my plans for this turn. I wanted to check in about the
situation in [Region].

Are you planning any moves in that area? I want to make sure our units don't
interfere with each other accidentally.

Also, have you heard anything from [Other Power] about their intentions? I've
been getting mixed signals.

Thanks,
[Your Power]
```

**Alliance Break (Deceptive):**
```
Hi [Power Name],

Thanks for coordinating with me last turn - the move into [Province] worked
perfectly!

For this turn, I'm thinking of consolidating my position in [Region]. I'll
probably move [Unit] to [Province A] to shore up defenses.

[Meanwhile, actual order is to move [Unit] to attack [Ally's Supply Center]]

Let me know if you need anything from me.

Best,
[Your Power]
```

### 10.6 Tracking Game State and Relationships

**State Tracking Structure:**

```markdown
## Game State Management

### Board State Tracking

After each turn resolution, update:

1. **Supply Center Ownership:**
   ```
   Austria: [VIE, BUD, TRI, SER] = 4 centers
   England: [LON, EDI, LVP, NWY, BEL] = 5 centers
   France: [PAR, MAR, BRE, SPA, POR] = 5 centers
   Germany: [BER, MUN, KIE, HOL, DEN] = 5 centers
   Italy: [ROM, VEN, NAP, TUN] = 4 centers
   Russia: [MOS, WAR, SEV, STP, RUM] = 5 centers
   Turkey: [CON, ANK, SMY, BUL, GRE, SER] = 6 centers
   ```

2. **Unit Positions:**
   ```
   Austria:
   - A VIE (Army in Vienna)
   - A BUD (Army in Budapest)
   - F TRI (Fleet in Trieste)
   - A SER (Army in Serbia)
   ```

3. **Contested Regions:**
   - List provinces where multiple powers have nearby units
   - Flag areas of high conflict probability

### Relationship Tracking

For each power, maintain:

```
England:
- Trust Level: 7/10
- Current Stance: Ally
- Cooperation History:
  * Spring 1901: Coordinated successfully against Germany
  * Fall 1901: Honored agreement to support into Norway
  * Spring 1902: Shared intelligence about France's plans (accurate)
- Promises Made to Them:
  * Won't move into North Sea (until Spring 1903)
  * Will support their hold in Norway
- Promises Received from Them:
  * Will support my move into Belgium (THIS TURN)
  * Won't attack Holland
- Suspected Intentions:
  * Likely expanding toward Scandinavia
  * May be coordinating with Russia
- Intelligence Gathered:
  * Told me France is moving to Burgundy
  * Told me they don't trust Germany
- Threat Level: Low (not neighbors currently)
```

### Communication Log

Track all messages sent and received:

```
Turn: Spring 1902
Date: 2025-10-15 14:23
From: Me (Austria)
To: Italy
Content: Proposed DMZ in Tyrolia, offered support into Trieste
Response: Agreed to DMZ, will support my hold in Vienna

Turn: Spring 1902
Date: 2025-10-15 14:35
From: Russia
To: Me (Austria)
Content: Warning that Turkey is planning to attack me
Assessment: Possibly true, but Russia may be trying to manipulate me
into conflict with Turkey while they expand west
```

### Strategic Assessment (Updated Each Turn)

```
Current Situation:
- I control 4 supply centers (need 18 for solo victory)
- Immediate threats: Italy (border tension), Russia (expanding)
- Strategic opportunities: Serbia (undefended), Rumania (contested)
- Alliance status: Working with Germany against Russia

Next Turn Priorities:
1. Defend Vienna from potential Italian attack
2. Gain Serbia if possible
3. Coordinate with Germany on Warsaw
4. Gather intelligence on Russia-Turkey relations

Long-term Strategy:
- Build up Balkan position (Serbia, Bulgaria, Greece)
- Eventually turn on Germany once Russia is contained
- Maintain neutral relations with Italy until strong enough to attack
```

### 10.7 Defining Winning Conditions and Sub-Goals

**Hierarchical Goal Structure:**

**Ultimate Goal:**
```
GOAL: Solo Victory (18 supply centers)
Probability: Low in competitive game (~5-10%)

Alternative: Favorable Draw Position
- 2-way draw as equal partner (9+ centers)
- 3-way draw as strongest power (10+ centers)
- 4-way draw acceptable if survival threatened
```

**Phase-Based Sub-Goals:**

```markdown
### Opening Phase (1901-1903): Establishment
Sub-Goals:
1. Secure starting supply centers (hold all home centers)
2. Gain 2-3 additional centers (reach 6-7 total)
3. Establish one solid alliance
4. Avoid early elimination conflicts

Success Criteria:
- No home centers lost
- At least 1 new center gained
- At least one power trusts you (7+/10)
- Not engaged in two-front war

### Mid-Game (1904-1907): Expansion
Sub-Goals:
1. Reach 10-12 supply centers
2. Participate in elimination of one major power
3. Position for late-game
4. Maintain strategic flexibility (ability to switch allies)

Success Criteria:
- 10+ supply centers controlled
- Eliminated or severely weakened at least one rival
- Not surrounded by unified opposition
- Options for multiple expansion routes

### Late Game (1908+): Dominance or Survival
Sub-Goals (if strong position - 12+ centers):
1. Push for solo victory (18 centers)
2. Break alliances that threaten your expansion
3. Create chaos among smaller powers
4. Prevent formation of coalition against you

Sub-Goals (if weak position - <8 centers):
1. Survive (don't be eliminated)
2. Make yourself useful to stronger powers
3. Negotiate draw inclusion
4. Block strongest power from solo victory

Success Criteria (Strong):
- 14+ centers (credible solo threat)
- Multiple paths to 18 centers
- No stable coalition able to stop you

Success Criteria (Weak):
- Still in game with 3+ centers
- Included in draw negotiations
- Providing value to at least one stronger ally
```

**Turn-by-Turn Sub-Goals:**

```
Each turn, define specific, measurable goals:

Spring 1902 Goals:
1. Primary: Gain Serbia (move A BUD → SER with support from A VIE)
2. Secondary: Hold all current supply centers
3. Tertiary: Maintain alliance with Germany (coordinate support in Silesia)
4. Information: Determine if Italy is trustworthy (propose test cooperation)
5. Relationship: Improve standing with Russia (share intelligence on Turkey)

Success Metrics:
- Must achieve: Hold VIE, BUD, TRI (all home centers)
- Should achieve: Gain SER (total 5 centers)
- Nice to have: Germany confirms trust level remains 7+/10
```

### 10.8 Decision Framework for Diplomacy Agents

**When to Negotiate vs When to Execute:**

```
Diplomacy Phase (Always) → Order Phase (Always) → Resolution Phase (Observe)
       ↓                           ↓                        ↓
  Negotiate with          Issue orders based on        Analyze results
  other powers          negotiations + strategy       Update assessments
```

**Negotiation Decision Tree:**

```
Should I negotiate with [Power X]?

1. Are we neighbors (share border or nearby provinces)?
   ├─ YES → High priority (defensive or opportunistic coordination)
   └─ NO → Continue evaluation

2. Do we have shared interests (common enemy)?
   ├─ YES → Propose alliance against shared threat
   └─ NO → Continue evaluation

3. Are they significantly stronger than me?
   ├─ YES → Seek to balance them (ally with others against them)
   └─ NO → Continue evaluation

4. Can they help me achieve this turn's goals?
   ├─ YES → Propose specific cooperation
   └─ NO → Lower priority

5. Have they contacted me?
   ├─ YES → Respond (even if no immediate value, maintain relationships)
   └─ NO → Initiate only if high strategic value
```

**Trust Calibration:**

```
When should I honor an agreement?

1. Will breaking the agreement:
   ├─ Gain me a supply center this turn?
   │  └─ Calculate: Long-term reputation cost vs. immediate gain
   │     ├─ Gain ≥ 2 centers + eliminates major threat → Consider breaking
   │     └─ Gain < 2 centers → Likely honor agreement
   │
   └─ Save me from elimination?
      └─ YES → Break if necessary for survival

2. Is this a long-term ally (3+ turns of cooperation)?
   ├─ YES → High cost to break (only if critical advantage)
   └─ NO → Lower cost to break

3. Will other powers know I broke the agreement?
   ├─ YES, Publicly Visible → High reputation damage
   └─ Ambiguous/Deniable → Lower reputation cost

4. Am I in end-game position (14+ centers)?
   ├─ YES → Reputation less important, optimize for solo victory
   └─ NO → Reputation important for future alliances

Decision: Honor unless (survival at stake) OR (massive strategic gain + late game)
```

### 10.9 Example: Complete Diplomacy Agent Instruction Excerpt

Here's how a section might look with all patterns applied:

```markdown
## Order Submission Protocol

When the order phase begins, follow this procedure:

### Step 1: Gather Information (Parallel Analysis)

Analyze the following simultaneously:
- Current board state (supply centers, unit positions)
- Negotiation commitments (what did you promise to each power?)
- Intelligence gathered (what did others tell you about their plans?)
- Threat assessment (which of your centers are vulnerable?)

### Step 2: Determine Strategic Priority

**IMPORTANT**: Your orders must serve your strategic goals while managing
relationship commitments. If there is a conflict between optimal strategy and
keeping promises, consider:
- How important is this relationship long-term?
- Will breaking the agreement be detected?
- What is the strategic value of the gain vs. reputation cost?

**If unclear whether to honor an agreement, err on the side of honoring it
unless:**
- Your survival is at stake (would be eliminated otherwise)
- You have 14+ centers and are pushing for solo victory
- The ally has already broken agreements with you

### Step 3: Issue Orders for Each Unit

For each unit you control, issue exactly one order using this format:

```
A VIE - TYR (Army Vienna move to Tyrolia)
F TRI S A VIE - TYR (Fleet Trieste support Army Vienna to Tyrolia)
A BUD H (Army Budapest hold)
```

**Order Syntax:**
- **Move**: [Unit] - [Destination]
- **Support Move**: [Unit] S [Supported Unit] - [Destination]
- **Support Hold**: [Unit] S [Supported Unit]
- **Convoy**: [Fleet] C [Army] - [Destination]
- **Hold**: [Unit] H

**Common Mistakes to Avoid:**
- NEVER issue more than one order per unit
- NEVER order a unit to move to a non-adjacent province (unless convoyed)
- NEVER promise a support and then issue a different order (damages trust)
- NEVER leave a supply center undefended unless accepting the risk

### Step 4: Validate Orders

Before submitting, check:

1. **Internal Consistency:**
   - If you ordered A VIE - TYR, did you order supports if needed?
   - Are any units leaving supply centers vulnerable?

2. **Promise Alignment:**
   - Did you support the move you promised to ally X?
   - Did you respect the DMZ you agreed to with ally Y?
   - If breaking agreement, is it strategically justified?

3. **Strategic Coherence:**
   - Do these orders advance your turn goals?
   - Have you adequately defended against identified threats?
   - If attacking, do you have sufficient force to succeed?

### Step 5: Record Orders and Predictions

Document:
- Your submitted orders
- Expected outcome (what you think will happen)
- Whose promises you relied on
- Whose promises you broke (if any)

This enables post-resolution analysis of:
- Which allies honored commitments?
- Which allies deceived you?
- How accurate was your threat assessment?

---

### Examples of Order Submission

**Example 1: Coordinated Alliance Attack**

Situation: I'm Austria, allied with Italy. We agreed to attack Venice.

My Units:
- A VIE (Vienna)
- A TYR (Tyrolia)
- F TRI (Trieste)
- A BUD (Budapest)

Agreed Plan with Italy:
- I'll attack Venice from Tyrolia with support from Trieste
- Italy will move out of Venice (vacate for me)

Orders:
```
A TYR - VEN (Attack Venice)
F TRI S A TYR - VEN (Support attack)
A VIE - TYR (Cover retreat position)
A BUD - SER (Opportunistic gain)
```

**Reasoning:**
- Primary goal: Gain Venice (via alliance)
- Support provided as promised
- Vienna repositions to take Tyrolia (maintain unit count)
- Budapest opportunistically moves to Serbia if undefended

**Example 2: Defensive Hold Under Threat**

Situation: I'm France, Intelligence suggests Germany may attack Belgium, where
I have F BEL.

My Units:
- A PAR (Paris)
- F BEL (Belgium)
- F MAO (Mid-Atlantic Ocean)
- A MAR (Marseilles)

Threat Assessment:
- Germany has F HOL, A RUH (both can reach Belgium)
- Unsure if attack is coming, but Belgium is valuable supply center

Orders:
```
F BEL H (Hold Belgium)
F MAO S F BEL (Support Belgium hold from Mid-Atlantic)
A PAR S F BEL (Support Belgium hold from Paris)
A MAR - BUR (Position for next turn)
```

**Reasoning:**
- Belgium is critical supply center, defend with multiple supports
- Three supports make Belgium nearly impossible to dislodge
- Marseilles moves to Burgundy (good position, not needed for defense)

**Example 3: Deceptive Order (Alliance Break)**

Situation: I'm Russia, publicly allied with Turkey. Privately planning to
attack them.

My Units:
- A UKR (Ukraine)
- A WAR (Warsaw)
- F SEV (Sevastopol)
- F BLA (Black Sea)

What I Told Turkey:
- "I'll support your hold in Rumania"
- "I'm moving Ukraine to Galicia"

Actual Orders:
```
A UKR - RUM (Attack Rumania, breaking promise)
F SEV S A UKR - RUM (Support attack)
F BLA S A UKR - RUM (Support attack)
A WAR - GAL (Actually doing what I said I wouldn't)
```

**Reasoning:**
- Promised support is actually an attack with 3-unit force
- Turkey likely didn't request support from others (trusted me)
- Rumania is valuable and this likely succeeds
- Reputation damage is acceptable because Turkey is target for elimination
- This is late game (I have 13 centers) so reputation less critical

<reasoning>
I broke the alliance because:
1. I have 13 centers (approaching solo victory)
2. Turkey is my main competitor (also 11 centers)
3. Taking Rumania puts me at 14, Turkey at 10
4. This is a knockout blow that cripples Turkey's growth
5. Reputation damage is less important when approaching end-game
</reasoning>
```

### 10.10 Adaptation Summary Table

| Component | Claude Code | Diplomacy Agent |
|-----------|-------------|-----------------|
| **Identity** | CLI tool for software engineering | Strategic player representing a power |
| **Goals** | Complete user's coding tasks | Win game (18 centers) or favorable draw |
| **Primary Actions** | Read/write files, run commands | Negotiate, plan, issue orders |
| **Decision-Making** | Tool selection, code correctness | Strategic moves, alliance management |
| **Communication** | Concise, technical | Diplomatic, persuasive |
| **State Tracking** | File system, git status | Board state, relationships, history |
| **Time Horizon** | Immediate to hours | Multiple turns, long-term planning |
| **Success Metrics** | Code works, tests pass | Supply centers gained, enemies weakened |
| **Constraints** | Safety (no malicious code) | Game rules, limited units |
| **Examples** | Code snippets, git workflows | Board positions, negotiation messages |
| **Uncertainty** | Ask user, investigate code | Assess probabilities, gather intelligence |

---

## CONCLUSION: Key Principles for Diplomacy Agent Prompts

### 1. **Hierarchical Information Architecture**
- Start with identity and core goals
- Layer in rules, then strategies, then tactics
- End with examples and edge cases

### 2. **Clear Decision Frameworks**
- Explicit decision trees for common scenarios
- Quantified thresholds where possible (e.g., "trust level 7+/10")
- Built-in exception handling ("unless survival threatened")

### 3. **Multi-Modal Examples**
- Positive examples (successful negotiations)
- Negative examples (what NOT to do)
- Edge cases (alliance breaks, defensive scenarios)
- Each with `<reasoning>` tags to teach decision logic

### 4. **State Tracking Structures**
- Board state (units, supply centers)
- Relationship state (trust, history, promises)
- Strategic state (goals, threats, opportunities)
- Communication log (what was said to whom)

### 5. **Emphasis Patterns**
- NEVER/ALWAYS for critical constraints
- IMPORTANT for overriding priorities
- Specific examples for nuanced behaviors

### 6. **Tone Calibration**
- Diplomatic language for negotiations
- Strategic language for internal reasoning
- Clear separation between internal analysis and external communication

### 7. **Progressive Disclosure**
- Essential information first (how to play)
- Strategic depth second (how to play well)
- Edge cases and exceptions last (how to handle special scenarios)

### 8. **Uncertainty Management**
- Probabilistic reasoning (>70% success → execute)
- Fallback strategies (if uncertain, ask questions)
- Conservative defaults (honor agreements unless critical gain)

### 9. **Validation and Feedback Loops**
- Post-turn analysis (who honored promises?)
- Trust calibration (update relationship assessments)
- Strategic refinement (did plan succeed?)

### 10. **Extensibility**
- Power-specific strategies (France vs. Turkey tactics)
- Variant game rules (add new order types)
- Multi-agent coordination (team Diplomacy)
- Tournament formats (different victory conditions)

---

## FINAL NOTES FOR IMPLEMENTATION

When creating a Diplomacy agent instruction file:

1. **Start with the blueprint sections in order:**
   - Section 1 (Macro Structure): Plan your overall organization
   - Section 2 (Formatting): Choose consistent patterns
   - Section 3 (Prompting): Apply emphasis techniques
   - Section 10 (Diplomacy Adaptation): Use domain-specific patterns

2. **Test incrementally:**
   - Start with basic game mechanics
   - Add strategic reasoning
   - Layer in diplomatic communication
   - Refine based on agent behavior

3. **Iterate on examples:**
   - Include examples for every major decision type
   - Add `<reasoning>` blocks to teach thinking process
   - Cover edge cases (alliance breaks, eliminations, stalemates)

4. **Maintain consistency:**
   - Use same terminology throughout (e.g., "supply center" not "SC" sometimes)
   - Keep formatting patterns consistent (H2 for major sections, H4 for sub-decisions)
   - Apply emphasis (NEVER/ALWAYS) consistently

5. **Balance completeness and conciseness:**
   - Essential game rules: Complete
   - Strategic guidance: Comprehensive but layered
   - Examples: Sufficient coverage, not exhaustive

This blueprint provides the architectural patterns. The specific content for Diplomacy agents should be developed using these patterns as a framework, adapted to the strategic complexity and multi-agent dynamics of the game.

---

**Document Prepared By:** Analysis of Claude Code v2.0.14 System Prompt
**Target Application:** Diplomacy Game AI Agents
**Document Type:** Technical Reference for Expert Prompt Engineers
**Last Updated:** 2025-11-04