<objective>
Extract and consolidate best practices for Claude Code generation from the Technical Mandates research document into an actionable reference guide for the MAMcrawler project.
</objective>

<context>
Based on "Technical Mandates for Execution-Faithful Code Generation in Claude Agent Systems" - this document provides the authoritative framework for reliable, secure code generation with Claude.
</context>

<core_principles>

## 1. STRUCTURED PROMPTING (XML Tags)

**Why:** Claude is engineered to utilize XML tags for formal, machine-readable boundaries. This improves fidelity especially with large context windows.

**Implementation:**
```xml
<objective>Clear statement of what needs to be built</objective>
<context>Project type, tech stack, constraints</context>
<requirements>Specific functional requirements</requirements>
<constraints>What to avoid and WHY</constraints>
<output>Exact file paths with relative paths</output>
<verification>How to confirm the solution works</verification>
<success_criteria>Clear, measurable criteria</success_criteria>
```

## 2. CHAIN-OF-THOUGHT (CoT) - MANDATORY FOR COMPLEX TASKS

**Why:** Externalizes reasoning BEFORE code generation, reducing logical errors and improving coherence.

**Implementation:**
- Wrap reasoning in `<scratchpad>` or `<thinking>` tags
- Force step-by-step logical plan before final code
- Makes reasoning visible and verifiable

**Example Trigger Phrases:**
- "Thoroughly analyze..."
- "Consider multiple approaches..."
- "Deeply consider..."
- "Before implementing, outline your approach..."

## 3. EPISTEMIC HONESTY

**Why:** Prevents "delusional correctness" where Claude generates high-confidence, low-factuality code.

**Implementation:**
Add to system prompt:
> "If you are unsure or don't have enough information to provide a confident answer, simply say 'I don't know' or 'I'm not sure'. Never fabricate code, dependencies, or facts."

## 4. NEGATIVE CONSTRAINT SPECIFICATION

**Why:** Acts as a security filter, reducing burden on runtime security controls.

**Implementation:**
Preemptively specify forbidden operations:
- "Do not use Python's exec() or eval() functions"
- "Do not import third-party packages unless whitelisted"
- "Never modify files outside the project directory"
- "Do not make network requests without explicit permission"

## 5. REFLECTION PATTERN (Self-Correction Loops)

**Why:** Boosts success rates from 53.8% to 81.8% through automated debugging.

**Architecture:**
1. **Generator Agent** - Creates initial code
2. **Execution/Testing** - Run against unit tests or interpreter
3. **Feedback Loop** - Route errors back to Generator
4. **Refinement** - Iterate until success or max retries

**Critical:** Test quality matters. Benchmark the agent's ability to generate reliable unit tests BEFORE trusting its self-correction.

## 6. MANDATORY SANDBOXING

**Why:** ALL LLM-generated code is inherently untrusted. Sandboxing is the foundational control.

**Requirements:**
- **Filesystem Isolation** - Restrict to current working directory only
- **Network Isolation** - Block arbitrary external network egress
- **Zero-Trust Policy** - Assume breach at output generation level
- **Minimal Privilege** - Execute in minimal-privilege container

**Network Whitelisting:**
- Avoid broad domains (github.com can enable data exfiltration)
- Use strict zero-trust network model
- Whitelist only essential, minimum-privilege external hosts

## 7. STRUCTURED OUTPUTS (Constrained Decoding)

**Why:** Guarantees valid JSON, eliminating parse errors and ensuring type safety.

**Use Cases:**
- Tool calls must match API schema exactly
- Prevents workflow failures from malformed arguments
- Removes need for retries due to schema violations

**Important:** This ensures FORMAT compliance, NOT factual correctness. Still need CoT for semantic verification.

## 8. RAG FOR CODE FIDELITY

**Why:** Grounds code generation in trusted knowledge, counters hallucination and package hallucination.

**Implementation:**
- Query validated repositories of approved dependencies
- Reference current API documentation
- Verify library existence before import
- Prevent typosquatting/dependency confusion attacks

## 9. DEPENDENCY GOVERNANCE (AI BOM)

**Why:** LLMs invent non-existent packages (Package Hallucination), exposing systems to malicious dependencies.

**Policy:**
- Automated pre-execution check
- Compare every import against verified registry
- Reject unknown dependencies
- Implement AI Bill of Materials (AI BOM) system

## 10. VERIFICATION METHODOLOGY

**Functional Correctness:**
- Use HumanEval or similar benchmarks
- Measure Pass@k metric
- Test against hidden test cases

**Unit Test Generation:**
- Benchmark agent's test generation capability (ULT/TestEval)
- Faulty tests → faulty self-correction
- Must verify test reliability before trusting agent

**Faithfulness Metrics:**
- Ensure explanations align with code execution
- Comments must match actual implementation
- No "delusional correctness"

</core_principles>

<integration_checklist>

For every code generation task:

1. ✅ Use XML-structured prompt
2. ✅ Include epistemic honesty clause
3. ✅ Specify negative constraints explicitly
4. ✅ Trigger CoT for complex tasks (use "thoroughly analyze")
5. ✅ Execute in sandbox with network isolation
6. ✅ Verify dependencies against approved registry
7. ✅ Use structured outputs for tool calls
8. ✅ Implement reflection loop for multi-step tasks
9. ✅ Generate unit tests BEFORE trusting output
10. ✅ Verify explanation-code alignment

</integration_checklist>

<anti_patterns>

**NEVER:**
- Execute LLM code outside sandbox
- Trust dependencies without verification
- Skip CoT for complex logic
- Allow broad network egress
- Trust format compliance as proof of correctness
- Use single-shot generation for complex tasks
- Ignore hallucination warnings
- Bypass unit test generation

</anti_patterns>

<success_criteria>

Code is execution-faithful when:
1. Passes all functional tests
2. Reasoning aligns with implementation
3. No hallucinated dependencies
4. Executes safely in sandbox
5. Self-correction converges to correct solution
6. Explanations match actual behavior

</success_criteria>

<references>

Key Sources:
- Anthropic Claude Agent SDK: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk
- Structured Outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Sandboxing: https://code.claude.com/docs/en/sandboxing
- Code Hallucination Research: https://arxiv.org/abs/2407.04831
- Self-Correcting Code Generation: https://deepsense.ai/resource/self-correcting-code-generation-using-multi-step-agent/

Full research document: F:\Downloads\Claude Code Generation Reliability Research.md

</references>
