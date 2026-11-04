# Task 2 report
Implemented: UserProfile birth_date (replaces age), unique dni, closed grouped RANK_CHOICES + RANK_VALUES (derived), NURSE role, age_in_year; admin registration (list_display rank/apellido/nombre/DNI/correo/rol, search on DNI/apellido/nombre); serializer now exposes birth_date instead of age (controller correction 2); migration 0003_profile_birth_date_dni_rank_roles; dev db recreated (not seeded; create_test_data.py untouched).
RED: `manage.py test users` -> 3 failures + 5 errors (age_in_year, RANK_VALUES, NURSE, admin registration missing; birth_date kwarg) as expected.
GREEN: full suite `manage.py test` -> Ran 16 tests, OK (7 brief tests + serializer test + Task 1 catalog tests).
Files: backend/users/{models,admin,tests}.py, backend/api/serializers.py, backend/users/migrations/0003_...py
Concerns: `UserProfile.objects.get_or_create(user=...)` in api/views.py (lines 25, 287) and the mock scripts create profiles with dni='' ; with unique=True a second such profile will violate the constraint. Needs handling in later tasks (registration/seed). Rank labels (Spanish names) were my choice; CY label "Coronel Mayor" worth verifying.

## Fix report
- dni is now CharField(max_length=20, unique=True, null=True, blank=True); get_or_create path yields dni=None (verified by new test, no change to api/views.py).
- Rank labels equal their codes; groups/order/RANK_VALUES unchanged.
- Migration 0003 regenerated in place (same name); dev db recreated.
- Tests (backend/users/tests.py): added test_profiles_without_dni_coexist; kept test_dni_is_unique (same non-empty DNI -> IntegrityError).
- Command: `cd backend && ./venv/Scripts/python.exe manage.py test` -> 17 tests, OK.

## Fix report 2
- UserProfile.save() coerces falsy dni to None (all write paths). Serializer untouched.
- Tests in backend/users/tests.py: test_blank_dni_is_stored_as_null_so_profiles_coexist (.save()), test_two_users_can_patch_blank_dni_through_the_api (APIClient.force_authenticate, no extra scaffolding), test_dni_is_unique kept.
- Command: `cd backend && ./venv/Scripts/python.exe manage.py test` -> 19 tests, OK.
