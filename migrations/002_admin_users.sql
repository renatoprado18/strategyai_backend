-- Migration: Admin Users Table
-- Purpose: Track which users have admin access
-- Created: 2025-01-26

-- ============================================
-- Admin Users Table
-- ============================================

CREATE TABLE IF NOT EXISTS admin_users (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    granted_by UUID REFERENCES auth.users(id),
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Indexes
-- ============================================

CREATE INDEX idx_admin_users_user_id ON admin_users(user_id);
CREATE INDEX idx_admin_users_email ON admin_users(email);
CREATE INDEX idx_admin_users_is_active ON admin_users(is_active);

-- ============================================
-- Row Level Security (RLS)
-- ============================================

ALTER TABLE admin_users ENABLE ROW LEVEL SECURITY;

-- Only authenticated users can view admin_users table
CREATE POLICY "Authenticated users can view admin_users"
    ON admin_users
    FOR SELECT
    USING (auth.role() = 'authenticated');

-- Only service role can insert/update/delete
CREATE POLICY "Service role can manage admin_users"
    ON admin_users
    FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- ============================================
-- Updated At Trigger
-- ============================================

CREATE OR REPLACE FUNCTION update_admin_users_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_admin_users_updated_at
    BEFORE UPDATE ON admin_users
    FOR EACH ROW
    EXECUTE FUNCTION update_admin_users_updated_at();

-- ============================================
-- Helper Functions
-- ============================================

-- Function to check if a user is an active admin
CREATE OR REPLACE FUNCTION is_admin(check_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM admin_users
        WHERE user_id = check_user_id
        AND is_active = true
        AND revoked_at IS NULL
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to grant admin access
CREATE OR REPLACE FUNCTION grant_admin_access(
    target_user_id UUID,
    target_email TEXT,
    granting_user_id UUID DEFAULT NULL,
    admin_notes TEXT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
BEGIN
    INSERT INTO admin_users (user_id, email, granted_by, notes, is_active)
    VALUES (target_user_id, target_email, granting_user_id, admin_notes, true)
    ON CONFLICT (user_id) DO UPDATE
    SET is_active = true,
        revoked_at = NULL,
        updated_at = NOW();

    RETURN true;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to revoke admin access
CREATE OR REPLACE FUNCTION revoke_admin_access(target_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE admin_users
    SET is_active = false,
        revoked_at = NOW(),
        updated_at = NOW()
    WHERE user_id = target_user_id;

    RETURN true;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- Comments
-- ============================================

COMMENT ON TABLE admin_users IS 'Tracks users with administrative access to the system';
COMMENT ON COLUMN admin_users.user_id IS 'Reference to auth.users(id)';
COMMENT ON COLUMN admin_users.granted_by IS 'User ID of admin who granted access';
COMMENT ON COLUMN admin_users.revoked_at IS 'Timestamp when admin access was revoked';
COMMENT ON COLUMN admin_users.is_active IS 'Whether admin access is currently active';
COMMENT ON COLUMN admin_users.notes IS 'Optional notes about why admin access was granted';

-- ============================================
-- Example Usage (Comment out in production)
-- ============================================

/*
-- To grant admin access to a user after they sign up:
SELECT grant_admin_access(
    target_user_id := 'user-uuid-from-auth-users',
    target_email := 'user@example.com',
    admin_notes := 'Initial admin user'
);

-- To check if a user is an admin:
SELECT is_admin('user-uuid-from-auth-users');

-- To revoke admin access:
SELECT revoke_admin_access('user-uuid-from-auth-users');

-- To view all active admins:
SELECT * FROM admin_users WHERE is_active = true AND revoked_at IS NULL;
*/
