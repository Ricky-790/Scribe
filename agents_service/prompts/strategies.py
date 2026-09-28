from .decomposer_prompts import DECOMPOSER_AGENT_INSTRUCTIONS
TECHNOLOGY_STRATEGY = """
[technology]

Use for: Software, AI, Blockchain, Developer tools, Infrastructure, Consumer technology,
Hardware, Emerging technologies.

Research dimensions:

- Problem Definition
  - What problem does the technology solve?
  - Why does this problem matter?
  - Who experiences it?

- Technical Foundations
  - Core architecture
  - Working principles
  - Important algorithms or protocols
  - Design philosophy
  - Major components

- Evolution
  - Origins
  - Major milestones
  - Important releases
  - Evolution of the ecosystem

- Current Ecosystem
  - Major companies
  - Open-source projects
  - Developers
  - Communities
  - Adoption metrics

- Competitive Landscape
  - Alternatives
  - Advantages
  - Limitations
  - Trade-offs

- Real-world Applications
  - Industries using it
  - Production deployments
  - Notable case studies

- Challenges
  - Technical bottlenecks
  - Security
  - Scalability
  - Regulatory issues
  - Criticisms

- Future Outlook
  - Active research
  - Emerging trends
  - Likely future developments
"""

FINANCE_STRATEGY = """
[finance]

Use for: Stocks, Commodities, ETFs, Crypto assets, Macroeconomics, Financial markets.

Research dimensions:

- Asset Overview
  - What is the asset?
  - Why does it exist?
  - Market role

- Historical Performance
  - Long-term price movement
  - Major rallies
  - Major crashes
  - Key turning points

- Drivers Behind Market Movement
  - Catalysts for significant price changes
  - Economic events
  - Monetary policy
  - Regulation
  - Supply and demand dynamics
  - Institutional activity

- Current Market State
  - Current trends
  - Liquidity
  - Market sentiment
  - Valuation

- Fundamental Factors
  - Revenue/business fundamentals (if applicable)
  - Tokenomics
  - Cash flows
  - Economic indicators
  - On-chain metrics where relevant

- Risks
  - Market risks
  - Regulatory risks
  - Competitive risks
  - Liquidity risks

- Future Outlook
  - Analyst expectations
  - Market narratives
  - Growth opportunities
  - Bearish viewpoints
"""

SCIENTIFIC_STRATEGY = """
[scientific_or_academic]

Use for: Science, Medicine, Engineering, Mathematics, Psychology, Academic research.

Research dimensions:

- Background
  - What is being studied?
  - Historical context
  - Why the problem is important

- Scientific Foundations
  - Fundamental principles
  - Laws
  - Models
  - Mechanisms
  - Theoretical framework

- Current Understanding
  - Consensus
  - Competing hypotheses
  - State of the art

- Evidence
  - Landmark studies
  - Recent publications
  - Experimental findings
  - Meta analyses

- Practical Applications
  - Industry
  - Medicine
  - Engineering
  - Society

- Limitations
  - Known uncertainties
  - Methodological limitations
  - Areas with conflicting evidence

- Open Problems
  - Active research questions
  - Future directions
  - Emerging discoveries
"""

PERSON_STRATEGY = """
[person]

Use for: Individuals, Public figures, Researchers, Entrepreneurs, Executives, and
Organizations/Companies (treat an organization's leadership, culture, and identity the way
you would a person's biography).

Research dimensions:

- Background
  - Early life / founding story
  - Education
  - Career progression / company origins

- Major Contributions
  - Important work
  - Discoveries
  - Products
  - Publications
  - Leadership

- Influence
  - Industry impact
  - Academic impact
  - Cultural influence
  - Network and affiliations

- Recent Activity
  - Current projects
  - Public statements
  - Recent publications
  - New ventures

- Reputation
  - Recognition
  - Awards
  - Criticism
  - Controversies
  - Public perception

- Legacy
  - Long-term significance
  - Influence on future work
"""

HISTORIC_EVENT_STRATEGY = """
[historic_event]

Use for: Historical events, Wars, Discoveries, Political events, Economic crises, Scientific
breakthroughs.

Research dimensions:

- Historical Context
  - Conditions leading to the event
  - Background
  - Relevant timeline

- The Event
  - What happened
  - Sequence of events
  - Key participants

- Causes
  - Immediate causes
  - Underlying causes
  - Political
  - Economic
  - Scientific
  - Social factors

- Consequences
  - Short-term effects
  - Long-term effects
  - Global impact

- Different Perspectives
  - Scholarly interpretations
  - Competing viewpoints
  - Historical debates

- Modern Relevance
  - Influence today
  - Lessons learned
  - Connections to current events
"""

GENERAL_STRATEGY = """
[general]

Use when no single strategy clearly dominates.

Break the topic into its natural dimensions and investigate each one.
Prefer meaningful research questions over a fixed report structure.
"""

STRATEGY_BLOCKS: dict[str, str] = {
    "technology": TECHNOLOGY_STRATEGY,
    "finance": FINANCE_STRATEGY,
    "scientific_or_academic": SCIENTIFIC_STRATEGY,
    "person": PERSON_STRATEGY,
    "historic_event": HISTORIC_EVENT_STRATEGY,
    "general": GENERAL_STRATEGY,
}

COMBINING_STRATEGIES_GUIDANCE = """
────────────────────────────────────────────────────────
Combining Strategies
────────────────────────────────────────────────────────

This topic has been assigned more than one category. Treat the dimensions above as a combined
pool, not separate reports to stitch together.

- Merge overlapping sections.
- Remove redundant work.
- Preserve logical flow.
- Emphasize the dimensions most relevant to the user's question.
- The report should feel like a coherent narrative rather than separate reports glued together.

Examples of how prior combined topics were handled:
- AI in Healthcare        -> Technology + Scientific
- AI-powered Trading      -> Technology + Finance
- NVIDIA                  -> Person + Technology + Finance
- Bitcoin                 -> Technology + Finance + Historical
- The Discovery of CRISPR -> Scientific + Historical
- OpenAI                  -> Technology + Person
"""


def build_strategy_context(categories: list[str]) -> str:
    """
    Build the strategy context to inject into the decomposer prompt, using only the
    strategy blocks relevant to the given categories. Includes combining guidance
    automatically when more than one category is present.
    """
    blocks = [STRATEGY_BLOCKS.get(c, GENERAL_STRATEGY) for c in categories]
    context = "\n".join(blocks)
    if len(categories) > 1:
        context += "\n" + COMBINING_STRATEGIES_GUIDANCE
    return context


def build_decomposer_instructions(categories: list[str]) -> str:
    strategy_context = build_strategy_context(categories)
    return DECOMPOSER_AGENT_INSTRUCTIONS.format(strategy_context=strategy_context)
