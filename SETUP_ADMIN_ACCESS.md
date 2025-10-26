# Admin Access Setup Guide

Quick guide to grant admin access so you and your dad can login to the admin dashboard.

---

## 🎯 Goal

Allow you and your dad to:
1. Login at `/admin/login`
2. View all submissions in the admin dashboard
3. See AI-generated reports
4. Copy reports to manually email to clients

---

## 📝 Prerequisites

- ✅ Both migrations ran in Supabase (`submissions` + `admin_users` tables exist)
- ✅ You or your dad have created accounts via `/admin/signup`
- ✅ You have access to Supabase SQL Editor

---

## 🚀 Step-by-Step

### Step 1: Create Account (If Not Done Yet)

1. Go to: `https://strategyai-landing.vercel.app/admin/signup`
2. Enter your email and password (minimum 6 characters)
3. Click "Criar Conta"
4. You'll see: "Conta criada com sucesso!"
5. You'll be redirected to login page

**Repeat for your dad's email**

---

### Step 2: Get User IDs from Supabase

1. Go to: https://clltdyxxkzblznwzsxbn.supabase.co
2. Click **Authentication** in left sidebar
3. Click **Users** tab
4. You'll see a list of all users who signed up

**For each person who needs admin access:**
- Find their email in the list
- Copy their **User UID** (looks like: `550e8400-e29b-41d4-a716-446655440000`)
- Keep this UUID handy for next step

---

### Step 3: Grant Admin Access

1. In Supabase, click **SQL Editor** in left sidebar
2. Click **New Query**
3. For each person, run this query (replace the placeholders):

```sql
SELECT grant_admin_access(
    target_user_id := 'PASTE-USER-UUID-HERE',
    target_email := 'user@email.com',
    admin_notes := 'Company owner - full admin access'
);
```

**Example for you:**
```sql
SELECT grant_admin_access(
    target_user_id := '123e4567-e89b-12d3-a456-426614174000',
    target_email := 'renato@strategyai.com',
    admin_notes := 'Son - technical admin'
);
```

**Example for your dad:**
```sql
SELECT grant_admin_access(
    target_user_id := '987e6543-e21b-34c5-b654-321321321000',
    target_email := 'dad@strategyai.com',
    admin_notes := 'Father - business owner'
);
```

4. Click **Run** (or press Ctrl+Enter)
5. You should see: `true` (means success!)

---

### Step 4: Verify Admin Access Was Granted

Run this query in SQL Editor:

```sql
SELECT
    email,
    is_active,
    granted_at,
    notes
FROM admin_users
WHERE is_active = true
ORDER BY granted_at DESC;
```

**Expected result:**
```
email                | is_active | granted_at           | notes
---------------------|-----------|----------------------|------------------------
dad@strategyai.com   | true      | 2025-01-26 10:15:30 | Father - business owner
renato@strategyai.com| true      | 2025-01-26 10:14:22 | Son - technical admin
```

✅ If you see both emails → Admin access granted successfully!

---

### Step 5: Test Login

1. Go to: `https://strategyai-landing.vercel.app/admin/login`
2. Enter your email and password
3. Click "Entrar"

**Expected:**
- ✅ Redirected to: `/admin/dashboard-x9k2p`
- ✅ See your email in header
- ✅ See "Logout" button
- ✅ See list of all submissions
- ✅ Can click on submissions to view full AI reports

**If you see "Access denied":**
- Check if admin access was granted (run Step 4 query again)
- Verify you're using the correct email/password
- Check Railway logs for authentication errors

---

## 👨‍💼 For Your Dad

Once admin access is granted, show your dad:

### How to Login
1. Go to: `https://strategyai-landing.vercel.app/admin/login`
2. Enter email: `his@email.com`
3. Enter password: (the one he created)
4. Click "Entrar"

### How to View Submissions
1. After login, he'll see the dashboard automatically
2. List shows all submissions with:
   - Company name
   - Contact name
   - Email
   - Industry
   - Status (pending/completed/failed)
   - Submission date

### How to View AI Reports
1. Click on any submission in the list
2. Full AI-generated report opens
3. Report includes:
   - Executive Summary (Sumário Executivo)
   - SWOT Analysis (Análise SWOT)
   - Strategic Opportunities (Oportunidades Estratégicas)
   - Action Recommendations (Recomendações de Ação)

### How to Email Reports to Clients
1. Open the report for the client
2. Copy the entire report (Ctrl+A, Ctrl+C)
3. Paste into email
4. Add personal message
5. Send to client's email (shown in submission details)

---

## 🔐 Security Notes

### Password Requirements
- Minimum 6 characters
- No other restrictions (but recommend strong passwords)

### Adding More Admins Later

Anyone can signup at `/admin/signup`, but they won't have access until you grant it:

1. Have them signup first
2. You run the `grant_admin_access()` SQL in Supabase
3. Then they can login

### Revoking Admin Access

If you need to remove someone's admin access:

```sql
SELECT revoke_admin_access('user-uuid-here');
```

They can still login to Supabase Auth, but can't access the admin dashboard.

---

## 🆘 Troubleshooting

### "Invalid email or password"
- Double-check email spelling
- Reset password if forgotten (not implemented yet - contact support)

### "Access denied. Your account does not have admin privileges."
- Admin access not granted yet
- Run the `grant_admin_access()` SQL command
- Wait a few seconds, then try login again

### "No submissions showing in dashboard"
- Check if any submissions exist in database (run verification queries)
- Check if RLS policies are correct
- Verify backend is connected to Supabase

### Can't see some submissions
- All admins see ALL submissions (no filtering by user)
- If submission exists in database but not in dashboard, check browser console for errors

---

## ✅ Success Checklist

- [ ] You signed up at `/admin/signup`
- [ ] Your dad signed up at `/admin/signup`
- [ ] You ran `grant_admin_access()` for yourself
- [ ] You ran `grant_admin_access()` for your dad
- [ ] You verified admin_users table shows both emails
- [ ] You successfully logged in
- [ ] Your dad successfully logged in
- [ ] Dashboard shows list of submissions
- [ ] Can click and view full AI reports
- [ ] Reports display properly formatted in Portuguese

**Once all checked → Admin system is ready to use!**

---

## 📋 Quick Reference

### Grant admin access:
```sql
SELECT grant_admin_access(
    target_user_id := 'USER-UUID',
    target_email := 'user@email.com',
    admin_notes := 'Reason'
);
```

### Check who has admin access:
```sql
SELECT email, granted_at, notes
FROM admin_users
WHERE is_active = true;
```

### Revoke admin access:
```sql
SELECT revoke_admin_access('USER-UUID');
```

---

**Last Updated:** January 2025
