-- ==========================================================================
-- PRODUCT DEMO SEED (02_sample_data.sql)
-- Idempotent demo bootstrap for Docker init and integration tests.
-- Stable IDs: see sql/README.md
-- Visual regression data lives in tests/fixtures/visual_fixture.sql only.
-- ==========================================================================
--
-- Demo tenant: SAMPLE LENDING — primary lending lifecycle showcase
-- Demo tenant: OTHER BANK — multi-tenant isolation with a stricter policy
--
-- Sections:
--   1. SAMPLE LENDING checkpoints (stable names for tests/smoke)
--   2. SAMPLE LENDING signals (variables, endpoints, functions, expressions)
--   3. Checkpoint ↔ signal associations
--   4. Variable signal defaults (realistic demo values)
--   5. OTHER BANK tenant + stricter onboarding policy
--   6. Current-version pointers
--   7. Sample audit row for overview/search demos
--   8. Inactive signal strict-resolution demo
--   9. Demo policy refresh (UPDATE existing rows on re-apply)
-- ==========================================================================

\c risk_engine_db

---------------------------------------
-- 1) Demo tenant: SAMPLE LENDING
---------------------------------------
INSERT INTO tenants (id, name)
SELECT uuid_generate_v4(), 'SAMPLE LENDING'
WHERE NOT EXISTS (
    SELECT 1 FROM tenants WHERE name = 'SAMPLE LENDING'
)
RETURNING id;

UPDATE tenants
SET id = '11111111-1111-1111-1111-111111111111'
WHERE name = 'SAMPLE LENDING'
  AND id <> '11111111-1111-1111-1111-111111111111';


---------------------------------------
-- 2) SAMPLE LENDING checkpoints
---------------------------------------
-- Onboarding (stable name + DSL for tests/smoke)
INSERT INTO checkpoints (
    id, tenant_id, name, description, type, dsl_expression, method_of_call,
    max_cost, override_cost_flag, timeout_seconds
)
SELECT
  '22222222-2222-2222-2222-222222222201',
  '11111111-1111-1111-1111-111111111111',
  'Onboarding',
  'Application intake — identity, watchlists, and KYC score before account opening.',
  'onboarding',
  'age_check and not (blocklist_check) and (kyc_score > 80)',
  'http://127.0.0.1:8000/mock/onboarding',
  100,
  FALSE,
  30
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoints
   WHERE name = 'Onboarding'
     AND tenant_id = '11111111-1111-1111-1111-111111111111'
);

-- Compliance
INSERT INTO checkpoints (
    id, tenant_id, name, description, type, dsl_expression, method_of_call,
    max_cost, override_cost_flag, timeout_seconds
)
SELECT
  '22222222-2222-2222-2222-222222222202',
  '11111111-1111-1111-1111-111111111111',
  'Compliance',
  'Document authenticity and sanctions screening for regulatory onboarding.',
  'compliance',
  'doc_verification and sanction_screening',
  'http://127.0.0.1:8000/mock/compliance',
  200,
  FALSE,
  30
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoints
   WHERE name = 'Compliance'
     AND tenant_id = '11111111-1111-1111-1111-111111111111'
);

-- Underwriting
INSERT INTO checkpoints (
    id, tenant_id, name, description, type, dsl_expression, method_of_call,
    max_cost, override_cost_flag, timeout_seconds
)
SELECT
  '22222222-2222-2222-2222-222222222203',
  '11111111-1111-1111-1111-111111111111',
  'Underwriting',
  'Credit eligibility, income verification, and requested amount limits.',
  'underwriting',
  '(credit_score > 70) and income_verification and (loan_amount_check < 50000)',
  'http://127.0.0.1:8000/mock/underwriting',
  300,
  FALSE,
  60
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoints
   WHERE name = 'Underwriting'
     AND tenant_id = '11111111-1111-1111-1111-111111111111'
);

-- Funds Disbursement
INSERT INTO checkpoints (
    id, tenant_id, name, description, type, dsl_expression, method_of_call,
    max_cost, override_cost_flag, timeout_seconds
)
SELECT
  '22222222-2222-2222-2222-222222222204',
  '11111111-1111-1111-1111-111111111111',
  'Funds Disbursement',
  'Disbursement readiness — limits and delinquency guardrails before funding.',
  'funds_disbursement',
  'disbursement_limit_check and (previous_delinquency == 0)',
  'http://127.0.0.1:8000/mock/disbursement',
  100,
  FALSE,
  30
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoints
   WHERE name = 'Funds Disbursement'
     AND tenant_id = '11111111-1111-1111-1111-111111111111'
);

-- Servicing
INSERT INTO checkpoints (
    id, tenant_id, name, description, type, dsl_expression, method_of_call,
    max_cost, override_cost_flag, timeout_seconds
)
SELECT
  '22222222-2222-2222-2222-222222222205',
  '11111111-1111-1111-1111-111111111111',
  'Servicing',
  'Servicing intervention — active loan status and delinquency severity.',
  'servicing',
  '(active_loan == TRUE) and (delinquent_severity < 60)',
  'http://127.0.0.1:8000/mock/servicing',
  50,
  FALSE,
  30
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoints
   WHERE name = 'Servicing'
     AND tenant_id = '11111111-1111-1111-1111-111111111111'
);


---------------------------------------
-- 3) SAMPLE LENDING signals
---------------------------------------
-- age_check (variable)
INSERT INTO signals (
    id, tenant_id, name, description, type, method_of_call, expression_body,
    cost, cache_expiration_seconds, timeout_seconds, can_run_in_parallel,
    order_of_evaluation, http_method, request_url_params_template,
    request_body_template, request_headers_template, bearer_token,
    allow_caching, global_reuse, function_params_template
)
SELECT
  '33333333-3333-3333-3333-333333333301',
  '11111111-1111-1111-1111-111111111111',
  'age_check',
  'Applicant meets minimum age requirement (18+).',
  'variable',
  NULL,
  NULL,
  5,
  300,
  5,
  TRUE,
  1,
  NULL,
  NULL,
  NULL,
  NULL,
  NULL,
  TRUE,
  FALSE,
  NULL
WHERE NOT EXISTS (
  SELECT 1 FROM signals
   WHERE name = 'age_check'
     AND tenant_id = '11111111-1111-1111-1111-111111111111'
);

-- blocklist_check (variable)
INSERT INTO signals (
    id, tenant_id, name, description, type, method_of_call, expression_body,
    cost, cache_expiration_seconds, timeout_seconds, can_run_in_parallel,
    order_of_evaluation, http_method, request_url_params_template,
    request_body_template, request_headers_template, bearer_token,
    allow_caching, global_reuse, function_params_template
)
SELECT
  '33333333-3333-3333-3333-333333333302',
  '11111111-1111-1111-1111-111111111111',
  'blocklist_check',
  'Applicant appears on internal fraud or sanctions watchlist.',
  'variable',
  NULL,
  NULL,
  10,
  300,
  5,
  TRUE,
  1,
  NULL,
  NULL,
  NULL,
  NULL,
  NULL,
  TRUE,
  TRUE,
  NULL
WHERE NOT EXISTS (
  SELECT 1 FROM signals
   WHERE name = 'blocklist_check'
     AND tenant_id = '11111111-1111-1111-1111-111111111111'
);

-- previous_delinquency (variable)
INSERT INTO signals (
    id, tenant_id, name, description, type, method_of_call, expression_body,
    cost, cache_expiration_seconds, timeout_seconds, can_run_in_parallel,
    order_of_evaluation, http_method, request_url_params_template,
    request_body_template, request_headers_template, bearer_token,
    allow_caching, global_reuse, function_params_template
)
SELECT
  '33333333-3333-3333-3333-333333333303',
  '11111111-1111-1111-1111-111111111111',
  'previous_delinquency',
  'Count of prior delinquency events in the last 24 months.',
  'variable',
  NULL,
  NULL,
  10,
  300,
  5,
  TRUE,
  1,
  NULL,
  NULL,
  NULL,
  NULL,
  NULL,
  TRUE,
  FALSE,
  NULL
WHERE NOT EXISTS (
  SELECT 1 FROM signals
   WHERE name = 'previous_delinquency'
     AND tenant_id = '11111111-1111-1111-1111-111111111111'
);

-- active_loan (variable)
INSERT INTO signals (
    id, tenant_id, name, description, type, method_of_call, expression_body,
    cost, cache_expiration_seconds, timeout_seconds, can_run_in_parallel,
    order_of_evaluation, http_method, request_url_params_template,
    request_body_template, request_headers_template, bearer_token,
    allow_caching, global_reuse, function_params_template
)
SELECT
  '33333333-3333-3333-3333-333333333304',
  '11111111-1111-1111-1111-111111111111',
  'active_loan',
  'Whether the applicant currently has an active loan on file.',
  'variable',
  NULL,
  NULL,
  5,
  300,
  5,
  TRUE,
  1,
  NULL,
  NULL,
  NULL,
  NULL,
  NULL,
  TRUE,
  FALSE,
  NULL
WHERE NOT EXISTS (
  SELECT 1 FROM signals
   WHERE name = 'active_loan'
     AND tenant_id = '11111111-1111-1111-1111-111111111111'
);

-- doc_verification (internal_endpoint)
INSERT INTO signals (
    id, tenant_id, name, description, type, method_of_call, expression_body,
    cost, cache_expiration_seconds, timeout_seconds, can_run_in_parallel,
    order_of_evaluation, http_method, request_url_params_template,
    request_body_template, request_headers_template, bearer_token,
    allow_caching, global_reuse, function_params_template
)
SELECT
  '33333333-3333-3333-3333-333333333305',
  '11111111-1111-1111-1111-111111111111',
  'doc_verification',
  'Document authenticity verified via internal POST service with applicant profile payload.',
  'internal_endpoint',
  'http://127.0.0.1:8000/mock/doc-verify',
  NULL,
  20,
  600,
  10,
  TRUE,
  1,
  'POST',
  NULL,
  '{"documentType": "ID", "userId": "%applicant_id%"}',
  NULL,
  NULL,
  TRUE,
  FALSE,
  NULL
WHERE NOT EXISTS (
  SELECT 1 FROM signals
   WHERE name = 'doc_verification'
     AND tenant_id = '11111111-1111-1111-1111-111111111111'
);

-- sanction_screening (internal_endpoint)
INSERT INTO signals (
    id, tenant_id, name, description, type, method_of_call, expression_body,
    cost, cache_expiration_seconds, timeout_seconds, can_run_in_parallel,
    order_of_evaluation, http_method, request_url_params_template,
    request_body_template, request_headers_template, bearer_token,
    allow_caching, global_reuse, function_params_template
)
SELECT
  '33333333-3333-3333-3333-333333333306',
  '11111111-1111-1111-1111-111111111111',
  'sanction_screening',
  'Sanctions and PEP screening via internal GET service with applicant identifier.',
  'internal_endpoint',
  'http://127.0.0.1:8000/mock/sanction-screen',
  NULL,
  20,
  600,
  10,
  TRUE,
  1,
  'GET',
  'userId=%applicant_id%',
  NULL,
  NULL,
  NULL,
  TRUE,
  TRUE,
  NULL
WHERE NOT EXISTS (
  SELECT 1 FROM signals
   WHERE name = 'sanction_screening'
     AND tenant_id = '11111111-1111-1111-1111-111111111111'
);

-- kyc_score (external_endpoint)
INSERT INTO signals (
    id, tenant_id, name, description, type, method_of_call, expression_body,
    cost, cache_expiration_seconds, timeout_seconds, can_run_in_parallel,
    order_of_evaluation, http_method, request_url_params_template,
    request_body_template, request_headers_template, bearer_token,
    allow_caching, global_reuse, function_params_template
)
SELECT
  '33333333-3333-3333-3333-333333333307',
  '11111111-1111-1111-1111-111111111111',
  'kyc_score',
  'Know-your-customer composite score (0–100) from external identity bureau.',
  'external_endpoint',
  'http://127.0.0.1:8000/mock/kyc_score',
  NULL,
  30,
  600,
  15,
  TRUE,
  1,
  'GET',
  'ssn=%user_ssn%',
  NULL,
  NULL,
  NULL,
  TRUE,
  FALSE,
  NULL
WHERE NOT EXISTS (
  SELECT 1 FROM signals
   WHERE name = 'kyc_score'
     AND tenant_id = '11111111-1111-1111-1111-111111111111'
);

-- credit_score (external_endpoint)
INSERT INTO signals (
    id, tenant_id, name, description, type, method_of_call, expression_body,
    cost, cache_expiration_seconds, timeout_seconds, can_run_in_parallel,
    order_of_evaluation, http_method, request_url_params_template,
    request_body_template, request_headers_template, bearer_token,
    allow_caching, global_reuse, function_params_template
)
SELECT
  '33333333-3333-3333-3333-333333333308',
  '11111111-1111-1111-1111-111111111111',
  'credit_score',
  'Primary bureau credit score (300–850) from external credit pull.',
  'external_endpoint',
  'http://127.0.0.1:8000/mock/credit_score',
  NULL,
  30,
  600,
  15,
  TRUE,
  1,
  'POST',
  NULL,
  '{"ssn": "%user_ssn%"}',
  NULL,
  NULL,
  TRUE,
  FALSE,
  NULL
WHERE NOT EXISTS (
  SELECT 1 FROM signals
   WHERE name = 'credit_score'
     AND tenant_id = '11111111-1111-1111-1111-111111111111'
);

-- income_verification (function)
INSERT INTO signals (
    id, tenant_id, name, description, type, method_of_call, expression_body,
    cost, cache_expiration_seconds, timeout_seconds, can_run_in_parallel,
    order_of_evaluation, http_method, request_url_params_template,
    request_body_template, request_headers_template, bearer_token,
    allow_caching, global_reuse, function_params_template
)
SELECT
  '33333333-3333-3333-3333-333333333309',
  '11111111-1111-1111-1111-111111111111',
  'income_verification',
  'Verified gross monthly income meets policy floor for requested product.',
  'function',
  'income_verification',
  NULL,
  25,
  300,
  10,
  TRUE,
  1,
  NULL,
  NULL,
  NULL,
  NULL,
  NULL,
  TRUE,
  FALSE,
  '{"min_income":"30000","applicant_param":"%applicant_id%"}'
WHERE NOT EXISTS (
  SELECT 1 FROM signals
   WHERE name = 'income_verification'
     AND tenant_id = '11111111-1111-1111-1111-111111111111'
);

-- loan_amount_check (function)
INSERT INTO signals (
    id, tenant_id, name, description, type, method_of_call, expression_body,
    cost, cache_expiration_seconds, timeout_seconds, can_run_in_parallel,
    order_of_evaluation, http_method, request_url_params_template,
    request_body_template, request_headers_template, bearer_token,
    allow_caching, global_reuse, function_params_template
)
SELECT
  '33333333-3333-3333-3333-333333333310',
  '11111111-1111-1111-1111-111111111111',
  'loan_amount_check',
  'Requested principal within product limit and affordability rules.',
  'function',
  'loan_amount_check',
  NULL,
  25,
  300,
  10,
  TRUE,
  1,
  NULL,
  NULL,
  NULL,
  NULL,
  NULL,
  TRUE,
  FALSE,
  '{"max_loan":"50000"}'
WHERE NOT EXISTS (
  SELECT 1 FROM signals
   WHERE name = 'loan_amount_check'
     AND tenant_id = '11111111-1111-1111-1111-111111111111'
);

-- disbursement_limit_check (function)
INSERT INTO signals (
    id, tenant_id, name, description, type, method_of_call, expression_body,
    cost, cache_expiration_seconds, timeout_seconds, can_run_in_parallel,
    order_of_evaluation, http_method, request_url_params_template,
    request_body_template, request_headers_template, bearer_token,
    allow_caching, global_reuse, function_params_template
)
SELECT
  '33333333-3333-3333-3333-333333333311',
  '11111111-1111-1111-1111-111111111111',
  'disbursement_limit_check',
  'Outstanding exposure plus requested disbursement within tenant limit.',
  'function',
  'disbursement_limit_check',
  NULL,
  25,
  300,
  10,
  TRUE,
  1,
  NULL,
  NULL,
  NULL,
  NULL,
  NULL,
  TRUE,
  FALSE,
  '{"limit":"100000","applicant":"%applicant_id%"}'
WHERE NOT EXISTS (
  SELECT 1 FROM signals
   WHERE name = 'disbursement_limit_check'
     AND tenant_id = '11111111-1111-1111-1111-111111111111'
);

-- delinquent_days (expression)
INSERT INTO signals (
    id, tenant_id, name, description, type, method_of_call, expression_body,
    cost, cache_expiration_seconds, timeout_seconds, can_run_in_parallel,
    order_of_evaluation, http_method, request_url_params_template,
    request_body_template, request_headers_template, bearer_token,
    allow_caching, global_reuse, function_params_template
)
SELECT
  '33333333-3333-3333-3333-333333333312',
  '11111111-1111-1111-1111-111111111111',
  'delinquent_days',
  'Derived delinquency exposure in days (prior events × severity factor).',
  'expression',
  NULL,
  'previous_delinquency * 5',
  5,
  300,
  5,
  TRUE,
  2,
  NULL,
  NULL,
  NULL,
  NULL,
  NULL,
  TRUE,
  FALSE,
  NULL
WHERE NOT EXISTS (
  SELECT 1 FROM signals
   WHERE name = 'delinquent_days'
     AND tenant_id = '11111111-1111-1111-1111-111111111111'
);

-- delinquent_severity (expression)
INSERT INTO signals (
    id, tenant_id, name, description, type, method_of_call, expression_body,
    cost, cache_expiration_seconds, timeout_seconds, can_run_in_parallel,
    order_of_evaluation, http_method, request_url_params_template,
    request_body_template, request_headers_template, bearer_token,
    allow_caching, global_reuse, function_params_template
)
SELECT
  '33333333-3333-3333-3333-333333333313',
  '11111111-1111-1111-1111-111111111111',
  'delinquent_severity',
  'Weighted delinquency severity score used in servicing intervention rules.',
  'expression',
  NULL,
  'delinquent_days + 10',
  5,
  300,
  5,
  TRUE,
  3,
  NULL,
  NULL,
  NULL,
  NULL,
  NULL,
  TRUE,
  FALSE,
  NULL
WHERE NOT EXISTS (
  SELECT 1 FROM signals
   WHERE name = 'delinquent_severity'
     AND tenant_id = '11111111-1111-1111-1111-111111111111'
);


---------------------------------------
-- 4) Checkpoint ↔ signal associations (SAMPLE LENDING)
---------------------------------------
-- Onboarding
INSERT INTO checkpoint_signals (id, checkpoint_id, signal_id)
SELECT uuid_generate_v4(),
       '22222222-2222-2222-2222-222222222201',
       '33333333-3333-3333-3333-333333333301'
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoint_signals
   WHERE checkpoint_id = '22222222-2222-2222-2222-222222222201'
     AND signal_id = '33333333-3333-3333-3333-333333333301'
);

INSERT INTO checkpoint_signals (id, checkpoint_id, signal_id)
SELECT uuid_generate_v4(),
       '22222222-2222-2222-2222-222222222201',
       '33333333-3333-3333-3333-333333333302'
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoint_signals
   WHERE checkpoint_id = '22222222-2222-2222-2222-222222222201'
     AND signal_id = '33333333-3333-3333-3333-333333333302'
);

INSERT INTO checkpoint_signals (id, checkpoint_id, signal_id)
SELECT uuid_generate_v4(),
       '22222222-2222-2222-2222-222222222201',
       '33333333-3333-3333-3333-333333333307'
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoint_signals
   WHERE checkpoint_id = '22222222-2222-2222-2222-222222222201'
     AND signal_id = '33333333-3333-3333-3333-333333333307'
);

-- Compliance
INSERT INTO checkpoint_signals (id, checkpoint_id, signal_id)
SELECT uuid_generate_v4(),
       '22222222-2222-2222-2222-222222222202',
       '33333333-3333-3333-3333-333333333305'
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoint_signals
   WHERE checkpoint_id = '22222222-2222-2222-2222-222222222202'
     AND signal_id = '33333333-3333-3333-3333-333333333305'
);

INSERT INTO checkpoint_signals (id, checkpoint_id, signal_id)
SELECT uuid_generate_v4(),
       '22222222-2222-2222-2222-222222222202',
       '33333333-3333-3333-3333-333333333306'
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoint_signals
   WHERE checkpoint_id = '22222222-2222-2222-2222-222222222202'
     AND signal_id = '33333333-3333-3333-3333-333333333306'
);

-- Underwriting
INSERT INTO checkpoint_signals (id, checkpoint_id, signal_id)
SELECT uuid_generate_v4(),
       '22222222-2222-2222-2222-222222222203',
       '33333333-3333-3333-3333-333333333308'
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoint_signals
   WHERE checkpoint_id = '22222222-2222-2222-2222-222222222203'
     AND signal_id = '33333333-3333-3333-3333-333333333308'
);

INSERT INTO checkpoint_signals (id, checkpoint_id, signal_id)
SELECT uuid_generate_v4(),
       '22222222-2222-2222-2222-222222222203',
       '33333333-3333-3333-3333-333333333309'
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoint_signals
   WHERE checkpoint_id = '22222222-2222-2222-2222-222222222203'
     AND signal_id = '33333333-3333-3333-3333-333333333309'
);

INSERT INTO checkpoint_signals (id, checkpoint_id, signal_id)
SELECT uuid_generate_v4(),
       '22222222-2222-2222-2222-222222222203',
       '33333333-3333-3333-3333-333333333310'
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoint_signals
   WHERE checkpoint_id = '22222222-2222-2222-2222-222222222203'
     AND signal_id = '33333333-3333-3333-3333-333333333310'
);

-- Funds Disbursement
INSERT INTO checkpoint_signals (id, checkpoint_id, signal_id)
SELECT uuid_generate_v4(),
       '22222222-2222-2222-2222-222222222204',
       '33333333-3333-3333-3333-333333333311'
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoint_signals
   WHERE checkpoint_id = '22222222-2222-2222-2222-222222222204'
     AND signal_id = '33333333-3333-3333-3333-333333333311'
);

INSERT INTO checkpoint_signals (id, checkpoint_id, signal_id)
SELECT uuid_generate_v4(),
       '22222222-2222-2222-2222-222222222204',
       '33333333-3333-3333-3333-333333333303'
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoint_signals
   WHERE checkpoint_id = '22222222-2222-2222-2222-222222222204'
     AND signal_id = '33333333-3333-3333-3333-333333333303'
);

-- Servicing
INSERT INTO checkpoint_signals (id, checkpoint_id, signal_id)
SELECT uuid_generate_v4(),
       '22222222-2222-2222-2222-222222222205',
       '33333333-3333-3333-3333-333333333304'
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoint_signals
   WHERE checkpoint_id = '22222222-2222-2222-2222-222222222205'
     AND signal_id = '33333333-3333-3333-3333-333333333304'
);

INSERT INTO checkpoint_signals (id, checkpoint_id, signal_id)
SELECT uuid_generate_v4(),
       '22222222-2222-2222-2222-222222222205',
       '33333333-3333-3333-3333-333333333312'
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoint_signals
   WHERE checkpoint_id = '22222222-2222-2222-2222-222222222205'
     AND signal_id = '33333333-3333-3333-3333-333333333312'
);

INSERT INTO checkpoint_signals (id, checkpoint_id, signal_id)
SELECT uuid_generate_v4(),
       '22222222-2222-2222-2222-222222222205',
       '33333333-3333-3333-3333-333333333313'
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoint_signals
   WHERE checkpoint_id = '22222222-2222-2222-2222-222222222205'
     AND signal_id = '33333333-3333-3333-3333-333333333313'
);


---------------------------------------
-- 5) Variable signal defaults (SAMPLE LENDING)
---------------------------------------

-- age_check — applicant is of legal age
INSERT INTO signal_variable_values (id, signal_id, name, value)
SELECT
  uuid_generate_v4(),
  '33333333-3333-3333-3333-333333333301',
  'age_check',
  'True'
WHERE NOT EXISTS (
  SELECT 1 FROM signal_variable_values
   WHERE signal_id = '33333333-3333-3333-3333-333333333301'
     AND name = 'age_check'
);

-- blocklist_check — applicant not on internal watchlist
INSERT INTO signal_variable_values (id, signal_id, name, value)
SELECT
  uuid_generate_v4(),
  '33333333-3333-3333-3333-333333333302',
  'blocklist_check',
  'False'
WHERE NOT EXISTS (
  SELECT 1 FROM signal_variable_values
   WHERE signal_id = '33333333-3333-3333-3333-333333333302'
     AND name = 'blocklist_check'
);

-- previous_delinquency — clean repayment history
INSERT INTO signal_variable_values (id, signal_id, name, value)
SELECT
  uuid_generate_v4(),
  '33333333-3333-3333-3333-333333333303',
  'previous_delinquency',
  '0'
WHERE NOT EXISTS (
  SELECT 1 FROM signal_variable_values
   WHERE signal_id = '33333333-3333-3333-3333-333333333303'
     AND name = 'previous_delinquency'
);

-- active_loan — servicing scenario has an active obligation
INSERT INTO signal_variable_values (id, signal_id, name, value)
SELECT
  uuid_generate_v4(),
  '33333333-3333-3333-3333-333333333304',
  'active_loan',
  'True'
WHERE NOT EXISTS (
  SELECT 1 FROM signal_variable_values
   WHERE signal_id = '33333333-3333-3333-3333-333333333304'
     AND name = 'active_loan'
);

---------------------------------------
-- 6) Demo tenant: OTHER BANK — stricter onboarding policy
-- Same checkpoint name as SAMPLE LENDING; different tenant policy and outcome.
---------------------------------------
INSERT INTO tenants (id, name)
SELECT '99999999-9999-9999-9999-999999999999', 'OTHER BANK'
WHERE NOT EXISTS (
  SELECT 1 FROM tenants WHERE name = 'OTHER BANK'
);

INSERT INTO checkpoints (
    id, tenant_id, name, description, type, dsl_expression, method_of_call,
    max_cost, override_cost_flag, timeout_seconds
)
SELECT
  '88888888-8888-8888-8888-888888888801',
  '99999999-9999-9999-9999-999999999999',
  'Onboarding',
  'Premium onboarding — stricter identity, sanctions, credit, and affordability gates.',
  'onboarding',
  'identity_verified and sanctions_clear and credit_score >= 740 and debt_to_income_ratio < 0.35',
  NULL,
  100,
  FALSE,
  30
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoints
   WHERE name = 'Onboarding'
     AND tenant_id = '99999999-9999-9999-9999-999999999999'
);

-- OTHER BANK policy signals (variables only — deterministic without mock HTTP)
INSERT INTO signals (
    id, tenant_id, name, description, type, cost, timeout_seconds,
    can_run_in_parallel, order_of_evaluation, allow_caching, global_reuse
)
SELECT
  '88888888-8888-8888-8888-888888888802',
  '99999999-9999-9999-9999-999999999999',
  'identity_verified',
  'Government ID and selfie verification passed.',
  'variable',
  5, 5, TRUE, 1, TRUE, FALSE
WHERE NOT EXISTS (
  SELECT 1 FROM signals
   WHERE tenant_id = '99999999-9999-9999-9999-999999999999'
     AND name = 'identity_verified'
);

INSERT INTO signals (
    id, tenant_id, name, description, type, cost, timeout_seconds,
    can_run_in_parallel, order_of_evaluation, allow_caching, global_reuse
)
SELECT
  '88888888-8888-8888-8888-888888888803',
  '99999999-9999-9999-9999-999999999999',
  'sanctions_clear',
  'Global sanctions and PEP screening returned no hits.',
  'variable',
  5, 5, TRUE, 1, TRUE, FALSE
WHERE NOT EXISTS (
  SELECT 1 FROM signals
   WHERE tenant_id = '99999999-9999-9999-9999-999999999999'
     AND name = 'sanctions_clear'
);

INSERT INTO signals (
    id, tenant_id, name, description, type, cost, timeout_seconds,
    can_run_in_parallel, order_of_evaluation, allow_caching, global_reuse
)
SELECT
  '88888888-8888-8888-8888-888888888804',
  '99999999-9999-9999-9999-999999999999',
  'credit_score',
  'Bureau credit score used for premium onboarding threshold.',
  'variable',
  5, 5, TRUE, 2, TRUE, FALSE
WHERE NOT EXISTS (
  SELECT 1 FROM signals
   WHERE tenant_id = '99999999-9999-9999-9999-999999999999'
     AND name = 'credit_score'
);

INSERT INTO signals (
    id, tenant_id, name, description, type, cost, timeout_seconds,
    can_run_in_parallel, order_of_evaluation, allow_caching, global_reuse
)
SELECT
  '88888888-8888-8888-8888-888888888805',
  '99999999-9999-9999-9999-999999999999',
  'debt_to_income_ratio',
  'Monthly debt obligations divided by verified gross income.',
  'variable',
  5, 5, TRUE, 2, TRUE, FALSE
WHERE NOT EXISTS (
  SELECT 1 FROM signals
   WHERE tenant_id = '99999999-9999-9999-9999-999999999999'
     AND name = 'debt_to_income_ratio'
);

INSERT INTO signal_variable_values (id, signal_id, name, value)
SELECT uuid_generate_v4(), '88888888-8888-8888-8888-888888888802', 'identity_verified', 'True'
WHERE NOT EXISTS (
  SELECT 1 FROM signal_variable_values
   WHERE signal_id = '88888888-8888-8888-8888-888888888802'
     AND name = 'identity_verified'
);

INSERT INTO signal_variable_values (id, signal_id, name, value)
SELECT uuid_generate_v4(), '88888888-8888-8888-8888-888888888803', 'sanctions_clear', 'True'
WHERE NOT EXISTS (
  SELECT 1 FROM signal_variable_values
   WHERE signal_id = '88888888-8888-8888-8888-888888888803'
     AND name = 'sanctions_clear'
);

INSERT INTO signal_variable_values (id, signal_id, name, value)
SELECT uuid_generate_v4(), '88888888-8888-8888-8888-888888888804', 'credit_score', '690'
WHERE NOT EXISTS (
  SELECT 1 FROM signal_variable_values
   WHERE signal_id = '88888888-8888-8888-8888-888888888804'
     AND name = 'credit_score'
);

INSERT INTO signal_variable_values (id, signal_id, name, value)
SELECT uuid_generate_v4(), '88888888-8888-8888-8888-888888888805', 'debt_to_income_ratio', '0.40'
WHERE NOT EXISTS (
  SELECT 1 FROM signal_variable_values
   WHERE signal_id = '88888888-8888-8888-8888-888888888805'
     AND name = 'debt_to_income_ratio'
);

INSERT INTO checkpoint_signals (id, checkpoint_id, signal_id)
SELECT uuid_generate_v4(), '88888888-8888-8888-8888-888888888801', '88888888-8888-8888-8888-888888888802'
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoint_signals
   WHERE checkpoint_id = '88888888-8888-8888-8888-888888888801'
     AND signal_id = '88888888-8888-8888-8888-888888888802'
);

INSERT INTO checkpoint_signals (id, checkpoint_id, signal_id)
SELECT uuid_generate_v4(), '88888888-8888-8888-8888-888888888801', '88888888-8888-8888-8888-888888888803'
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoint_signals
   WHERE checkpoint_id = '88888888-8888-8888-8888-888888888801'
     AND signal_id = '88888888-8888-8888-8888-888888888803'
);

INSERT INTO checkpoint_signals (id, checkpoint_id, signal_id)
SELECT uuid_generate_v4(), '88888888-8888-8888-8888-888888888801', '88888888-8888-8888-8888-888888888804'
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoint_signals
   WHERE checkpoint_id = '88888888-8888-8888-8888-888888888801'
     AND signal_id = '88888888-8888-8888-8888-888888888804'
);

INSERT INTO checkpoint_signals (id, checkpoint_id, signal_id)
SELECT uuid_generate_v4(), '88888888-8888-8888-8888-888888888801', '88888888-8888-8888-8888-888888888805'
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoint_signals
   WHERE checkpoint_id = '88888888-8888-8888-8888-888888888801'
     AND signal_id = '88888888-8888-8888-8888-888888888805'
);

INSERT INTO signal_current_version (tenant_id, name, signal_id)
SELECT '99999999-9999-9999-9999-999999999999', 'identity_verified', '88888888-8888-8888-8888-888888888802'
WHERE NOT EXISTS (
  SELECT 1 FROM signal_current_version
   WHERE tenant_id = '99999999-9999-9999-9999-999999999999'
     AND name = 'identity_verified'
);

INSERT INTO signal_current_version (tenant_id, name, signal_id)
SELECT '99999999-9999-9999-9999-999999999999', 'sanctions_clear', '88888888-8888-8888-8888-888888888803'
WHERE NOT EXISTS (
  SELECT 1 FROM signal_current_version
   WHERE tenant_id = '99999999-9999-9999-9999-999999999999'
     AND name = 'sanctions_clear'
);

INSERT INTO signal_current_version (tenant_id, name, signal_id)
SELECT '99999999-9999-9999-9999-999999999999', 'credit_score', '88888888-8888-8888-8888-888888888804'
WHERE NOT EXISTS (
  SELECT 1 FROM signal_current_version
   WHERE tenant_id = '99999999-9999-9999-9999-999999999999'
     AND name = 'credit_score'
);

INSERT INTO signal_current_version (tenant_id, name, signal_id)
SELECT '99999999-9999-9999-9999-999999999999', 'debt_to_income_ratio', '88888888-8888-8888-8888-888888888805'
WHERE NOT EXISTS (
  SELECT 1 FROM signal_current_version
   WHERE tenant_id = '99999999-9999-9999-9999-999999999999'
     AND name = 'debt_to_income_ratio'
);

INSERT INTO checkpoint_current_version (tenant_id, name, checkpoint_id)
SELECT
  '99999999-9999-9999-9999-999999999999',
  'Onboarding',
  '88888888-8888-8888-8888-888888888801'
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoint_current_version
   WHERE tenant_id = '99999999-9999-9999-9999-999999999999'
     AND name = 'Onboarding'
);

---------------------------------------
-- 7) Current-version pointers (SAMPLE LENDING)
---------------------------------------
INSERT INTO checkpoint_current_version (tenant_id, name, checkpoint_id)
SELECT c.tenant_id, c.name, c.id
  FROM checkpoints c
 WHERE c.tenant_id = '11111111-1111-1111-1111-111111111111'
ON CONFLICT (tenant_id, name) DO UPDATE
   SET checkpoint_id = EXCLUDED.checkpoint_id,
       updated_at = NOW();

INSERT INTO signal_current_version (tenant_id, name, signal_id)
SELECT s.tenant_id, s.name, s.id
  FROM signals s
 WHERE s.tenant_id = '11111111-1111-1111-1111-111111111111'
ON CONFLICT (tenant_id, name) DO UPDATE
   SET signal_id = EXCLUDED.signal_id,
       updated_at = NOW();

---------------------------------------
-- 8) Sample audit row for overview/search demos
---------------------------------------
INSERT INTO decision_log (
  id, checkpoint_id, tenant_id, applicant_id,
  final_decision_value, cost_incurred, correlation_id, decision_timestamp
)
SELECT
  '44444444-4444-4444-4444-444444444444',
  '22222222-2222-2222-2222-222222222201',
  '11111111-1111-1111-1111-111111111111',
  'demo-applicant-1042',
  'True',
  65,
  'demo-onboarding-approved',
  NOW() - INTERVAL '2 hours'
WHERE NOT EXISTS (
  SELECT 1 FROM decision_log
   WHERE id = '44444444-4444-4444-4444-444444444444'
);

---------------------------------------
-- 9) Inactive signal — linked but not current (strict resolution demo)
---------------------------------------
INSERT INTO signals (
    id, tenant_id, name, description, type, method_of_call,
    expression_body, cost, cache_expiration_seconds, timeout_seconds,
    can_run_in_parallel, order_of_evaluation
)
SELECT
  '77777777-7777-7777-7777-777777777701',
  '11111111-1111-1111-1111-111111111111',
  'inactive_demo',
  'Linked to Onboarding but excluded from signal_current_version; must not execute.',
  'expression',
  NULL,
  'False',
  1,
  0,
  30,
  FALSE,
  99
WHERE NOT EXISTS (
  SELECT 1 FROM signals WHERE id = '77777777-7777-7777-7777-777777777701'
);

INSERT INTO checkpoint_signals (id, checkpoint_id, signal_id)
SELECT
  '77777777-7777-7777-7777-777777777702',
  '22222222-2222-2222-2222-222222222201',
  '77777777-7777-7777-7777-777777777701'
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoint_signals
   WHERE checkpoint_id = '22222222-2222-2222-2222-222222222201'
     AND signal_id = '77777777-7777-7777-7777-777777777701'
);

---------------------------------------
-- 10) Demo policy refresh (UPDATE existing rows on re-apply)
---------------------------------------
UPDATE checkpoints
   SET description = 'Application intake — identity, watchlists, and KYC score before account opening.'
 WHERE id = '22222222-2222-2222-2222-222222222201';

UPDATE checkpoints
   SET description = 'Document authenticity and sanctions screening for regulatory onboarding.'
 WHERE id = '22222222-2222-2222-2222-222222222202';

UPDATE checkpoints
   SET description = 'Credit eligibility, income verification, and requested amount limits.'
 WHERE id = '22222222-2222-2222-2222-222222222203';

UPDATE checkpoints
   SET description = 'Disbursement readiness — limits and delinquency guardrails before funding.'
 WHERE id = '22222222-2222-2222-2222-222222222204';

UPDATE checkpoints
   SET description = 'Servicing intervention — active loan status and delinquency severity.'
 WHERE id = '22222222-2222-2222-2222-222222222205';

UPDATE checkpoints
   SET description = 'Premium onboarding — stricter identity, sanctions, credit, and affordability gates.',
       dsl_expression = 'identity_verified and sanctions_clear and credit_score >= 740 and debt_to_income_ratio < 0.35'
 WHERE id = '88888888-8888-8888-8888-888888888801';

-- SAMPLE LENDING signal descriptions
UPDATE signals
   SET description = 'Applicant meets minimum age requirement (18+).'
 WHERE id = '33333333-3333-3333-3333-333333333301';

UPDATE signals
   SET description = 'Applicant appears on internal fraud or sanctions watchlist.'
 WHERE id = '33333333-3333-3333-3333-333333333302';

UPDATE signals
   SET description = 'Count of prior delinquency events in the last 24 months.'
 WHERE id = '33333333-3333-3333-3333-333333333303';

UPDATE signals
   SET description = 'Whether the applicant currently has an active loan on file.'
 WHERE id = '33333333-3333-3333-3333-333333333304';

UPDATE signals
   SET description = 'Document authenticity verified via internal POST service with applicant profile payload.'
 WHERE id = '33333333-3333-3333-3333-333333333305';

UPDATE signals
   SET description = 'Sanctions and PEP screening via internal GET service with applicant identifier.'
 WHERE id = '33333333-3333-3333-3333-333333333306';

UPDATE signals
   SET description = 'Know-your-customer composite score (0–100) from external identity bureau.'
 WHERE id = '33333333-3333-3333-3333-333333333307';

UPDATE signals
   SET description = 'Primary bureau credit score (300–850) from external credit pull.'
 WHERE id = '33333333-3333-3333-3333-333333333308';

UPDATE signals
   SET description = 'Verified gross monthly income meets policy floor for requested product.'
 WHERE id = '33333333-3333-3333-3333-333333333309';

UPDATE signals
   SET description = 'Requested principal within product limit and affordability rules.'
 WHERE id = '33333333-3333-3333-3333-333333333310';

UPDATE signals
   SET description = 'Outstanding exposure plus requested disbursement within tenant limit.'
 WHERE id = '33333333-3333-3333-3333-333333333311';

UPDATE signals
   SET description = 'Derived delinquency exposure in days (prior events × severity factor).',
       expression_body = 'previous_delinquency * 5'
 WHERE id = '33333333-3333-3333-3333-333333333312';

UPDATE signals
   SET description = 'Weighted delinquency severity score used in servicing intervention rules.',
       expression_body = 'delinquent_days + 10'
 WHERE id = '33333333-3333-3333-3333-333333333313';

UPDATE signals
   SET description = 'Linked to Onboarding but excluded from signal_current_version; must not execute.'
 WHERE id = '77777777-7777-7777-7777-777777777701';

-- OTHER BANK signal descriptions
UPDATE signals
   SET description = 'Government ID and selfie verification passed.'
 WHERE id = '88888888-8888-8888-8888-888888888802';

UPDATE signals
   SET description = 'Global sanctions and PEP screening returned no hits.'
 WHERE id = '88888888-8888-8888-8888-888888888803';

UPDATE signals
   SET description = 'Bureau credit score used for premium onboarding threshold.'
 WHERE id = '88888888-8888-8888-8888-888888888804';

UPDATE signals
   SET description = 'Monthly debt obligations divided by verified gross income.'
 WHERE id = '88888888-8888-8888-8888-888888888805';

UPDATE decision_log
   SET applicant_id = 'demo-applicant-1042',
       final_decision_value = 'True',
       cost_incurred = 65,
       correlation_id = 'demo-onboarding-approved',
       decision_timestamp = NOW() - INTERVAL '2 hours'
 WHERE id = '44444444-4444-4444-4444-444444444444'
   AND final_decision_value = 'PENDING';

UPDATE signal_variable_values
   SET value = '690'
 WHERE signal_id = '88888888-8888-8888-8888-888888888804'
   AND name = 'credit_score';

UPDATE signal_variable_values
   SET value = '0.40'
 WHERE signal_id = '88888888-8888-8888-8888-888888888805'
   AND name = 'debt_to_income_ratio';
