# Task 4 report

Implemented: StudyBlock.study_code (choices from catalog.CODES), is_current, save() (title from catalog; on creation of a current block, demotes only same user + same study_code; no demotion on re-save). Serializer gets study_code and is_current. Migration api/0008 (one-off default "g" for existing rows, not preserved).
Tests: 8 in api/tests/test_study_block.py (incl. not-deleted, re-save, other point/diver, study_code error asserted via message_dict). Full suite 37 pass (29 + 8).
RED: `manage.py test api.tests.test_study_block` -> TypeError: StudyBlock() got unexpected keyword arguments: 'study_code' (errors=15). GREEN: 8 OK; full suite 37 OK.
Files: backend/api/models.py, serializers.py, migrations/0008_..., tests/test_study_block.py.
Notes: title is still required in the serializer (POST breaks anyway, accepted per brief). Frontend, create_test_data.py untouched.

## Fix report
1. Rewrote the re-save test (now test_resaving_an_old_instance_does_not_demote_the_current_one): create first, second (demotes first in DB; in-memory first stays True), then first.save(update_fields=["description"]) and assert second still current. Note: a plain first.save() would write is_current=True back and, with fix 3, hit the unique constraint, so update_fields is used. Discrimination check: removed the `self._state.adding` gate -> test FAILED with "AssertionError: False is not true" (second demoted); gate restored.
2. Demotion + super().save() wrapped in transaction.atomic().
3. Added partial UniqueConstraint one_current_study_per_diver_and_point (user, study_code; condition is_current=True), migration api/0009 (0008 untouched). New test test_database_rejects_a_second_current_row_for_the_same_point flips a historical row back via QuerySet.update() and expects IntegrityError.
Covering file: backend/api/tests/test_study_block.py. Command: `./venv/Scripts/python.exe manage.py test api.tests.test_study_block` (9 tests OK); full suite `manage.py test`: Ran 38 tests, OK.
