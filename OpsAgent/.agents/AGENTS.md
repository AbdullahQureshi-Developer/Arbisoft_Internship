# OpsAgent — Superpowers Workflow Rules

This project has the Superpowers skill framework installed at `.agents/skills/`.
Use these skills **actively** throughout the build — not just installed and unused.

---

## When to Use Each Skill

### Before Starting Any Phase
- Run `/brainstorming` to explore the approach before writing code.
- Run `/writing-plans` to lay out concrete steps.
- Run `/executing-plans` to work through the approved plan.

### While Writing Any Test File
Use `/test-driven-development` — write the test first, confirm it fails, then implement.
Applies to: `test_review_skill.py`, `test_summarization_skill.py`, `test_task_extraction_skill.py`, `test_router.py`, `test_event_extraction_skill.py`, and any new test files.

### Before Marking Any Phase Complete
Run `/verification-before-completion` to confirm acceptance criteria are actually met (not just assumed). Example: "Workflow 1 works live end-to-end in Slack."

### When Something Breaks
If a tool call fails, Slack doesn't respond, or a reminder doesn't fire and the cause is not obvious — use `/systematic-debugging` instead of guessing at fixes.

### When Wiring Multiple Agents or Skills Together
For multi-step chains (e.g., the multi-agent router, parallel workflows) use `/subagent-driven-development` or `/dispatching-parallel-agents` if pieces can be parallelised independently.

### Before Merging or Wrapping Up a Phase
Run `/finishing-a-development-branch` as a final checklist before closing the branch.

### For Code Review
- Use `/requesting-code-review` to prepare a structured review request.
- Use `/receiving-code-review` when acting on feedback from the user.

---

## Skills to Skip for This Project

The following skills are **not relevant** to this backend/agent system and should be ignored:

- `copywriter`
- `i18n-localization`
- `mobile-developer`
- `mobile-uiux-promax`
- `subscription-billing`
- `ux-designer`
- `product-manager`

This project has no localization, mobile, billing, or end-user UI surface.

---

## Relevant Skills Summary

| Skill | Trigger |
|---|---|
| `/brainstorming` | Before every phase |
| `/writing-plans` | Before every phase |
| `/executing-plans` | During every phase |
| `/test-driven-development` | Every test file |
| `/verification-before-completion` | Before closing any phase |
| `/systematic-debugging` | Any non-obvious breakage |
| `/subagent-driven-development` | Multi-agent wiring |
| `/dispatching-parallel-agents` | Parallelisable work |
| `/finishing-a-development-branch` | Branch wrap-up |
| `/requesting-code-review` | Requesting review |
| `/receiving-code-review` | Acting on feedback |
| `/using-superpowers` | Learn the skill system |
| `/using-git-worktrees` | Parallel branch work |
