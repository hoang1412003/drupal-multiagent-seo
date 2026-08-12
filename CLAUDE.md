# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 0. Project Handoff (Required)

Before proposing or changing anything in this repository:

0. Communicate with the project owner in Vietnamese unless the user requests another language.
1. Read `README.md`, especially **"Dành cho AI/model tiếp nhận dự án"**, for the project map.
2. Read `docs/technical-debt.md` **section 8 — BÀN GIAO** for the current state, next action, cost gates, and commands. This is the source of truth for work in progress.
3. Read the relevant measurement contract in `docs/evaluation-plan.md`; for labeling work, also read `docs/goldset/annotation-guideline.md`.
4. For standalone service, admin, authentication, connector/site, or market-profile work, read `docs/superpowers/specs/2026-08-12-standalone-multiagent-platform-admin-design.md`. It is approved design, not implemented state.

Do not treat measurements in historical reports or superseded subsections as valid for the current code. A valid E1/E5 result must be traceable to the locked score-path snapshot (a later documentation-only descendant is allowed only when the score-path diff is empty), match the locked `(prompt_version, model)`, and have its own evidence file.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
