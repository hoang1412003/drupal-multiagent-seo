# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 0. Project Handoff (Required)

Before proposing or changing anything in this repository:

0. Communicate with the project owner in Vietnamese unless the user requests another language.
1. Read `README.md`, especially **"Dành cho AI/model tiếp nhận dự án"**, for the project map.
2. Read `docs/technical-debt.md` **section 8 — BÀN GIAO** for the current state, next action, cost gates, and commands. This is the source of truth for work in progress.
3. Read the relevant measurement contract in `docs/evaluation-plan.md`; for labeling work, also read `docs/goldset/annotation-guideline.md`.
4. For standalone service, admin, authentication, connector/site, or market-profile work, read `docs/superpowers/specs/2026-08-12-standalone-multiagent-platform-admin-design.md`, `docs/superpowers/plans/2026-08-12-standalone-multiagent-platform.md`, and the six post-review decisions in `docs/technical-debt.md` section 8.9. **As of 2026-08-14, P1 through P5 are complete; the MVP acceptance matrix is 11/11 pass** (`docs/evidence/platform-mvp-acceptance.md`). Do not replace the revision-safe result callback with generic JSON:API PATCH or remove hash-v1 rollback compatibility. Run the whole offline suite with one command: `cd multiagent && .venv\Scripts\python.exe scripts\run_test_group.py all-offline` — it must report 0 failures and 0 skips. A completed platform does **not** mean scoring results exist: every run produced during P1→P5 is `is_fixture=true`.

**As of 2026-08-16, all six measurements have been run** — see `docs/technical-debt.md` section 8 for the status block and each measurement's evidence file. Headline results: E1 passed (σ `final_score` = 1.60 < 2); E3 shows the 4-agent architecture beats a single combined call (Kappa CV 0.406 vs 0.302); **E5 ran but no threshold could be locked** — `publish_min = 80` recommends `publish` for 9/33 gold articles that annotators marked as needing revision, and the gold set has zero `publish` samples to calibrate against. `meta.calibrated` stays `false` and `scoring.yaml` is unchanged. The remaining work is **not** more measurement but **two design decisions that need the mentor** (both are the same question: who is allowed to block publication), plus debt item B15.

5. The editor report UI was redesigned and merged (PR #50, 2026-08-16). It is deliberately confined to PHP/JS/CSS under `drupal/web/modules/custom/vf_ai_review/` and touches **no Python**, so the score-path diff stays empty. Read `docs/editor-ui-design.md` section 10 before changing it — section 10.6 records **four silent Drupal traps** already hit there, none of which any test caught. **This module still has no JS test harness** — the Vitest suite added on 2026-08-21 covers `multiagent/console_ui/` only, not `vf_ai_review`. Its interactions were verified by hand once and nothing guards against regressions, so re-check in a browser after editing `js/vf_ai_review.js` and do not claim otherwise. PHP tests: `cd drupal && ddev exec php scripts/test_ai_report_renderer.php`.

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
