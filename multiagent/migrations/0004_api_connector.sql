-- Plan 4: credential theo site cho /api/v1, phien ban hash noi dung va
-- trang thai health cua connector.
--
-- Khong rewrite hash lich su: moi row job/run da ton tai giu version 1 vi
-- chung duoc bam bang text_utils.content_hash() bon field. Chi job moi do
-- Drupal gui sau cutover moi mang version 2 (sau field).

CREATE TABLE site_api_credential (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id uuid NOT NULL REFERENCES site(id),
  token_prefix text NOT NULL,
  token_hash char(64) NOT NULL UNIQUE,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_used_at timestamptz,
  revoked_at timestamptz
);

-- Tra cuu luc xac thuc chi quet credential con hieu luc. Prefix khong phai
-- bi mat: no chi thu hep danh sach ung vien truoc khi so hash constant-time.
CREATE INDEX site_api_credential_prefix
  ON site_api_credential (token_prefix) WHERE active = true;

ALTER TABLE review_job
  ADD COLUMN content_hash_version smallint NOT NULL DEFAULT 1;

ALTER TABLE run_log
  ADD COLUMN content_hash_version smallint NOT NULL DEFAULT 1,
  ADD COLUMN source_url text,
  ADD COLUMN is_fixture boolean NOT NULL DEFAULT false;

ALTER TABLE review_job
  ADD CONSTRAINT review_job_content_hash_version_check
  CHECK (content_hash_version IN (1, 2));

ALTER TABLE run_log
  ADD CONSTRAINT run_log_content_hash_version_check
  CHECK (content_hash_version IN (1, 2));

-- Health cua connector do Task 8 ghi. De NULL nghia la chua bao gio kiem,
-- khac han voi 'ok'; dashboard phai hien unknown chu khong doan.
ALTER TABLE site
  ADD COLUMN last_health_status text,
  ADD COLUMN last_health_checked_at timestamptz,
  ADD COLUMN last_health_error text;
