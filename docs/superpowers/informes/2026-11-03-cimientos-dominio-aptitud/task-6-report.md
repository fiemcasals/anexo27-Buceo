# Task 6 report — El motor de aptitud derivada

**Status:** DONE
**Commit:** `b430a52` feat(api): add the fitness engine that derives study states and aptitude

## What I implemented

`backend/api/fitness.py`, the derived-state engine. Nothing is stored: every state is
recomputed on each read from the dictámenes and the dates.

Public surface, exactly as the brief's *Produces* list:

- `StudyState` — `NOT_REQUIRED`, `MISSING`, `BEFORE_WINDOW`, `IN_REVIEW`, `PRE_REVIEWED`,
  `APPROVED`, `REJECTED`, `EXPIRED`, `DATE_INVALID`
- `DiverState` — `NO_WINDOW`, `UNKNOWN_AGE`, `PROBLEM`, `INCOMPLETE`, `TO_REVIEW`, `APTO`
- `SlotStatus` — frozen dataclass: `code`, `state`, `block`, `last_dictamen`, `expires_on`
- `DiverSummary` — frozen dataclass: `required_codes`, `slots`, `presented`, `approved`,
  `pending_review`, `pre_reviewed`, `problems`, `last_doctor_review`, `state`, `is_apto`
- `required_codes(profile) -> tuple[str, ...]` — `()` when there is no window or no birth date
- `diver_summary(profile, today) -> DiverSummary`

Three small helpers are public because they are the rules themselves and later plans
(and the Anexo 27 screens) will want them:

- `habilitation_year(window) -> int` — `window.end_date.year`
- `validity_ends_on(code, study_date) -> date` — last day the study still covers
  (renamed from `expires_on` during the review fixes, so it no longer shares the name of the
  `SlotStatus.expires_on` field it fills)
- `earliest_valid_date(code, window) -> date` — `end_date − validity_days`

### The four rules, and how they are expressed

1. **Validity is measured against the chosen window, never against today.** `today` enters the
   computation in exactly one place: deciding `BEFORE_WINDOW` vs `MISSING` for a point with
   nothing uploaded. Every validity comparison uses `window.end_date`.
2. **The binding day is `end_date`.** A point is valid iff
   `validity_ends_on(code, study_date) >= window.end_date` **and** `study_date <= window.end_date`.
3. **Age = window year − birth year**, delegated to `UserProfile.age_in_year(habilitation_year(window))`.
   The window's own year is used, not `cycle` — that is what makes the July 2027 complementary
   date age the diver by a year even though its `cycle` is 2026.
4. **The Anexo 27 is one rule, not a special case.** Its 30-day catalog validity makes
   `earliest_valid_date("h", window) == end_date − 30`, which is exactly
   `HabilitationWindow.anexo27_earliest_date`. A test asserts the two agree so they cannot drift.

### Precedence decisions I had to make (not spelled out in the brief)

- **Dates outrank the dictamen.** For an uploaded block the order is `DATE_INVALID` →
  `EXPIRED` → latest dictamen. An approved study that does not cover the window is `EXPIRED`,
  which the brief's own test demands; I applied the same gate to a rejected-and-expired study
  for consistency. The rejection is not lost: `SlotStatus.last_dictamen` still carries it, so a
  screen can show the reason.
- **`BEFORE_WINDOW` makes the diver `INCOMPLETE`.** Without this the ladder would fall through
  to `APTO` for a diver whose only outstanding point is an Anexo 27 that cannot be presented yet.
  `INCOMPLETE_STATES = {MISSING, BEFORE_WINDOW}`.
- **`NOT_REQUIRED` with no window / no birth date.** `slots` always covers all eight catalog
  codes in catalog order. When nothing can be required, every slot is `NOT_REQUIRED` but still
  carries its `block`, `last_dictamen` and `expires_on`, so uploads stay visible; the headline is
  the `DiverState` (`NO_WINDOW` / `UNKNOWN_AGE`).
- **Counters cover only the required points**, so a 38-year-old who uploads point `a` by mistake
  does not inflate `approved`/`presented`. **`last_doctor_review` covers all eight**, so a point
  that the age rule later dropped does not erase the record that the doctor reviewed this diver.
- **`APPROVED` needs no role check.** The `verdict_matches_reviewer_role` DB constraint makes
  `status == 'APPROVED'` equivalent to doctor-approved; the verdict alone names the state
  (`_STATE_BY_VERDICT`). `PRE_APPROVED` maps to `PRE_REVIEWED` and never to approved.
- **The latest dictamen decides**, sorted in memory by `(created_at, pk)` — not "does a dictamen
  of kind X exist". Both directions are tested: pre-approval then rejection → `REJECTED`, and
  rejection then approval → `APPROVED`.
- **`is_apto` is derived from `state`** (`state is DiverState.APTO`), so the two can never
  disagree. `APTO` is reached only after `PROBLEM`, `INCOMPLETE` and `TO_REVIEW` are all ruled
  out, which leaves `APPROVED` as the only possible state for every required point; and with a
  window and an age the required set is never empty (seven points are age-independent), so the
  aptitude can never come from a vacuous `all()`.

## What I tested and the results

`backend/api/tests/test_fitness.py` — 49 tests (46 at first review, plus the 3 added to close
the review), all of the brief's verbatim cases plus the
boundaries and the performance shape.

- `RequiredSetTests` (6): 38 → seven, 39 → seven, exactly 40 (born 31/12/1986) → eight,
  the complementary July 2027 date ages the diver, no window → `()`, no birth date → `()`.
- `SlotStateTests` (26): every state; the expiry/`DATE_INVALID`/Anexo-27 boundaries; a
  single-day window; latest-dictamen in both directions; only the current block counts (twice,
  see below); `expires_on`; engine vs. `anexo27_earliest_date`.
- `DiverSummaryTests` (16): the brief's eight, plus the counters split by state, slots covering
  the eight codes in order, a non-required upload not counting, `INCOMPLETE` outranking
  `TO_REVIEW`, an expired point being a `PROBLEM`, the still-closed Anexo 27 leaving the diver
  `INCOMPLETE` rather than apto, and a summary with no window requiring and counting nothing.
- `RosterPerformanceTests` (1): three fully-reviewed divers fetched with the documented
  prefetch, then `assertNumQueries(0)` around the summaries.

Full suite: **108 tests OK** (59 pre-existing + 49 new; it was 105 with 46 at first review). Only the three known `allauth`
deprecation warnings. `makemigrations --check --dry-run` → **No changes detected**: no migration
needed, none written.

## TDD Evidence

### RED — before `api/fitness.py` existed

```
$ cd backend && ./venv/Scripts/python.exe manage.py test api.tests.test_fitness -v 2
ERROR: test_fitness (unittest.loader._FailedTest.test_fitness)
ImportError: Failed to import test module: test_fitness
  File "...\backend\api\tests\test_fitness.py", line 15, in <module>
    from api import catalog, fitness
ImportError: cannot import name 'fitness' from 'api'
Ran 1 test in 0.000s
FAILED (errors=1)
```

Expected: the brief predicts `ModuleNotFoundError: No module named 'api.fitness'`. Same cause —
the module does not exist; it surfaces as `ImportError: cannot import name 'fitness' from 'api'`
only because the test imports it as `from api import catalog, fitness` rather than
`import api.fitness`. Nothing could be collected, so no test could pass for any reason.

### GREEN — after implementing `api/fitness.py`

```
$ cd backend && ./venv/Scripts/python.exe manage.py test api.tests.test_fitness -v 2
... (46 tests listed, all "ok")
Ran 46 tests in 0.252s
OK
```

```
$ cd backend && ./venv/Scripts/python.exe manage.py test
System check identified 3 issues (0 silenced).   # the three known allauth warnings
.........................................................................................................
Ran 105 tests in 0.814s
OK
```

## Files changed

- `backend/api/fitness.py` — new, 296 lines
- `backend/api/tests/test_fitness.py` — new, 499 lines

No model, migration, serializer, view, `create_test_data.py` or frontend file was touched.

## Boundary decisions

| Boundary | Decision | Test that pins it |
| --- | --- | --- |
| A study expiring exactly on `end_date` | **Valid** (inclusive): `expires_on >= end_date` | `test_a_study_valid_exactly_through_the_last_day_is_not_expired` (study 20/11/2025 → `APPROVED`), against `test_approved_but_expiring_inside_the_window_is_expired` (19/11/2025 → `EXPIRED`) |
| A study dated exactly on `end_date` | **Valid** (inclusive): `study_date > end_date` is the failure | `test_a_study_dated_on_the_last_day_of_the_window_is_valid` / `test_a_study_dated_one_day_after_the_window_is_already_not_trusted` |
| Anexo 27 dated exactly on `end_date − 30` | **Valid** (inclusive) — it is the same `expires_on >= end_date` rule | `test_an_anexo_27_dated_when_its_window_opens_is_valid` / `..._one_day_before_its_window_is_too_old` |
| The day the Anexo 27 window opens (`today == end_date − 30`) | **Open** → `MISSING`, not `BEFORE_WINDOW`: the condition is `today < earliest_valid_date` | `test_the_anexo_27_window_opens_on_the_thirtieth_day_before_the_end` (21/10 → `MISSING`, 20/10 → `BEFORE_WINDOW`) |
| Age exactly 40 in the window's year | **Owes all eight**: `age >= min_age` on a plain year subtraction | `test_turning_forty_during_the_habilitation_year_owes_eight` (born 31/12/1986), with 39 → seven as the tight lower side |
| A single-day window (`start_date == end_date`) | Legitimate; judged against that one day, inclusively | `test_a_single_day_window_is_judged_against_that_one_day` (both sides of the boundary) |
| Which year is "the habilitation year" | `end_date.year` — consistent with the binding day, and the conservative choice for a window straddling New Year | `test_the_complementary_date_uses_its_own_year` |

## How a caller should prefetch a whole roster

`diver_summary` never queries on its own; it reads `profile.habilitation_window`,
`profile.birth_date`, `profile.user.study_blocks.all()` and `block.comments.all()`. The roster
screen fetches all of that in four queries total, regardless of how many divers:

```python
UserProfile.objects.select_related("user", "habilitation_window").prefetch_related(
    Prefetch(
        "user__study_blocks",
        queryset=StudyBlock.objects.filter(is_current=True).prefetch_related("comments"),
    )
)
```

Then `[fitness.diver_summary(p, today) for p in profiles]` issues **zero** further queries —
asserted by `RosterPerformanceTests` with `assertNumQueries(0)`.

Two deliberate choices make this robust rather than fragile:

- The engine filters `is_current` **in Python**, not with `.filter()`. Calling `.filter()` on a
  prefetched manager re-queries; iterating `.all()` uses the cache. So the `Prefetch` may filter
  `is_current=True` (fewer rows) or not — the answer is the same either way.
- The engine sorts the dictámenes **in Python** by `(created_at, pk)`. The caller does not have
  to order the `comments` prefetch, and a caller who orders it differently cannot change the
  result.

What a caller must not do is omit the prefetch: without it each diver costs one query for the
blocks plus one per uploaded point for the dictámenes — the 150 × 8 shape §13 warns about.
`required_codes(profile)` alone needs only `select_related("habilitation_window")`.

## Self-review findings

I ran a mutation check over the implementation — 27 single-rule mutations, each reverting one
rule, run against the test file — to answer the "could this test fail?" question with evidence
rather than by inspection.

**One real defect found, in a test from the brief.** `test_only_the_current_block_of_a_slot_is_considered`
**survived** deleting the `is_current` filter from `_current_blocks`. The reason: the dict
comprehension keyed by `study_code` lets the last row iterated win, and the replacement block has
the higher pk, so the right answer came out by accident of row order. The test proved nothing
about `is_current`. I kept the brief's test verbatim and added
`test_a_demoted_block_is_ignored_even_if_it_was_saved_last`, which puts the demoted block last in
pk order and so fails if the filter is removed. This is the same test shape the task brief warned
about from an earlier task.

Every other mutation was caught, including: validity measured against `start_date` (2 failures),
against `today` (5), each of the four boundary flips, first-dictamen-wins instead of last (4),
`PRE_APPROVED` treated as approved (3), the `BEFORE_WINDOW` rule deleted (3), `BEFORE_WINDOW`
dropped from `INCOMPLETE_STATES` (1), nurse dictámenes counted in `last_doctor_review` (2), the
age rule ignored (8), each reordering of the `DiverState` ladder (1–2 each), `NOT_REQUIRED`
ignored, counters taken over all eight slots instead of the required ones, and `expires_on` off
by one (6).

Other review notes:

- No test asserts merely "a `ValidationError` was raised"; every assertion names the specific
  state, count or date.
- The dataclasses are frozen, so a caller cannot write a state back into them.
- `_STATE_BY_VERDICT` is a dict lookup rather than an if/else chain, so there is no dead
  `else: return REJECTED` branch and an unknown verdict raises `KeyError` instead of being
  silently labelled a rejection.
- `fitness.py` imports only `catalog`, the stdlib and `django.utils.timezone`; no model imports
  at runtime (the annotations are under `TYPE_CHECKING`), so there is no import cycle with
  `api.models` or `users.models`.

## Issues and concerns

- **`created_at` and the timezone.** `last_doctor_review` converts with
  `timezone.localtime(dictamen.created_at).date()`. With `TIME_ZONE = 'UTC'` that is the naive
  `.date()`, but using `localtime` means the day shown stays the local day if the project's
  timezone is ever changed to Argentina. The test helper writes the dictamen's `created_at` at
  12:00, well away from either edge.
- **The rejected-and-expired precedence is my call, not the brief's.** A point that is both
  rejected and out of date reports `EXPIRED`. If the screens would rather lead with the
  rejection reason, invert the two checks in `_study_state`; `last_dictamen` carries the
  rejection either way, so no information is lost today.
- **`last_doctor_review` scope is also my call**: the latest doctor dictamen over all eight
  current blocks, while the counters cover only the required set. It is documented in the
  function's docstring. No test distinguishes it from the required-only variant, because I did
  not want to pin a choice the roster screen may want to revisit in plan 3.
- **Nothing consumes the engine yet.** Task 7 (test data) and the later plans will be the first
  real callers; the documented prefetch is the contract they should follow.

---

# Fix report — closing the review

**Commit:** `7430bfa` test(api): pin the fitness engine's two unpinned rulings and name the
validity helper (on top of `b430a52`)

**Covering test file:** `backend/api/tests/test_fitness.py` (the only test file for this task).

**Command:** `cd backend && ./venv/Scripts/python.exe manage.py test api.tests.test_fitness`
**Output:** `Ran 49 tests in 0.261s` / `OK`

**Full suite:** `cd backend && ./venv/Scripts/python.exe manage.py test` →
`Ran 108 tests in 0.824s` / `OK` (59 pre-existing + 49), with only the three known `allauth`
deprecation warnings. `makemigrations --check --dry-run` → `No changes detected`: still no
migration.

Per-class split, now measured rather than counted by hand
(`manage.py test api.tests.test_fitness -v 2 | sed -n 's/.*test_fitness\.\([A-Za-z]*\)\..*/\1/p' | sort | uniq -c`):
`RequiredSetTests` 6, `SlotStateTests` 26, `DiverSummaryTests` 16, `RosterPerformanceTests` 1 = 49.

## Item 1 — `last_doctor_review`'s scope is now pinned

Added `DiverSummaryTests.test_last_doctor_review_counts_a_point_the_age_rule_left_out`, in the
second form the coordinator asked for: a 38-year-old whose point `a` (outside the required set)
carries the **only** doctor dictamen, dated 14/10/2026, while the one required point that was
reviewed carries a nurse pre-approval dated 28/10. It asserts
`_slot_of(s, "a").state == NOT_REQUIRED` and `s.last_doctor_review == date(2026, 10, 14)`.

Under a required-only variant there is no doctor dictamen left among the required slots, so the
value is `None` — the test fails on the date assertion regardless of how the rest shakes out.

**Mutation check I ran** (restricting `_last_doctor_review` to slots whose state is not
`NOT_REQUIRED`): **CAUGHT** — `FAILED (failures=1)`, the single failure being
`test_last_doctor_review_counts_a_point_the_age_rule_left_out`. Implementation restored and
re-verified green.

## Item 2 — the rejected-and-expired ruling is now pinned

Added `SlotStateTests.test_a_study_both_rejected_and_expired_reports_expired`: point `b` dated
19/11/2025 (so it expires 19/11/2026 and does not cover the window's 20/11) carrying a doctor's
rejection. It asserts `slot.state == EXPIRED` **and** that the reason survives —
`last_dictamen.status == "REJECTED"`, `rejection_reason == "OTHER"`,
`content == "Falta la firma."`. The second half is the point: a later plan's screen has to show
the rejection beside the expired state, and that is now a test, not a claim in a report.

**Mutation check I ran** (a `REJECTED` short-circuit inserted ahead of both date gates in
`_study_state`): **CAUGHT** — `FAILED (failures=1)`, the single failure being
`test_a_study_both_rejected_and_expired_reports_expired`. Restored and re-verified green.

## Item 3 — `is_current` coverage is now order-independent

Added `SlotStateTests.test_a_slot_whose_only_block_is_demoted_counts_as_missing`, **beside** the
existing two rather than instead of them: the slot has exactly one block, which is demoted, and
the assertions are `state == MISSING` and `block is None`. With one row there is no row order to
be lucky about, so the test keeps discriminating if `StudyBlock` ever gains a `Meta.ordering`.

**Mutation check I ran** (the `is_current` filter deleted from `_current_blocks`): **CAUGHT** —
`FAILED (failures=2)`, both `test_a_demoted_block_is_ignored_even_if_it_was_saved_last` and the
new `test_a_slot_whose_only_block_is_demoted_counts_as_missing`. Restored and re-verified green.

## Item 4 — the module function renamed

`fitness.expires_on(code, study_date)` → `fitness.validity_ends_on(code, study_date)`. The
`SlotStatus.expires_on` **field** keeps its name, since that is what later serializers and
templates read. Three call sites updated (`_slot_status`, `_study_state`, and the field
assignment, which now reads
`expires_on=(None if block is None else validity_ends_on(code, block.study_date))`). No test
referenced the function by name, so nothing in the tests changed for this; the suite confirms
the rename is complete.

## Item 5 — the report's counts corrected

My per-class split (6/25/14/1) was wrong; the reviewer's count (6/24/15/1) was right. The
"What I tested" section above now carries the post-fix numbers (6/26/16/1 = 49), and the suite
totals read 108 / 49 instead of 105 / 46. I took them from the measured output this time rather
than counting by eye.

## Remaining concerns

None new. Of the three concerns in my original report, two are now pinned by tests (the
rejected-and-expired precedence, item 2; and `last_doctor_review`'s scope, item 1 — so it is now
a decision a future change has to confront deliberately rather than one it could break in
silence). The `timezone.localtime` note on `created_at` stands as written: correct today under
`TIME_ZONE = 'UTC'` and correct too if the project's timezone is later changed to Argentina.
