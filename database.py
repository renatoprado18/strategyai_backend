"""
Database module for Supabase connection and operations
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from supabase_client import supabase_service, supabase_anon

# Table name
TABLE_NAME = "submissions"


async def init_db():
    """
    Initialize the database with schema.
    Note: In Supabase, you should create the table manually via SQL editor or dashboard.

    SQL to run in Supabase SQL Editor:

    CREATE TABLE IF NOT EXISTS submissions (
        id BIGSERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        company TEXT NOT NULL,
        website TEXT,
        industry TEXT NOT NULL,
        challenge TEXT,
        status TEXT DEFAULT 'pending',
        report_json TEXT,
        error_message TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_status ON submissions(status);
    CREATE INDEX IF NOT EXISTS idx_created ON submissions(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_email ON submissions(email);

    -- Enable Row Level Security
    ALTER TABLE submissions ENABLE ROW LEVEL SECURITY;

    -- Policy: Anyone can insert (for public form submission)
    CREATE POLICY "Anyone can insert submissions"
        ON submissions FOR INSERT
        WITH CHECK (true);

    -- Policy: Only authenticated users can view all submissions
    CREATE POLICY "Authenticated users can view all submissions"
        ON submissions FOR SELECT
        USING (auth.role() = 'authenticated');

    -- Policy: Only authenticated users can update submissions
    CREATE POLICY "Authenticated users can update submissions"
        ON submissions FOR UPDATE
        USING (auth.role() = 'authenticated');
    """
    print("[INFO] Supabase database initialization")
    print("[INFO] Make sure you've created the submissions table in Supabase SQL Editor")
    print("[INFO] See database.py docstring for SQL schema")


# CRUD Operations

async def create_submission(
    name: str,
    email: str,
    company: str,
    website: Optional[str],
    linkedin_company: Optional[str],
    linkedin_founder: Optional[str],
    industry: str,
    challenge: Optional[str],
) -> int:
    """Create a new submission with LinkedIn fields for enhanced analysis"""
    try:
        data = {
            "name": name,
            "email": email,
            "company": company,
            "website": website,
            "linkedin_company": linkedin_company,
            "linkedin_founder": linkedin_founder,
            "industry": industry,
            "challenge": challenge,
            "status": "pending"
        }

        # Use service client to bypass RLS (backend handles authorization)
        response = supabase_service.table(TABLE_NAME).insert(data).execute()

        if response.data and len(response.data) > 0:
            return response.data[0]["id"]
        else:
            raise Exception("Failed to create submission")
    except Exception as e:
        print(f"[ERROR] Failed to create submission: {str(e)}")
        raise


async def get_submission(submission_id: int) -> Optional[Dict[str, Any]]:
    """Get a submission by ID"""
    try:
        # Use service client to bypass RLS
        response = supabase_service.table(TABLE_NAME).select("*").eq("id", submission_id).execute()

        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"[ERROR] Failed to get submission {submission_id}: {str(e)}")
        return None


async def get_all_submissions() -> List[Dict[str, Any]]:
    """Get all submissions ordered by created_at DESC"""
    try:
        # Use service client to bypass RLS
        response = supabase_service.table(TABLE_NAME).select("*").order("created_at", desc=True).execute()

        return response.data if response.data else []
    except Exception as e:
        print(f"[ERROR] Failed to get all submissions: {str(e)}")
        return []


async def update_submission_status(
    submission_id: int,
    status: str,
    report_json: Optional[str] = None,
    error_message: Optional[str] = None,
    data_quality_json: Optional[str] = None,
    processing_metadata: Optional[str] = None,
):
    """Update submission status, report, and quality metadata"""
    try:
        data = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }

        if report_json is not None:
            data["report_json"] = report_json

        if error_message is not None:
            data["error_message"] = error_message

        if data_quality_json is not None:
            data["data_quality_json"] = data_quality_json

        if processing_metadata is not None:
            data["processing_metadata"] = processing_metadata

        # Use service client to bypass RLS
        response = supabase_service.table(TABLE_NAME).update(data).eq("id", submission_id).execute()

        if not response.data:
            raise Exception(f"Failed to update submission {submission_id}")
    except Exception as e:
        print(f"[ERROR] Failed to update submission status: {str(e)}")
        raise


async def get_submissions_by_ip_today(ip_address: str) -> int:
    """
    Get count of submissions from an IP today.
    Note: This is now handled by Upstash Redis in rate_limiter.py
    This function is kept for backward compatibility but returns 0.
    """
    return 0


# Utility functions

async def count_submissions() -> int:
    """Count total submissions"""
    try:
        # Use service client
        response = supabase_service.table(TABLE_NAME).select("id", count="exact").execute()
        return response.count if hasattr(response, 'count') else 0
    except Exception as e:
        print(f"[ERROR] Failed to count submissions: {str(e)}")
        return 0


async def count_submissions_by_status(status: str) -> int:
    """Count submissions by status"""
    try:
        # Use service client
        response = supabase_service.table(TABLE_NAME).select("id", count="exact").eq("status", status).execute()
        return response.count if hasattr(response, 'count') else 0
    except Exception as e:
        print(f"[ERROR] Failed to count submissions by status: {str(e)}")
        return 0
