# SQL migrations

Ordered files in this directory are applied at application startup and recorded in `schema_migrations`.

- Filename order is the migration order (`001_…`, `002_…`, …).
- Each file runs at most once per database.
- Fresh Postgres volumes still run `sql/01_schema.sql` and `sql/02_sample_data.sql` on init; migrations cover upgrades on existing volumes.

Add a new migration when changing production schema. Do not edit applied migration files in place.
