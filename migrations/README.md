# Database Migrations

This folder contains SQL migration scripts for the Supabase database.

## How to Apply Migrations

### Using Supabase Dashboard (Recommended)

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor** in the left sidebar
3. Copy the contents of the migration file
4. Paste into the SQL editor
5. Click **Run** to execute

### Using Supabase CLI

```bash
# If you have Supabase CLI installed
supabase db push --db-url "your-supabase-connection-string"
```

## Migration History

| File | Date | Description |
|------|------|-------------|
| `001_add_status_workflow_and_confidence.sql` | 2025-01-27 | Adds status workflow stages (pending/processing/completed/ready_to_send/sent/failed), confidence scoring columns, and chat history |

## Verification After Migration

Run these queries in Supabase SQL Editor to verify migration success:

### Check New Columns

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'submissions'
  AND column_name IN ('confidence_score', 'confidence_breakdown', 'chat_history');
```

Expected result: 3 rows showing the new columns.

### Check Status Constraint

```sql
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conname = 'submissions_status_check';
```

Expected result: Constraint with 6 status values (pending, processing, completed, ready_to_send, sent, failed).

### Check Indexes

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'submissions'
  AND indexname LIKE '%confidence%';
```

Expected result: 2 indexes on confidence_score.

## Rollback Instructions

If you need to roll back a migration, each migration file includes a rollback section at the bottom. Copy and run the commented-out rollback SQL commands.

## Notes

- Always backup your database before running migrations
- Test migrations on a staging environment first
- Migrations are designed to be idempotent (safe to run multiple times)
- Each migration uses `IF NOT EXISTS` and `IF EXISTS` to prevent errors on re-runs
