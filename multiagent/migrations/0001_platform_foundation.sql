CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Baseline cho database moi. Database legacy da co cac bang nay thi giu
-- nguyen du lieu va duoc ALTER/backfill o phan sau.
CREATE TABLE IF NOT EXISTS review_job (
  id bigserial PRIMARY KEY,
  node_id text NOT NULL,
  content_hash text NOT NULL,
  status text NOT NULL,
  attempts int NOT NULL DEFAULT 0,
  run_after timestamptz NOT NULL DEFAULT now(),
  claimed_at timestamptz,
  claimed_by text,
  last_error text,
  source text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS run_log (
  id bigserial PRIMARY KEY,
  job_id bigint,
  node_id text NOT NULL,
  content_hash text NOT NULL,
  scored_at timestamptz NOT NULL DEFAULT now(),
  duration_ms int,
  decision text,
  final_score numeric,
  missing_agents jsonb NOT NULL DEFAULT '[]'::jsonb,
  veto_reason text,
  note text,
  agent_results jsonb NOT NULL,
  config_meta jsonb NOT NULL,
  usage jsonb NOT NULL,
  model text NOT NULL,
  payload jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS kb_chunk (
  collection text NOT NULL,
  chunk_id text NOT NULL,
  document text NOT NULL,
  embedding vector(1024) NOT NULL,
  content_type text NOT NULL,
  langcode text NOT NULL,
  meta jsonb NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (collection, chunk_id)
);

CREATE TABLE site (
  id uuid PRIMARY KEY,
  slug text NOT NULL UNIQUE,
  name text NOT NULL,
  connector_type text NOT NULL CHECK (connector_type IN ('drupal')),
  base_url text NOT NULL,
  secret_ref text NOT NULL,
  active boolean NOT NULL DEFAULT true,
  intake_paused boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE review_profile (
  id uuid PRIMARY KEY,
  code text NOT NULL UNIQUE,
  market_code char(2) NOT NULL,
  language_code text NOT NULL,
  content_type text NOT NULL,
  status text NOT NULL CHECK (status IN ('active', 'inactive')),
  policy_version text NOT NULL,
  policy_snapshot jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE site_profile_assignment (
  site_id uuid NOT NULL REFERENCES site(id),
  profile_id uuid NOT NULL REFERENCES review_profile(id),
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (site_id, profile_id)
);

INSERT INTO site (
  id, slug, name, connector_type, base_url, secret_ref, active, intake_paused
) VALUES (
  '00000000-0000-4000-8000-000000000001',
  'drupal-vn-primary',
  'Drupal Viet Nam primary',
  'drupal',
  'http://drupal.ddev.site',
  'DRUPAL',
  true,
  false
) ON CONFLICT DO NOTHING;

INSERT INTO review_profile (
  id, code, market_code, language_code, content_type, status,
  policy_version, policy_snapshot
) VALUES (
  '00000000-0000-4000-8000-000000000002',
  'cam-nang-vn',
  'VN',
  'vi',
  'cam_nang',
  'active',
  'cam-nang-vn-v1',
  '{
    "release": "cam-nang-vn-v1",
    "score_path_snapshot": "04f10e1",
    "prompt_version": "020738e209017213",
    "rubric_version": "v1",
    "model": "claude-haiku-4-5-20251001",
    "scoring_key": "cam_nang:vi",
    "scoring_sha256": "6ca88fc2ad60e72fcdd162bbc0e55441d32841160db9563bf13ffdb7d81ebd49",
    "compliance_rules_sha256": "edfd49d48e144f7e491ff8527650125370af72219e518222c4421c263ae4c6f6",
    "brand_rules_sha256": "f4c9d489363c1471dafd99335d91cb0c44427c01a24789de0fa7f119ef443f9a",
    "factcheck_kb_specs_sha256": "fe2185e06d64dcb237b8b49b683d42d4d3487f2bc7d1187de81e3b6ab05e6d61",
    "brand_guideline_sha256": "4a2e6d92a54858be511c2307f967be823c1ff6499d640b1646a3941f0b7686e3",
    "brand_corpus_index_sha256": "f0dcacda43765ebe858e1b12edeea910b828106f37ba9422bd313b9245c41175",
    "embedding_model": "BAAI/bge-m3",
    "embedding_dimension": 1024
  }'::jsonb
) ON CONFLICT DO NOTHING;

INSERT INTO site_profile_assignment (site_id, profile_id, active)
VALUES (
  '00000000-0000-4000-8000-000000000001',
  '00000000-0000-4000-8000-000000000002',
  true
) ON CONFLICT DO NOTHING;

ALTER TABLE review_job
  ADD COLUMN public_id uuid,
  ADD COLUMN site_id uuid,
  ADD COLUMN profile_id uuid,
  ADD COLUMN policy_version text,
  ADD COLUMN external_content_id text,
  ADD COLUMN external_revision_id text,
  ADD COLUMN content_type text,
  ADD COLUMN langcode text,
  ADD COLUMN correlation_id uuid,
  ADD COLUMN supersedes_job_id bigint;

UPDATE review_job SET
  public_id = COALESCE(public_id, gen_random_uuid()),
  site_id = COALESCE(site_id, '00000000-0000-4000-8000-000000000001'),
  profile_id = COALESCE(profile_id, '00000000-0000-4000-8000-000000000002'),
  policy_version = COALESCE(policy_version, 'cam-nang-vn-v1'),
  external_content_id = COALESCE(external_content_id, node_id),
  content_type = COALESCE(content_type, 'cam_nang'),
  langcode = COALESCE(langcode, 'vi'),
  correlation_id = COALESCE(correlation_id, gen_random_uuid());

ALTER TABLE review_job
  ALTER COLUMN public_id SET DEFAULT gen_random_uuid(),
  ALTER COLUMN public_id SET NOT NULL,
  ALTER COLUMN site_id SET NOT NULL,
  ALTER COLUMN profile_id SET NOT NULL,
  ALTER COLUMN policy_version SET NOT NULL,
  ALTER COLUMN external_content_id SET NOT NULL,
  ALTER COLUMN content_type SET NOT NULL,
  ALTER COLUMN langcode SET NOT NULL,
  ALTER COLUMN correlation_id SET DEFAULT gen_random_uuid(),
  ALTER COLUMN correlation_id SET NOT NULL;

ALTER TABLE run_log
  ADD COLUMN public_id uuid,
  ADD COLUMN site_id uuid,
  ADD COLUMN profile_id uuid,
  ADD COLUMN policy_version text,
  ADD COLUMN external_content_id text,
  ADD COLUMN external_revision_id text,
  ADD COLUMN content_type text,
  ADD COLUMN langcode text,
  ADD COLUMN correlation_id uuid,
  ADD COLUMN writeback_status text,
  ADD COLUMN writeback_error text;

UPDATE run_log AS run SET
  public_id = COALESCE(run.public_id, gen_random_uuid()),
  site_id = COALESCE(run.site_id, job.site_id, '00000000-0000-4000-8000-000000000001'),
  profile_id = COALESCE(run.profile_id, job.profile_id, '00000000-0000-4000-8000-000000000002'),
  policy_version = COALESCE(run.policy_version, job.policy_version, 'cam-nang-vn-v1'),
  external_content_id = COALESCE(run.external_content_id, job.external_content_id, run.node_id),
  external_revision_id = COALESCE(run.external_revision_id, job.external_revision_id),
  content_type = COALESCE(run.content_type, job.content_type, 'cam_nang'),
  langcode = COALESCE(run.langcode, job.langcode, 'vi'),
  correlation_id = COALESCE(run.correlation_id, job.correlation_id, gen_random_uuid()),
  writeback_status = COALESCE(run.writeback_status, 'unknown')
FROM review_job AS job
WHERE run.job_id = job.id;

UPDATE run_log SET
  public_id = COALESCE(public_id, gen_random_uuid()),
  site_id = COALESCE(site_id, '00000000-0000-4000-8000-000000000001'),
  profile_id = COALESCE(profile_id, '00000000-0000-4000-8000-000000000002'),
  policy_version = COALESCE(policy_version, 'cam-nang-vn-v1'),
  external_content_id = COALESCE(external_content_id, node_id),
  content_type = COALESCE(content_type, 'cam_nang'),
  langcode = COALESCE(langcode, 'vi'),
  correlation_id = COALESCE(correlation_id, gen_random_uuid()),
  writeback_status = COALESCE(writeback_status, 'unknown');

ALTER TABLE run_log
  ALTER COLUMN public_id SET DEFAULT gen_random_uuid(),
  ALTER COLUMN public_id SET NOT NULL,
  ALTER COLUMN site_id SET NOT NULL,
  ALTER COLUMN profile_id SET NOT NULL,
  ALTER COLUMN policy_version SET NOT NULL,
  ALTER COLUMN external_content_id SET NOT NULL,
  ALTER COLUMN content_type SET NOT NULL,
  ALTER COLUMN langcode SET NOT NULL,
  ALTER COLUMN correlation_id SET DEFAULT gen_random_uuid(),
  ALTER COLUMN correlation_id SET NOT NULL,
  ALTER COLUMN writeback_status SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'review_job_site_fk'
                 AND conrelid = 'review_job'::regclass) THEN
    ALTER TABLE review_job ADD CONSTRAINT review_job_site_fk
      FOREIGN KEY (site_id) REFERENCES site(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'review_job_profile_fk'
                 AND conrelid = 'review_job'::regclass) THEN
    ALTER TABLE review_job ADD CONSTRAINT review_job_profile_fk
      FOREIGN KEY (profile_id) REFERENCES review_profile(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'review_job_supersedes_fk'
                 AND conrelid = 'review_job'::regclass) THEN
    ALTER TABLE review_job ADD CONSTRAINT review_job_supersedes_fk
      FOREIGN KEY (supersedes_job_id) REFERENCES review_job(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'run_log_site_fk'
                 AND conrelid = 'run_log'::regclass) THEN
    ALTER TABLE run_log ADD CONSTRAINT run_log_site_fk
      FOREIGN KEY (site_id) REFERENCES site(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'run_log_profile_fk'
                 AND conrelid = 'run_log'::regclass) THEN
    ALTER TABLE run_log ADD CONSTRAINT run_log_profile_fk
      FOREIGN KEY (profile_id) REFERENCES review_profile(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'run_log_writeback_status_check'
                 AND conrelid = 'run_log'::regclass) THEN
    ALTER TABLE run_log ADD CONSTRAINT run_log_writeback_status_check CHECK (
      writeback_status IN ('unknown', 'pending', 'succeeded', 'failed', 'superseded')
    );
  END IF;
END
$$;

DROP INDEX IF EXISTS review_job_dedup;

CREATE UNIQUE INDEX review_job_public_id_unique ON review_job (public_id);
CREATE UNIQUE INDEX run_log_public_id_unique ON run_log (public_id);
CREATE UNIQUE INDEX review_job_scoped_dedup
  ON review_job (site_id, external_content_id, content_hash, policy_version)
  WHERE status IN ('queued', 'running', 'done');
CREATE INDEX review_job_scoped_claim
  ON review_job (status, run_after, site_id);
CREATE INDEX run_log_scoped_lookup
  ON run_log (
    site_id, external_content_id, content_hash, policy_version, scored_at DESC
  );

CREATE FUNCTION guard_assignment_active_scope() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  target_content_type text;
  target_language_code text;
  target_status text;
BEGIN
  IF NOT NEW.active THEN
    RETURN NEW;
  END IF;

  PERFORM id FROM site WHERE id = NEW.site_id FOR UPDATE;
  SELECT content_type, language_code, status
  INTO target_content_type, target_language_code, target_status
  FROM review_profile
  WHERE id = NEW.profile_id;

  IF target_status = 'active' AND EXISTS (
    SELECT 1
    FROM site_profile_assignment AS assignment
    JOIN review_profile AS profile ON profile.id = assignment.profile_id
    WHERE assignment.site_id = NEW.site_id
      AND assignment.active
      AND assignment.profile_id <> NEW.profile_id
      AND profile.status = 'active'
      AND profile.content_type = target_content_type
      AND profile.language_code = target_language_code
  ) THEN
    RAISE EXCEPTION 'active profile trung scope site/content_type/language_code'
      USING ERRCODE = '23505';
  END IF;
  RETURN NEW;
END
$$;

CREATE CONSTRAINT TRIGGER site_profile_assignment_scope_guard
AFTER INSERT OR UPDATE ON site_profile_assignment
DEFERRABLE INITIALLY IMMEDIATE
FOR EACH ROW EXECUTE FUNCTION guard_assignment_active_scope();

CREATE FUNCTION guard_profile_active_scope() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  assigned_site_id uuid;
BEGIN
  IF NEW.status <> 'active' THEN
    RETURN NEW;
  END IF;

  FOR assigned_site_id IN
    SELECT assignment.site_id
    FROM site_profile_assignment AS assignment
    WHERE assignment.profile_id = NEW.id AND assignment.active
  LOOP
    PERFORM id FROM site WHERE id = assigned_site_id FOR UPDATE;
    IF EXISTS (
      SELECT 1
      FROM site_profile_assignment AS assignment
      JOIN review_profile AS profile ON profile.id = assignment.profile_id
      WHERE assignment.site_id = assigned_site_id
        AND assignment.active
        AND assignment.profile_id <> NEW.id
        AND profile.status = 'active'
        AND profile.content_type = NEW.content_type
        AND profile.language_code = NEW.language_code
    ) THEN
      RAISE EXCEPTION 'active profile trung scope site/content_type/language_code'
        USING ERRCODE = '23505';
    END IF;
  END LOOP;
  RETURN NEW;
END
$$;

CREATE CONSTRAINT TRIGGER review_profile_scope_guard
AFTER UPDATE OF content_type, language_code, status ON review_profile
DEFERRABLE INITIALLY IMMEDIATE
FOR EACH ROW EXECUTE FUNCTION guard_profile_active_scope();
