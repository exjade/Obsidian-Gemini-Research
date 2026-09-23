# Codex project instructions

## Codex with ChatGPT

For substantial implementation work in this repository, use
`$codex-with-chatgpt`.

The official `codex-with-chatgpt` SKILL.md is authoritative.

Follow all of its existing rules for:

- setup and connection
- security
- browser handling
- recovery and doctor
- conversation/project reuse
- checkpoints
- INIT / PLAN / EXECUTING / EXECUTED / REVIEW / DONE / BLOCKED
- MCP access
- execution recording

Do not replace, duplicate, weaken, or bypass those rules.

The instructions below only customize how the normal C2C coding workflow
should be used for this repository.

## Delegation-first workflow

ChatGPT is the primary planning and review layer.
Codex is the execution layer, as defined by the official C2C Skill.

For bugs, features, refactors, architecture changes and substantial
pending work:

1. Use the normal `$codex-with-chatgpt` coding workflow.
2. Send the user's actual goal to ChatGPT with INIT.
3. Let ChatGPT inspect the repository directly through MCP.
4. Wait for `STATE: PLAN` before substantial implementation.
5. Execute the received PLAN locally with Codex.
6. Run the appropriate tests/checks.
7. Record the execution according to the official C2C Skill.
8. Send EXECUTED.
9. Let ChatGPT independently REVIEW the implementation through MCP.
10. Continue with another PLAN only when the review actually requires it.

## Pending work

When the user asks to continue the project, continue pending work,
continue where we left off, or says "sigue con los pendientes":

Ask ChatGPT through C2C to:

1. read `PENDIENTES.md` through MCP;
2. inspect `git_status`;
3. identify the next coherent pending-work batch;
4. use `search_workspace` and `read_file` only for the files needed for
   that batch;
5. return one substantive C2C PLAN with rationale, concrete file-level
   actions, tests and success criteria.

Codex should not independently reconstruct the entire project before
requesting that PLAN.

## Pending-task bookkeeping

When a task is only partially completed, do not hide completed work inside
the description of an unchecked umbrella item.

Represent milestones as nested checkboxes:

- [ ] Umbrella task
  - [x] Completed delivery
  - [ ] Remaining delivery
  - [ ] Remaining delivery

An unchecked umbrella checkbox must not combine completed, pending, and
optional work in its own sentence. Put the deliverables in separate child
checkboxes as soon as a milestone is partly complete. Keep the parent label
short; record implementation detail under the relevant child. If a child is
completed but follow-up remains, mark that child `[x]` and leave the follow-up
as a separate `[ ]` child. Do not mark the parent complete until every
required child is complete; optional work must be labelled optional rather
than silently included in the completion condition.

When a C2C batch reaches DONE, mark its corresponding deliverable `[x]`.
Leave the umbrella `[ ]` until all required child deliverables are complete.

Do not create a new duplicate pending item when updating status; update the
existing hierarchy in place.

## New bugs and features

When the user reports a new bug or requests a new feature:

- treat the user's message as the task GOAL;
- do not require it to already exist in `PENDIENTES.md`;
- delegate repository investigation and high-level planning to ChatGPT;
- let ChatGPT inspect the relevant code through MCP;
- then execute the PLAN with Codex.

## Efficient execution

Preserve the official C2C protocol, but minimize unnecessary round trips.

Prefer, when technically reasonable:

1 PLAN
→ 1 coherent implementation batch
→ 1 test/check batch
→ 1 EXECUTED
→ 1 REVIEW

Do not return to ChatGPT after every individual file edit or routine
shell command.

Routine implementation decisions inside an accepted PLAN belong to Codex.

Only return early to ChatGPT if:

- a major assumption in the PLAN is wrong;
- a material blocker appears;
- the requested behavior needs to change substantially;
- or a user decision is required.

Never paste source files, diffs or long logs into ChatGPT when MCP can
provide them.
