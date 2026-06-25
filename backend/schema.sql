-- Run this in your Supabase project → SQL Editor → New query

CREATE TABLE IF NOT EXISTS analysis_results (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ticker TEXT NOT NULL,
    decision TEXT,
    conviction TEXT,
    target_weight TEXT,
    credit_score DOUBLE PRECISION,
    regime TEXT,
    key_thesis TEXT,
    weighted_signal DOUBLE PRECISION,
    agent_outputs JSONB DEFAULT '{}'::jsonb,
    errors JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analysis_ticker ON analysis_results(ticker);
CREATE INDEX IF NOT EXISTS idx_analysis_created ON analysis_results(created_at DESC);

CREATE TABLE IF NOT EXISTS credit_scores (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ticker TEXT NOT NULL,
    credit_score DOUBLE PRECISION,
    default_probability DOUBLE PRECISION,
    risk_label TEXT,
    features JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_credit_ticker ON credit_scores(ticker);

CREATE TABLE IF NOT EXISTS agent_run_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ticker TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    thesis TEXT,
    confidence INTEGER,
    summary TEXT,
    full_output JSONB DEFAULT '{}'::jsonb,
    run_duration_ms INTEGER,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_logs_ticker ON agent_run_logs(ticker);

-- Allow the anon key (used by the backend) to read and write all tables.
-- RLS is enabled by default on new Supabase tables; these policies open it up
-- for the anon role so the FastAPI backend can persist analysis results.

ALTER TABLE analysis_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_scores    ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_run_logs   ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_all" ON analysis_results;
DROP POLICY IF EXISTS "anon_all" ON credit_scores;
DROP POLICY IF EXISTS "anon_all" ON agent_run_logs;

CREATE POLICY "anon_all" ON analysis_results FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON credit_scores    FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all" ON agent_run_logs   FOR ALL TO anon USING (true) WITH CHECK (true);
