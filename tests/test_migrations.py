def test_schema_migrations_table_exists():
    from engine.db import db_cursor

    with db_cursor() as (conn, cur):
        cur.execute(
            """
            SELECT version FROM schema_migrations
             ORDER BY version
            """
        )
        versions = [row[0] for row in cur.fetchall()]
        conn.commit()
    assert "001_promotion_audit.sql" in versions
    assert "002_promotion_audit_action.sql" in versions
    assert "003_signal_log_error_message.sql" in versions
    assert "004_execution_planner.sql" in versions


def test_signal_log_error_message_column():
    from engine.db import db_cursor

    with db_cursor() as (conn, cur):
        cur.execute(
            """
            SELECT column_name
              FROM information_schema.columns
             WHERE table_name = 'signal_log'
               AND column_name = 'error_message'
            """
        )
        assert cur.fetchone() is not None
        conn.commit()
