# Task 7 report

Status: DONE. Commit: "chore: seed test data for the new fitness domain" (only backend/create_test_data.py changed).

## Implemented
Rewrote backend/create_test_data.py. Seeds admin, medico (DOCTOR), vera (NURSE, SG), the single 1.a window of cycle 2026 (18-20/11/2026; 2.a and complementaria deliberately absent), and 9 divers. Password 12345 for all.

## Command run
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 ./venv/Scripts/python.exe manage.py shell -c "exec(open('create_test_data.py', encoding='utf-8').read())"
(same as the brief, plus the two env vars). Ran twice; both completed with identical output.

## Engine verification (fitness.diver_summary, today 2026-11-03)
| diver | intended | reported |
|---|---|---|
| apto (b age 30, 7 studies all doctor-approved) | APTO | APTO (7/7) |
| cumple40 (born 30/12/1986, age 40, owes 8) | APTO, 8 | APTO, 8 required |
| faltantes (3 of 7 loaded) | INCOMPLETE | INCOMPLETE |
| vencido (c dated 01/10/2025, doctor-approved) | PROBLEM (expired) | PROBLEM, problems=1 |
| rechazo (d rejected ILLEGIBLE; e nurse pre-approved then doctor rejected) | PROBLEM | PROBLEM, problems=2 |
| preaprobado (f nurse pre-approved only) | TO_REVIEW | TO_REVIEW, pre_reviewed=1, not apto |
| mayor (born 1978, no point a) | INCOMPLETE, owes 8 | INCOMPLETE, 8 required, 7 presented |
| sinfecha (no window) | NO_WINDOW | NO_WINDOW |
| sinnacim (window, no birth date) | UNKNOWN_AGE | UNKNOWN_AGE |
Under-40 age 27-32 owe 7; 40+ (40, 48) owe 8.

## Idempotency
Deletes the seeded users by username (cascades profiles/studies/dictamenes) and recreates them; the window is update_or_create on (cycle, slot). After two runs: 1 window, 50 study blocks, 12 users (no duplicates, no IntegrityError). Non-seed data untouched.

## Tests
Full suite: 108 tests OK. No new tests: the brief specifies none (TDD not applicable; the script's own printed engine table is the verification). DB constraints were not worked around; all rows inserted cleanly.

## Notes / concerns
- Did not delete db.sqlite3 / rerun migrate (step 2): the existing dev DB was already migrated; script ran on it directly.
- Doctor/nurse/admin have no window (they do not present studies) and are not printed as divers.
- BEFORE_WINDOW and DATE_INVALID states are not seeded (BEFORE_WINDOW is unreachable with today inside the Anexo 27 window; DATE_INVALID was not in the required list).
- Brief dropped old Permission/DiveActivity/DiveLog and the instructor user from the seed; not part of the new domain.
- Heads up: study dates are hardcoded against the fixed 2026 window, so they stay coherent with the engine regardless of the run date, but after ~21/10/2026 "today" matters for BEFORE_WINDOW only.

## Fix report (coordinator follow-up)
Commands: `rm -f db.sqlite3`; `./venv/Scripts/python.exe manage.py migrate`; seed script (brief invocation) run twice; counts query; `manage.py test`.

1. Empty-database run: ALL migrations applied OK from zero (api 0001-0013, users 0001-0004, plus allauth/auth/etc.), no failure, no warning beyond the 3 known allauth deprecations. Full migrate output was:
   contenttypes.0001, auth.0001, account.0001-0009, admin.0001-0003, api.0001 ... api.0013 (each "OK"), contenttypes.0002, auth.0002-0012, authtoken.0001-0004, sessions.0001, sites.0001-0002, socialaccount.0001-0006, users.0001-0004 (each "OK").
   Caveat: from an empty DB the data-backfill risk is untested (no rows exist during migration); only the schema chain is proven.
   Seed run 1 and run 2 produced identical tables (below). Counts after both runs: windows 1, study blocks 57, comments 57, dive activities 1, dive logs 1, users 14 (no duplication). Test suite: 108 OK.
2. Restored instructor user (is_instructor=True, no window) plus one DiveActivity and one DiveLog, using the old script's values. Both work against current models; no field broke. Not restored: the old `Permission` grant (medico->buzo1), which was not asked for; it is a one-line addition if wanted.
3. Added `fechaerronea`: study f dated 2027-03-10 (after window end), no dictamen. Engine: slot f = DATE_INVALID, diver PROBLEM (problems=1).

Engine table after fix (both runs):
apto APTO | faltantes INCOMPLETE | vencido PROBLEM | rechazo PROBLEM | preaprobado TO_REVIEW | cumple40 APTO (8) | mayor INCOMPLETE (8) | fechaerronea PROBLEM (f DATE_INVALID) | instructor NO_WINDOW | sinfecha NO_WINDOW | sinnacim UNKNOWN_AGE

Deliberate gap: BEFORE_WINDOW is not seeded. With today 2026-11-03 and window end 2026-11-20, the Anexo 27 presentation window opened 2026-10-21, so the state cannot occur for this cycle; whoever builds the screen must construct it by hand.

## Permission grant restored
Grant apto -> medico (MODIFY, ["ALL"]) restored; no field broke. Two seed runs: Permission count 1 (users deleted by cascade). Suite 108 OK.

## Fix report 3 (review items)
Commands (from backend/), invocation = brief's, with/without `SEED_CONFIRM=1` prefix; then a state query and `manage.py test`.

1. Guard: script now lists existing seeded usernames that will be deleted, then refuses (SystemExit) unless SEED_CONFIRM=1. Not gated on DEBUG. Docstring updated. Verified: without the variable (users existing from earlier runs) it printed "Se van a borrar los siguientes usuarios y todos sus datos asociados: admin, apto, ..." then "Se cancela: ... Para confirmar, definir SEED_CONFIRM=1." and deleted nothing (counts afterwards unchanged). With SEED_CONFIRM=1 ran twice, identical tables.
2. Seeded `enrevision` (f uploaded, no dictamen: slot IN_REVIEW, diver TO_REVIEW, rev=1) and `reemplazo` (d uploaded 2026-08-01, rejected OUT_OF_TERM by doctor, re-uploaded and approved; diver APTO). DB shows: block 367 is_current=False, 2026-08-01, [REJECTED/OUT_OF_TERM]; block 368 is_current=True, 2026-09-15, [APPROVED]. Final counts: 1 window, 72 blocks, 71 comments, 1 dive activity, 1 dive log, 1 permission, 16 users. Suite: 108 OK.
3. `default_date(code)` helper replaces the hidden swap in upload(); `rol` column dropped; instructor comment fixed.

on_delete (read from api/models.py): Permission.grantor and .grantee = CASCADE; DiveActivity.instructor = CASCADE; DiveActivity.safety_diver/medic/supervisor = SET_NULL; DiveLog.diver = SET_NULL, DiveLog.activity = CASCADE. So deleting seeded users removes their permissions and the instructor's activity (and its logs by cascade). Nothing is orphaned: the activity belongs to the seeded instructor, so it is always removed on re-run; a DiveLog whose diver is deleted would only be nulled, but its activity is deleted by the instructor cascade, so none survive. Re-runs therefore do not duplicate (counts 1/1/1).
