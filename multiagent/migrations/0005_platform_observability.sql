-- Plan 5: quan sat duoc worker va chi phi LLM.
--
-- Hai bang deu la BANG MOI, khong sua bang cu. Row job/run/KB/auth hien co
-- khong bi dong toi.

-- Worker song hay chet phai co NGUON THAT, khong duoc suy tu "API con song".
-- API va worker la hai tien trinh doc lap: worker chet vi het RAM thi API van
-- tra 200 va dashboard van xanh - dung cai bay ma bang nay sinh ra de chan.
CREATE TABLE worker_heartbeat (
  instance_id text PRIMARY KEY,
  started_at timestamptz NOT NULL,
  last_seen_at timestamptz NOT NULL,
  version text NOT NULL,
  current_job_id uuid REFERENCES review_job(public_id) ON DELETE SET NULL,
  CONSTRAINT worker_heartbeat_instance_len
    CHECK (char_length(instance_id) BETWEEN 1 AND 128),
  CONSTRAINT worker_heartbeat_version_len
    CHECK (char_length(version) BETWEEN 1 AND 128)
);

CREATE INDEX worker_heartbeat_last_seen_idx ON worker_heartbeat (last_seen_at);

-- Chi phi tung lan goi LLM, ghi BEN VUNG ngay khi co usage response.
--
-- KHONG co FK toi run_log, va do la co y: mot attempt co the tieu tien roi
-- agent nem loi TRUOC khi run_log ton tai. Bat FK se lam dung nhung lan do
-- khong ghi duoc - tuc chi phi that bien mat khoi so sach, con dashboard thi
-- bao it hon thuc te.
--
-- Khong co cot nao chua prompt/output/noi dung bai. Chi so dem va nhan.
CREATE TABLE llm_usage_event (
  id bigserial PRIMARY KEY,
  job_id bigint NOT NULL REFERENCES review_job(id),
  attempt smallint NOT NULL,
  sequence_no smallint NOT NULL,
  correlation_id uuid NOT NULL,
  agent text NOT NULL,
  phase text NOT NULL,
  model text NOT NULL,
  input_tokens integer NOT NULL CHECK (input_tokens >= 0),
  output_tokens integer NOT NULL CHECK (output_tokens >= 0),
  is_fixture boolean NOT NULL DEFAULT false,
  recorded_at timestamptz NOT NULL DEFAULT now(),
  -- Khoa idempotency: ghi lai cung mot lan goi la no-op, khong cong doi chi phi.
  UNIQUE (job_id, attempt, sequence_no)
);

CREATE INDEX llm_usage_event_recorded_at_idx ON llm_usage_event (recorded_at);
