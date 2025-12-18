---
description: Analyze the current conversation and create a handoff document for continuing this work in a fresh Antigravity context allowed-tools:  Read  Write  Bash  WebSearch  WebFetch
---

allowed-tools:
  - Read
  - Write
  - Bash
  - WebSearch
  - WebFetch
---

Create a comprehensive, high-fidelity handoff document that captures all context from the current conversation so work can continue in a fresh Antigravity context with zero information loss.

## Instructions

**PRIORITY: Comprehensive detail and precision over brevity.** The objective is to enable another engineer or a fresh Antigravity agent to resume work exactly where it stopped, without ambiguity or missing context.

Adapt detail to the task type (coding, research, analysis, writing, configuration, etc.) while maintaining full coverage:

1. **Original Task**
   Clearly identify the task that was initially requested. Exclude scope added later or side work unless it directly altered the original objective.

2. **Work Completed**
   Document everything accomplished in explicit detail:

* All artifacts created, modified, or analyzed (files, documents, configs, research, etc.)
* Exact changes made, including locations (file paths, sections, line ranges if applicable)
* Actions taken (commands run, searches performed, APIs or tools used)
* Findings or insights discovered
* Decisions made and the reasoning behind them
* Any side work completed that materially affects the task

3. **Work Remaining**
   Specify exactly what still needs to be done:

* Concrete, actionable steps
* Precise targets or locations (file paths, URLs, systems)
* Dependencies or required ordering
* Validation, verification, or testing steps required to complete the work

4. **Attempted Approaches**
   Capture all approaches that were tried:

* What was attempted and why
* What failed or was abandoned and the reason
* Errors, blockers, or limitations encountered
* Dead ends that should not be retried
* Alternative approaches considered but not pursued

5. **Critical Context**
   Preserve all essential knowledge required to continue:

* Key decisions and trade-offs
* Constraints, requirements, and boundaries
* Important discoveries, edge cases, or non-obvious behaviors
* Environment, configuration, or setup details
* Assumptions made that require validation
* References to documentation, sources, or external resources

6. **Current State**
   Describe the exact current state of the work:

* Status of all deliverables (complete, in progress, not started)
* What is finalized vs. draft or temporary
* Temporary workarounds or incomplete solutions
* Current position in the workflow or process
* Open questions or pending decisions

Write the handoff document to `./whats-next.md` using the XML structure below. The output file must contain ONLY the structured handoff content.

## Output Format

```xml
<original_task>
[Precisely describe the original task and its intended scope]
</original_task>

<work_completed>
[Complete, detailed record of all work performed:
- Artifacts created, modified, or analyzed (with references)
- Specific changes and locations
- Actions taken and tools used
- Findings and insights
- Decisions made and rationale]
</work_completed>

<work_remaining>
[Exact list of remaining work:
- Actionable steps with precise targets
- Dependencies or ordering constraints
- Validation or verification requirements]
</work_remaining>

<attempted_approaches>
[All approaches attempted:
- What was tried and why
- Failures or abandoned paths with reasons
- Errors, blockers, or limitations
- Dead ends to avoid
- Alternatives considered but not executed]
</attempted_approaches>

<critical_context>
[All essential context needed to continue:
- Key decisions and trade-offs
- Constraints and boundaries
- Important discoveries, edge cases, or gotchas
- Environment and configuration details
- Assumptions needing validation
- References and sources]
</critical_context>

<current_state>
[Exact current status:
- Deliverable states
- Final vs. temporary work
- Workarounds in place
- Current workflow position
- Open questions or pending decisions]
</current_state>
```