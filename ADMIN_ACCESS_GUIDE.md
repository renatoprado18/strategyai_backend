# Admin Access Management Guide

Complete guide for granting and managing admin access to users.

---

## 📋 Overview

The system uses a two-tier authentication model:

1. **Supabase Auth** - Handles user authentication (email/password)
2. **`admin_users` Table** - Tracks which authenticated users have admin privileges

**User Flow:**
1. User signs up at `/admin/signup` → Account created in Supabase Auth
2. Admin manually grants access → User added to `admin_users` table
3. User can now login at `/admin/login` → Access granted to admin dashboard

---

## 🚀 Initial Setup

### Step 1: Run the Migration

Run the admin_users migration SQL in your Supabase SQL Editor:

1. Go to your Supabase project dashboard
2. Click **SQL Editor** in the left sidebar
3. Click **New Query**
4. Copy and paste the contents of `migrations/002_admin_users.sql`
5. Click **Run** (or press Ctrl+Enter)

✅ This creates:
- `admin_users` table
- Helper functions (`grant_admin_access`, `revoke_admin_access`, `is_admin`)
- Row Level Security policies
- Indexes for performance

---

## 👥 Granting Admin Access

### Method 1: Using SQL Function (Recommended)

**Step 1: Get the User ID**

1. Go to Supabase → **Authentication** → **Users**
2. Find the user you want to grant access to
3. Copy their **User UID** (UUID format)
4. Copy their **Email**

**Step 2: Grant Access via SQL**

1. Go to **SQL Editor** → **New Query**
2. Run this SQL:

```sql
SELECT grant_admin_access(
    target_user_id := 'paste-user-uuid-here',
    target_email := 'user@example.com',
    admin_notes := 'Initial admin setup'
);
```

**Example:**
```sql
SELECT grant_admin_access(
    target_user_id := '550e8400-e29b-41d4-a716-446655440000',
    target_email := 'admin@strategyai.com',
    admin_notes := 'Company founder - full admin access'
);
```

✅ **Success!** The user can now login and access the admin dashboard.

---

### Method 2: Direct Table Insert

If you prefer, you can insert directly into the table:

```sql
INSERT INTO admin_users (user_id, email, is_active, notes)
VALUES (
    'paste-user-uuid-here',
    'user@example.com',
    true,
    'Reason for granting access'
);
```

---

## 🔍 Checking Admin Status

### View All Active Admins

```sql
SELECT
    au.email,
    au.granted_at,
    au.notes,
    au.is_active
FROM admin_users au
WHERE au.is_active = true
AND au.revoked_at IS NULL
ORDER BY au.granted_at DESC;
```

### Check if Specific User is Admin

```sql
SELECT is_admin('user-uuid-here');
```

Returns `true` if admin, `false` if not.

---

## ❌ Revoking Admin Access

### Temporary Revocation (Can be re-enabled)

```sql
SELECT revoke_admin_access('user-uuid-here');
```

This sets:
- `is_active = false`
- `revoked_at = NOW()`

User will immediately lose admin access but the record remains for audit purposes.

### Permanent Deletion (Not Recommended)

```sql
DELETE FROM admin_users WHERE user_id = 'user-uuid-here';
```

⚠️ **Warning:** This permanently removes the record. Better to use `revoke_admin_access()` instead.

---

## 🔄 Re-enabling Revoked Access

If you previously revoked access and want to re-enable it:

```sql
SELECT grant_admin_access(
    target_user_id := 'user-uuid-here',
    target_email := 'user@example.com',
    admin_notes := 'Access re-granted after review'
);
```

This will:
- Set `is_active = true`
- Set `revoked_at = NULL`
- Update `updated_at = NOW()`

---

## 🧪 Testing Admin Access

### 1. Create Test Account

1. Go to your frontend: `https://your-app.vercel.app/admin/signup`
2. Create account with email: `test@example.com`

### 2. Try Login (Should Fail)

1. Go to `/admin/login`
2. Login with test credentials
3. ❌ **Expected:** "Access denied. Your account does not have admin privileges."

### 3. Grant Admin Access

Run in Supabase SQL Editor:

```sql
SELECT grant_admin_access(
    target_user_id := 'copy-user-uuid-from-auth-users',
    target_email := 'test@example.com',
    admin_notes := 'Test admin account'
);
```

### 4. Try Login Again (Should Succeed)

1. Go to `/admin/login`
2. Login with same credentials
3. ✅ **Expected:** Successfully redirected to admin dashboard

---

## 📊 Admin Users Table Schema

```sql
CREATE TABLE admin_users (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE,          -- Links to auth.users(id)
    email TEXT NOT NULL,                   -- User's email (for easy reference)
    granted_by UUID,                       -- Who granted access (optional)
    granted_at TIMESTAMPTZ DEFAULT NOW(),  -- When access was granted
    revoked_at TIMESTAMPTZ,                -- When access was revoked (NULL if active)
    is_active BOOLEAN DEFAULT true,        -- Is admin access currently active?
    notes TEXT,                            -- Why was access granted?
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 🔐 Security Notes

### Row Level Security (RLS)

The `admin_users` table has RLS enabled with these policies:

1. **SELECT**: Only authenticated users can view the table
2. **INSERT/UPDATE/DELETE**: Only service role can modify

This means:
- Regular users cannot see who is an admin
- Only Supabase service role (your backend) can modify admin access
- You must use SQL Editor or backend code to grant access

### Authentication Flow

```
User Signup
    ↓
Supabase Auth (email/password stored)
    ↓
Admin manually adds to admin_users table
    ↓
User Login
    ↓
Backend checks:
    1. Valid email/password? (Supabase Auth)
    2. User in admin_users table? (admin_users.is_active = true)
    ↓
If both pass → JWT token issued → Access granted
```

---

## 🆘 Troubleshooting

### User Can't Login After Being Granted Access

**Check 1: Verify user exists in admin_users**
```sql
SELECT * FROM admin_users WHERE email = 'user@example.com';
```

**Check 2: Verify is_active = true**
```sql
SELECT is_admin('user-uuid-here');
```

**Check 3: Check backend logs**
Look for errors in Railway logs when user tries to login.

### "Access Denied" Error Message

This is expected if:
- User signed up but admin access not yet granted
- User access was revoked
- User is not in `admin_users` table

**Solution:** Grant access using `grant_admin_access()` function.

### Backend Returns 403 Forbidden

This means:
- User authenticated successfully (valid email/password)
- But not found in `admin_users` table with `is_active = true`

**Solution:** Run the grant access SQL.

---

## 📝 Best Practices

### 1. Always Add Notes

When granting access, document why:

```sql
SELECT grant_admin_access(
    target_user_id := '...',
    target_email := 'newadmin@company.com',
    admin_notes := 'New marketing team lead - needs access to submissions dashboard'
);
```

### 2. Audit Admin Access Regularly

Run this monthly:

```sql
SELECT
    email,
    granted_at,
    notes,
    EXTRACT(DAY FROM NOW() - granted_at) as days_since_granted
FROM admin_users
WHERE is_active = true
ORDER BY granted_at DESC;
```

### 3. Revoke Instead of Delete

Keep audit trail:

```sql
-- ✅ Good
SELECT revoke_admin_access('user-id');

-- ❌ Bad (loses audit trail)
DELETE FROM admin_users WHERE user_id = 'user-id';
```

### 4. Use granted_by Field

Track who granted access:

```sql
INSERT INTO admin_users (user_id, email, granted_by, notes)
VALUES (
    'new-user-id',
    'newuser@example.com',
    'your-admin-user-id',
    'Granted by John Doe - approved by management'
);
```

---

## 🎯 Quick Reference

### Grant Access (Most Common)
```sql
SELECT grant_admin_access(
    target_user_id := 'USER_UUID',
    target_email := 'user@email.com',
    admin_notes := 'Reason here'
);
```

### Check If User Is Admin
```sql
SELECT is_admin('USER_UUID');
```

### List All Admins
```sql
SELECT email, granted_at, notes
FROM admin_users
WHERE is_active = true;
```

### Revoke Access
```sql
SELECT revoke_admin_access('USER_UUID');
```

---

## 📞 Support

If you need help:
1. Check Railway backend logs for errors
2. Verify migration ran successfully in Supabase
3. Ensure user exists in both `auth.users` and `admin_users` tables

---

**Last Updated:** January 2025
**Version:** 1.0
