# Task 3 report
Implemented HabilitationWindow (api/models.py, UniqueConstraint cycle+slot, clean() end<start, ordering start_date, anexo27_earliest_date = end_date-30d, Spanish impersonal __str__), UserProfile.habilitation_window (nullable FK, SET_NULL, related_name divers; save() override untouched), admin registration, migrations api 0006 and users 0004.
Tests: 8 in test_habilitation_window (7 from brief + FK behaviour test). end-before-start test asserts the error is only under __all__ so it cannot pass due to another field. Full suite: 27 pass (19 + 8).
RED: `manage.py test api.tests.test_habilitation_window` -> ImportError: cannot import name 'HabilitationWindow'. GREEN: full suite Ran 27 tests OK.
No validation requiring all three slots. Frontend, seed script untouched.

## Fix report
Added CheckConstraint window_end_not_before_start (end_date >= start_date) with Spanish violation_error_message; Spanish message on the unique constraint ('Ya existe una fecha con ese lugar en el ciclo.'); clean() kept. New migration api/0007 (0006 untouched).
New tests in backend/api/tests/test_habilitation_window.py: test_database_rejects_an_inverted_range (objects.create -> IntegrityError), test_duplicate_slot_has_a_spanish_message.
Command: cd backend && ./venv/Scripts/python.exe manage.py test -> "Ran 29 tests ... OK".
