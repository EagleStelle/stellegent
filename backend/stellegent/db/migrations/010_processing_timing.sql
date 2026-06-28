-- Per-lecture processing latency, stored as compact JSON so the stage list can
-- evolve without another schema change.
ALTER TABLE lectures ADD COLUMN processing_timing TEXT;
