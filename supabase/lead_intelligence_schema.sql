-- ============================================================
-- QEVN LEAD INTELLIGENCE — SUPABASE POSTGRESQL SCHEMA
-- Run this script in the Supabase Dashboard -> SQL Editor
-- ============================================================

-- 1. LEADS TABLE
CREATE TABLE IF NOT EXISTS public.leads (
    id TEXT PRIMARY KEY,
    score NUMERIC(5, 2) NOT NULL DEFAULT 50.0,
    temperature TEXT NOT NULL DEFAULT 'COOL',
    status TEXT NOT NULL DEFAULT 'new',
    company_name TEXT NOT NULL,
    person_name TEXT NOT NULL DEFAULT 'Unknown',
    industry TEXT DEFAULT 'Unknown',
    location TEXT DEFAULT 'Unknown',
    has_email BOOLEAN DEFAULT FALSE,
    has_phone BOOLEAN DEFAULT FALSE,
    is_decision_maker BOOLEAN DEFAULT FALSE,
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    last_enriched TIMESTAMPTZ,
    in_watchlist BOOLEAN DEFAULT FALSE,
    data_json JSONB NOT NULL
);

-- Indexes for lightning-fast CRM filters and sorting
CREATE INDEX IF NOT EXISTS idx_supabase_leads_score ON public.leads(score DESC);
CREATE INDEX IF NOT EXISTS idx_supabase_leads_temp ON public.leads(temperature);
CREATE INDEX IF NOT EXISTS idx_supabase_leads_status ON public.leads(status);
CREATE INDEX IF NOT EXISTS idx_supabase_leads_company ON public.leads(company_name);
CREATE INDEX IF NOT EXISTS idx_supabase_leads_last_seen ON public.leads(last_seen DESC);

-- 2. SEARCH RUNS AUDIT LOG
CREATE TABLE IF NOT EXISTS public.search_runs (
    run_id TEXT PRIMARY KEY,
    user_query TEXT NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    result_count INT DEFAULT 0,
    qualified_count INT DEFAULT 0,
    data_json JSONB NOT NULL
);

-- 3. HISTORICAL FEEDBACK & OUTCOMES (ML Training Labels)
CREATE TABLE IF NOT EXISTS public.lead_outcomes (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    lead_id TEXT NOT NULL REFERENCES public.leads(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    label INT NOT NULL, -- 1 for positive (won, meeting, etc.), 0 for negative (lost, disqualified)
    features_json JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_supabase_outcomes_lead ON public.lead_outcomes(lead_id);
CREATE INDEX IF NOT EXISTS idx_supabase_outcomes_label ON public.lead_outcomes(label);

-- 4. COMPANY SIGNAL PROFILES (Cached Multi-Post Aggregations)
CREATE TABLE IF NOT EXISTS public.company_profiles (
    company_name TEXT PRIMARY KEY,
    data_json JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. ML MODEL METADATA
CREATE TABLE IF NOT EXISTS public.model_metadata (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    model_name TEXT NOT NULL,
    version TEXT NOT NULL,
    metrics_json JSONB NOT NULL,
    feature_names_json JSONB NOT NULL,
    trained_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Row-Level Security (RLS) configuration
ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.search_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lead_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.company_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.model_metadata ENABLE ROW LEVEL SECURITY;

-- Allow service_role and anon full read/write for development
CREATE POLICY "Allow public read-write for leads" ON public.leads FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public read-write for search_runs" ON public.search_runs FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public read-write for lead_outcomes" ON public.lead_outcomes FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public read-write for company_profiles" ON public.company_profiles FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public read-write for model_metadata" ON public.model_metadata FOR ALL USING (true) WITH CHECK (true);
