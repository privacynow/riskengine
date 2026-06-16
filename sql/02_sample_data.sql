-- ==========================================================================
-- SAMPLE DATA DML SCRIPT (sample_data.sql)
-- Populate sample tenant, checkpoints, signals, etc.
-- ==========================================================================

\c risk_engine_db

---------------------------------------
-- 1) Sample Tenant
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
-- 2) Sample Checkpoints
---------------------------------------
-- Onboarding
INSERT INTO checkpoints (
    id, tenant_id, name, description, type, dsl_expression, method_of_call,
    max_cost, override_cost_flag, timeout_seconds
)
SELECT
  '22222222-2222-2222-2222-222222222201',
  '11111111-1111-1111-1111-111111111111',
  'Onboarding',
  'Initial user onboarding checkpoint.',
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
  'Regulatory compliance checkpoint.',
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
  'Core underwriting checkpoint.',
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
  'Disbursement approval checkpoint.',
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
  'Repayment or servicing checkpoint.',
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
-- 3) Sample Signals
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
  'Boolean signal if age >= 18',
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
  'Boolean signal if user is blocklisted',
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
  'Number of previous delinquencies',
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
  'Boolean signal if user has an active loan',
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
  'Internal doc verification (POST with user data)',
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
  'Internal sanction screening (GET with query param)',
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
  'External endpoint returning user KYC score (0-100)',
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
  'External endpoint returning credit score (0-100)',
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
  'Local function verifying income',
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
  'Local function checking loan amount',
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
  'Function verifying disbursement limit',
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
  'Expression: previous_delinquency * 5',
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
  'Expression referencing delinquent_days',
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
-- 4) Associate signals with checkpoints
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
-- 5) Sample "variable" signal values
--    in the new "signal_variable_values" table
---------------------------------------
-- The new table is keyed by (id, signal_id, name, value)
-- with no "decision_id".
-- We'll just store some default values to demonstrate.
---------------------------------------

-- Age check (stores as 'True')
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

-- Blocklist check (stores as 'False')
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

-- Previous delinquency (stores as '0')
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

-- Active loan (stores as 'True')
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
-- 5b) Second tenant — same checkpoint name, different outcome (multi-tenant demo)
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
  'Always-decline onboarding checkpoint for multi-tenant demos.',
  'onboarding',
  'False',
  NULL,
  100,
  FALSE,
  30
WHERE NOT EXISTS (
  SELECT 1 FROM checkpoints
   WHERE name = 'Onboarding'
     AND tenant_id = '99999999-9999-9999-9999-999999999999'
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
-- 6) Seed current-version pointers for sample checkpoints and signals
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
-- Optionally, insert a placeholder decision if desired
-- (Just as a sample row in decision_log; no direct link to variable values.)
---------------------------------------
INSERT INTO decision_log (
  id, checkpoint_id, tenant_id, applicant_id,
  final_decision_value, cost_incurred, correlation_id, decision_timestamp
)
SELECT
  '44444444-4444-4444-4444-444444444444',
  '22222222-2222-2222-2222-222222222201',
  '11111111-1111-1111-1111-111111111111',
  'sample_user',
  'PENDING',
  0,
  'placeholder_correlation',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM decision_log
   WHERE id = '44444444-4444-4444-4444-444444444444'
);

---------------------------------------
-- 7) Inactive signal — linked but not current (strict resolution demo)
-- Inserted after current-version seed so it is deliberately excluded.
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
  'Linked to Onboarding but not in signal_current_version; must not execute.',
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
