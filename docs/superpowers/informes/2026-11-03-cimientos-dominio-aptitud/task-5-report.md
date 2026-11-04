# Task 5 report
Implemented on Comment: PRE_APPROVED status, REJECTION_REASONS (OUT_OF_TERM, UNFIT_VALUES, ILLEGIBLE, OTHER), REVIEWER_ROLES, reviewer_role (default DOCTOR so existing code creating Comments keeps working), rejection_reason (blank=True), content blank=True (controller correction), clean() (rejection needs reason and non-blank content; non-rejections forbid reason). Migration api/0010.
TDD: RED = test_dictamen run before implementation: 1 failure + 9 errors (no REJECTION_REASONS, PRE_APPROVED missing). GREEN = full suite 48 tests OK (38 + 10 new).
Tests assert specific fields via message_dict keys (list(errors) == [field]). Each rule test fails if the rule is removed: reason/content/forbidden-reason checks each assert the exact error key; reviewer_role test fails without choices.
Concern: reviewer_role has default DOCTOR (brief gave no default) for backward compatibility with existing views.
Files: backend/api/models.py, backend/api/tests/test_dictamen.py, backend/api/migrations/0010_*.py

## Fix: reviewer_role has no default
Removed default='DOCTOR'; field now required. New migration api/0011_alter_comment_reviewer_role.py (0010 untouched). Added reviewer_role and rejection_reason to CommentSerializer fields. Added test_a_dictamen_without_reviewer_role_is_refused (message_dict keys == ['reviewer_role']) in backend/api/tests/test_dictamen.py.
Command: `manage.py test api.tests.test_dictamen` -> 11 tests OK. Could-fail check: with default reintroduced the new test FAILED (1 failure); reverted, makemigrations --check clean. Full suite: 49 tests OK.

## Fix: authority and rejection constraints, status without default
1. status: default removed (migration 0012). Test test_a_dictamen_without_status_is_refused (keys == ['status']); fails if default restored (verified).
2. Migration 0013 adds CheckConstraints verdict_matches_reviewer_role (REJECTED | PRE_APPROVED+NURSE | APPROVED+DOCTOR) and rejection_has_reason_and_detail (REJECTED needs non-empty reason and content; others need empty reason), both with impersonal violation_error_message. clean() gained matching status rules (keyed on status).
3. Tests in backend/api/tests/test_dictamen.py: clean() for both mismatches, either role may reject, and DictamenDatabaseConstraintTests using objects.create() asserting IntegrityError names the constraint (5 refusals + legal combinations stored).
Command: `manage.py test api.tests.test_dictamen` -> 21 tests OK. Could-fail: neutralising the AddConstraint in 0013 made 5 constraint tests FAIL (reverted). Full suite: 59 OK. `makemigrations --check --dry-run` -> "No changes detected".
