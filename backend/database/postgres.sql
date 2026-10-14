CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE organizations (id uuid PRIMARY KEY, name text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE users (id uuid PRIMARY KEY, organization_id uuid NOT NULL REFERENCES organizations(id), email citext NOT NULL UNIQUE, role text NOT NULL CHECK (role IN ('owner','admin','analyst','viewer')), created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE organization_profiles (organization_id uuid PRIMARY KEY REFERENCES organizations(id), industry text, employee_count integer, contractor_ratio_pct numeric, monthly_revenue_toman numeric, updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE decisions (id uuid PRIMARY KEY, organization_id uuid NOT NULL REFERENCES organizations(id), title text NOT NULL, rationale text NOT NULL, supporting_document text, risk_level text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE alerts (id uuid PRIMARY KEY, organization_id uuid NOT NULL REFERENCES organizations(id), title text NOT NULL, body text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), read_at timestamptz);
CREATE TABLE connectors (id uuid PRIMARY KEY, organization_id uuid NOT NULL REFERENCES organizations(id), name text NOT NULL, kind text NOT NULL CHECK (kind IN ('hr','finance')), base_url text NOT NULL, secret_reference text NOT NULL, enabled boolean NOT NULL DEFAULT true, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE regulations (id uuid PRIMARY KEY, title text NOT NULL, body text NOT NULL, source_url text, source_name text NOT NULL, source_version text NOT NULL, published_on date, effective_from date, effective_to date, embedding vector(1536), created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(source_name, source_version));
CREATE INDEX regulations_embedding_idx ON regulations USING hnsw (embedding vector_cosine_ops);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE connectors ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_tenant_scope ON users USING (organization_id = current_setting('app.organization_id', true)::uuid);
CREATE POLICY profile_tenant_scope ON organization_profiles USING (organization_id = current_setting('app.organization_id', true)::uuid);
CREATE POLICY decision_tenant_scope ON decisions USING (organization_id = current_setting('app.organization_id', true)::uuid);
CREATE POLICY alert_tenant_scope ON alerts USING (organization_id = current_setting('app.organization_id', true)::uuid);
CREATE POLICY connector_tenant_scope ON connectors USING (organization_id = current_setting('app.organization_id', true)::uuid);

-- Every tenant-owned table must use the same RLS policy. Set app.organization_id
-- from the verified bearer-token principal at the beginning of each transaction.
