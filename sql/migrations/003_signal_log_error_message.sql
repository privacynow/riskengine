ALTER TABLE signal_log
    ADD COLUMN IF NOT EXISTS error_message TEXT;
