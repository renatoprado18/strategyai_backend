-- =====================================================
-- Strategy AI Backend - Supabase Database Schema
-- Version 2.0
-- =====================================================
-- Run this in Supabase SQL Editor
-- =====================================================

-- Create submissions table
CREATE TABLE IF NOT EXISTS submissions (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    company TEXT NOT NULL,
    website TEXT,
    industry TEXT NOT NULL,
    challenge TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed')),
    report_json TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status);
CREATE INDEX IF NOT EXISTS idx_submissions_created ON submissions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_submissions_email ON submissions(email);

-- Enable Row Level Security
ALTER TABLE submissions ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (for re-running this script)
DROP POLICY IF EXISTS "Anyone can insert submissions" ON submissions;
DROP POLICY IF EXISTS "Authenticated users can view all submissions" ON submissions;
DROP POLICY IF EXISTS "Authenticated users can update submissions" ON submissions;

-- Policy 1: Anyone can INSERT (for public form submission)
CREATE POLICY "Anyone can insert submissions"
    ON submissions
    FOR INSERT
    WITH CHECK (true);

-- Policy 2: Only authenticated users can SELECT all submissions
CREATE POLICY "Authenticated users can view all submissions"
    ON submissions
    FOR SELECT
    USING (auth.role() = 'authenticated');

-- Policy 3: Only authenticated users can UPDATE submissions
CREATE POLICY "Authenticated users can update submissions"
    ON submissions
    FOR UPDATE
    USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated');

-- Policy 4: Only authenticated users can DELETE submissions (optional)
CREATE POLICY "Authenticated users can delete submissions"
    ON submissions
    FOR DELETE
    USING (auth.role() = 'authenticated');

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at
DROP TRIGGER IF EXISTS update_submissions_updated_at ON submissions;
CREATE TRIGGER update_submissions_updated_at
    BEFORE UPDATE ON submissions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- Verification Queries (optional - run these to verify)
-- =====================================================

-- Check table structure
-- SELECT column_name, data_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_name = 'submissions'
-- ORDER BY ordinal_position;

-- Check indexes
-- SELECT indexname, indexdef
-- FROM pg_indexes
-- WHERE tablename = 'submissions';

-- Check RLS policies
-- SELECT policyname, permissive, roles, cmd, qual, with_check
-- FROM pg_policies
-- WHERE tablename = 'submissions';

-- =====================================================
-- Success Message
-- =====================================================
-- If you see no errors above, your database is ready!
--
-- Next steps:
-- 1. Create an admin user in Supabase Auth panel
-- 2. Update your .env file with Supabase credentials
-- 3. Deploy your backend to Railway
-- =====================================================
