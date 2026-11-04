# Task 1 report: Catálogo de los ocho estudios

## Implemented
- `backend/api/catalog.py`: frozen dataclass `RequiredStudy`, `ALL` (a..h), `CODES`, `get(code)` (KeyError on unknown), `required_for_age(age)` (`min_age is None or age >= min_age`). No Django imports.
- Texts, validity (365 days, h = 30) and age rule (only a, min 40) copied verbatim from the brief's Global Constraints.
- `upload_hint` set only for d and f, with the exact strings from the brief.
- `backend/api/tests/__init__.py` and `backend/api/tests/test_catalog.py` (8 SimpleTestCase tests).
- `backend/api/tests.py` removed with `git rm`.

## Tests
- Focused: `cd backend && ./venv/Scripts/python.exe manage.py test api.tests.test_catalog -v 2` -> 8 tests, OK.
- Full: `./venv/Scripts/python.exe manage.py test` -> 8 tests, OK.

## TDD Evidence
RED: after creating the test package and before `catalog.py` existed, the run reported:
`ImportError: cannot import name 'catalog' from 'api'` (test module failed to import, 1 error, FAILED). Expected: the module does not exist yet.
GREEN: after implementing `catalog.py`, all 8 tests printed `... ok` and the run ended `OK`.

## Files changed
- Created: `backend/api/catalog.py`, `backend/api/tests/__init__.py`, `backend/api/tests/test_catalog.py`
- Deleted: `backend/api/tests.py`

## Commit
- `6c88518` feat(api): add catalog of the eight required studies from Directiva 443/21

## Self-review
- Strings compared against the brief during writing; no re-wording.
- `_BY_CODE` dict used for O(1) lookup in `get`; `CODES` derived from `ALL` so they cannot drift.
- Git emitted CRLF warnings on the new files (autocrlf setting on this machine); content is LF as written. No action taken.

## Concerns
None blocking.
