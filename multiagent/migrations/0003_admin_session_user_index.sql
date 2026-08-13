-- Tang toc revoke tat ca session dang hoat dong cua mot admin user.
CREATE INDEX admin_session_user_idx
    ON admin_session (user_id)
    WHERE revoked_at IS NULL;
