CREATE TABLE admin_user (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  username text NOT NULL,
  username_normalized text NOT NULL UNIQUE,
  password_hash text NOT NULL,
  role text NOT NULL CONSTRAINT admin_user_role_check
    CHECK (role IN ('viewer', 'operator', 'admin')),
  active boolean NOT NULL DEFAULT true,
  must_change_password boolean NOT NULL DEFAULT true,
  password_changed_at timestamptz NOT NULL DEFAULT now(),
  last_login_at timestamptz,
  created_by uuid REFERENCES admin_user(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE admin_session (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES admin_user(id),
  token_hash char(64) NOT NULL UNIQUE,
  csrf_secret text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  idle_expires_at timestamptz NOT NULL,
  absolute_expires_at timestamptz NOT NULL,
  revoked_at timestamptz,
  revoke_reason text,
  CONSTRAINT admin_session_expiry_check CHECK (
    idle_expires_at <= absolute_expires_at
    AND created_at <= absolute_expires_at
  ),
  CONSTRAINT admin_session_revocation_check CHECK (
    (revoked_at IS NULL AND revoke_reason IS NULL)
    OR (revoked_at IS NOT NULL AND revoke_reason IS NOT NULL)
  )
);

CREATE INDEX admin_session_active_token_idx
  ON admin_session (token_hash)
  WHERE revoked_at IS NULL;

CREATE TABLE admin_login_throttle (
  subject_hash char(64) PRIMARY KEY,
  failure_count integer NOT NULL DEFAULT 0
    CONSTRAINT admin_login_throttle_failure_count_check CHECK (failure_count >= 0),
  window_started_at timestamptz NOT NULL DEFAULT now(),
  blocked_until timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE admin_audit_log (
  id bigserial PRIMARY KEY,
  actor_user_id uuid REFERENCES admin_user(id),
  actor_username text NOT NULL,
  action text NOT NULL,
  target_type text NOT NULL,
  target_id text,
  outcome text NOT NULL CONSTRAINT admin_audit_log_outcome_check
    CHECK (outcome IN ('success', 'denied', 'failed')),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX admin_audit_log_created_at_idx
  ON admin_audit_log (created_at DESC);

CREATE INDEX admin_audit_log_actor_created_at_idx
  ON admin_audit_log (actor_user_id, created_at DESC);
