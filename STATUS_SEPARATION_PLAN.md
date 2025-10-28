# Status Field Separation Plan

**Problem:** The current `status` field mixes backend processing state with user-facing action state, causing confusion.

**Solution:** Separate into two distinct fields:
1. `processing_state` - Backend system progress (internal)
2. `user_status` - What the user can do (external/UI)

---

## Current Problems

### Issue 1: Confusing Mix of Concerns

Current `status` values:
- `'pending'` - Is this "waiting to process" or "user needs to review"?
- `'processing'` - Backend state
- `'completed'` - Backend state
- `'ready_to_send'` - User action
- `'sent'` - User action
- `'failed'` - Backend state

**Problem:** Frontend doesn't know if status = "pending" means "AI is thinking" or "user needs to act"

### Issue 2: Progress Tracking Confusion

Progress stages (emit_progress):
- `"initializing"`, `"data_gathering"`, `"deep_research"`, `"ai_analysis"`, `"finalizing"`, `"completed"`, `"failed"`

These are DIFFERENT from status but serve similar purpose → confusing!

### Issue 3: Frontend UI Logic is Complex

Frontend must decode:
```javascript
if (status === 'completed') {
  // Show "View Report" button
} else if (status === 'processing') {
  // Show loading spinner
} else if (status === 'ready_to_send') {
  // Show "Send to Client" button
}
```

**Problem:** Frontend needs to know internal backend states to make UI decisions

---

## Proposed Solution

### New Schema Design

```sql
-- BACKEND PROCESSING STATE (internal, system-managed)
processing_state TEXT CHECK (processing_state IN (
    'queued',          -- Waiting in queue
    'data_gathering',  -- Collecting external data
    'ai_analyzing',    -- Running AI analysis
    'finalizing',      -- Saving to database
    'completed',       -- Successfully finished
    'failed'           -- Error occurred
));

-- USER-FACING STATUS (external, what user can do)
user_status TEXT CHECK (user_status IN (
    'draft',           -- User still editing form
    'submitted',       -- User submitted, waiting for analysis
    'analyzing',       -- Analysis in progress (maps to multiple processing_states)
    'ready',           -- Analysis done, ready for user review
    'reviewed',        -- User has reviewed the report
    'sent_to_client',  -- User sent report to their client
    'archived'         -- User archived this submission
));
```

### Mapping Between States

| processing_state | user_status | Frontend Shows |
|-----------------|-------------|----------------|
| `queued` | `submitted` | "Analysis queued..." |
| `data_gathering` | `analyzing` | "Collecting market data..." |
| `ai_analyzing` | `analyzing` | "AI generating analysis..." |
| `finalizing` | `analyzing` | "Finalizing report..." |
| `completed` | `ready` | "✅ Report Ready - View Now" |
| `failed` | `submitted` | "❌ Analysis Failed - Try Again" |
| (any) | `sent_to_client` | "✅ Sent to Client on [date]" |
| (any) | `archived` | "Archived" |

---

## Implementation Plan

### Phase 1: Database Migration

**File:** `migrations/007_separate_status_fields.sql`

```sql
-- Add new columns
ALTER TABLE submissions
ADD COLUMN IF NOT EXISTS processing_state TEXT DEFAULT 'queued';

ALTER TABLE submissions
ADD COLUMN IF NOT EXISTS user_status TEXT DEFAULT 'submitted';

-- Migrate existing data
UPDATE submissions
SET
    processing_state = CASE
        WHEN status = 'pending' THEN 'queued'
        WHEN status = 'processing' THEN 'ai_analyzing'
        WHEN status = 'completed' THEN 'completed'
        WHEN status = 'failed' THEN 'failed'
        WHEN status = 'ready_to_send' THEN 'completed'
        WHEN status = 'sent' THEN 'completed'
        ELSE 'queued'
    END,
    user_status = CASE
        WHEN status = 'pending' THEN 'submitted'
        WHEN status = 'processing' THEN 'analyzing'
        WHEN status = 'completed' THEN 'ready'
        WHEN status = 'failed' THEN 'submitted'
        WHEN status = 'ready_to_send' THEN 'ready'
        WHEN status = 'sent' THEN 'sent_to_client'
        ELSE 'submitted'
    END;

-- Add constraints
ALTER TABLE submissions
ADD CONSTRAINT submissions_processing_state_check CHECK (
    processing_state IN ('queued', 'data_gathering', 'ai_analyzing', 'finalizing', 'completed', 'failed')
);

ALTER TABLE submissions
ADD CONSTRAINT submissions_user_status_check CHECK (
    user_status IN ('draft', 'submitted', 'analyzing', 'ready', 'reviewed', 'sent_to_client', 'archived')
);

-- Keep old status column for backward compatibility (mark as deprecated)
COMMENT ON COLUMN submissions.status IS 'DEPRECATED: Use processing_state and user_status instead';

-- Add indexes
CREATE INDEX idx_submissions_processing_state ON submissions(processing_state);
CREATE INDEX idx_submissions_user_status ON submissions(user_status);
CREATE INDEX idx_submissions_user_status_updated ON submissions(user_status, updated_at DESC);
```

### Phase 2: Backend Updates

**File:** `app/core/database.py`

Add new function:
```python
async def update_submission_processing_state(
    submission_id: int,
    processing_state: str,
    user_status: Optional[str] = None,  # Auto-compute if not provided
    **kwargs
):
    """
    Update submission with separate processing and user states

    Args:
        processing_state: Backend state (queued, data_gathering, ai_analyzing, finalizing, completed, failed)
        user_status: User-facing state (submitted, analyzing, ready, etc.) - auto-computed if None
    """
    # Auto-compute user_status from processing_state if not provided
    if user_status is None:
        user_status_map = {
            'queued': 'submitted',
            'data_gathering': 'analyzing',
            'ai_analyzing': 'analyzing',
            'finalizing': 'analyzing',
            'completed': 'ready',
            'failed': 'submitted',  # Allow retry
        }
        user_status = user_status_map.get(processing_state, 'submitted')

    # Update both states
    # ... (implementation)
```

**File:** `app/utils/background_tasks.py`

Update progress tracking:
```python
# OLD
emit_progress(submission_id, "data_gathering", "Collecting data...", 10)
await update_submission_status(submission_id, status="processing")

# NEW
emit_progress(submission_id, "data_gathering", "Collecting data...", 10)
await update_submission_processing_state(
    submission_id,
    processing_state="data_gathering",
    # user_status auto-computed as "analyzing"
)
```

Update completion:
```python
# OLD
await update_submission_status(submission_id, status="completed", report_json=...)

# NEW
await update_submission_processing_state(
    submission_id,
    processing_state="completed",
    user_status="ready",  # Explicitly set: user can now view
    report_json=...
)
```

### Phase 3: Frontend Updates

**Current Frontend (Assumed):**
```typescript
// OLD - Frontend decodes backend internal states
function getStatusDisplay(status: string) {
  switch(status) {
    case 'pending': return 'Waiting...';
    case 'processing': return 'Analyzing...';
    case 'completed': return 'Ready to View';
    case 'failed': return 'Failed';
    case 'ready_to_send': return 'Ready to Send';
    case 'sent': return 'Sent';
  }
}
```

**New Frontend:**
```typescript
// NEW - Frontend uses user_status (designed for UI)
function getStatusDisplay(user_status: string) {
  const statusConfig = {
    'draft': { label: 'Draft', color: 'gray', action: 'Continue Editing' },
    'submitted': { label: 'Submitted', color: 'blue', action: 'View Progress' },
    'analyzing': { label: 'Analyzing...', color: 'yellow', action: 'View Progress' },
    'ready': { label: 'Ready', color: 'green', action: 'View Report' },
    'reviewed': { label: 'Reviewed', color: 'green', action: 'View Report' },
    'sent_to_client': { label: 'Sent', color: 'purple', action: 'View Report' },
    'archived': { label: 'Archived', color: 'gray', action: 'Restore' },
  };
  return statusConfig[user_status];
}
```

**API Response Changes:**
```json
{
  "id": 123,
  "company": "Example Corp",

  // DEPRECATED (keep for backward compatibility)
  "status": "completed",

  // NEW - Separate concerns
  "processing_state": "completed",  // Backend knows AI finished
  "user_status": "ready",           // Frontend knows user can view

  // Progress tracking (separate from status!)
  "current_progress": {
    "stage": "completed",
    "message": "Analysis complete!",
    "progress": 100
  }
}
```

### Phase 4: User Action Tracking

Add new endpoints for user status transitions:

```python
@router.post("/api/admin/submissions/{submission_id}/mark-reviewed")
async def mark_submission_reviewed(submission_id: int):
    """User has reviewed the report - update user_status"""
    await update_submission_processing_state(
        submission_id,
        processing_state=None,  # Don't change backend state
        user_status="reviewed"
    )

@router.post("/api/admin/submissions/{submission_id}/send-to-client")
async def send_to_client(submission_id: int, request: Request):
    """User sent report to their client"""
    body = await request.json()
    client_email = body.get("client_email")

    # Send email (implementation)

    # Update user status
    await update_submission_processing_state(
        submission_id,
        processing_state=None,
        user_status="sent_to_client",
        sent_to_client_at=datetime.now(timezone.utc).isoformat(),
        sent_to_client_email=client_email
    )

@router.post("/api/admin/submissions/{submission_id}/archive")
async def archive_submission(submission_id: int):
    """User archived this submission"""
    await update_submission_processing_state(
        submission_id,
        processing_state=None,
        user_status="archived"
    )
```

---

## Benefits of This Separation

### 1. Clear Responsibilities

**Backend (processing_state):**
- Managed by system/background tasks
- Tracks: "Where is the analysis pipeline right now?"
- Values reflect actual backend stages
- Changes automatically during processing

**Frontend (user_status):**
- Managed by user actions + system
- Tracks: "What can the user do with this submission?"
- Values designed for UI decisions
- Changes on user actions (review, send, archive)

### 2. Simpler Frontend Logic

**Before:**
```typescript
// Frontend must know backend implementation details
if (status === 'processing' || status === 'pending') {
  showSpinner();
} else if (status === 'completed' || status === 'ready_to_send') {
  showViewButton();
}
```

**After:**
```typescript
// Frontend uses UI-designed states
if (user_status === 'analyzing') {
  showSpinner();
} else if (user_status === 'ready') {
  showViewButton();
}
```

### 3. Better Progress Tracking

```typescript
// Show detailed progress while analyzing
if (user_status === 'analyzing') {
  showProgressBar(current_progress.progress);
  showStageMessage(current_progress.message);
}
```

### 4. Enable User Workflows

```typescript
// User can now track their OWN workflow
if (user_status === 'ready') {
  showActions(['View Report', 'Mark as Reviewed', 'Send to Client']);
} else if (user_status === 'reviewed') {
  showActions(['View Report', 'Send to Client', 'Archive']);
} else if (user_status === 'sent_to_client') {
  showActions(['View Report', 'Archive']);
  showSentInfo(sent_to_client_email, sent_to_client_at);
}
```

### 5. Better Analytics

```sql
-- How many analyses are currently running?
SELECT COUNT(*) FROM submissions WHERE processing_state IN ('data_gathering', 'ai_analyzing');

-- How many reports are waiting for user review?
SELECT COUNT(*) FROM submissions WHERE user_status = 'ready';

-- How many reports were sent to clients?
SELECT COUNT(*) FROM submissions WHERE user_status = 'sent_to_client';

-- Average time from submission to user review
SELECT AVG(updated_at - created_at)
FROM submissions
WHERE user_status = 'reviewed';
```

---

## Migration Strategy (Zero Downtime)

### Step 1: Add New Fields (Non-Breaking)
- Add `processing_state` and `user_status` columns
- Keep `status` column
- Migrate existing data

### Step 2: Update Backend (Dual-Write)
- Backend writes to BOTH `status` and new fields
- APIs return BOTH for compatibility

### Step 3: Update Frontend (Gradual)
- Frontend reads new fields but falls back to old `status`
- Deploy frontend changes

### Step 4: Remove Old Field (After Validation)
- Stop using `status` in backend
- Deprecate in API responses
- Eventually remove column (months later)

---

## Success Criteria

✅ Backend knows: "Is the AI currently processing?"
✅ Frontend knows: "What buttons should I show the user?"
✅ User knows: "What can I do with this report?"
✅ Analytics knows: "How many reports are awaiting user action?"
✅ No breaking changes to existing frontend

---

## Example User Journey

1. **User submits form**
   - `processing_state`: `queued`
   - `user_status`: `submitted`
   - UI shows: "Analysis queued..."

2. **Backend starts data gathering**
   - `processing_state`: `data_gathering`
   - `user_status`: `analyzing`
   - UI shows: "Collecting market data... 10%"

3. **Backend runs AI analysis**
   - `processing_state`: `ai_analyzing`
   - `user_status`: `analyzing`
   - UI shows: "AI generating analysis... 50%"

4. **Backend completes**
   - `processing_state`: `completed`
   - `user_status`: `ready`
   - UI shows: "✅ Report Ready - View Now"

5. **User views report**
   - `processing_state`: `completed` (unchanged)
   - `user_status`: `ready` (unchanged)
   - UI shows: "View Report" button

6. **User marks as reviewed**
   - `processing_state`: `completed` (unchanged)
   - `user_status`: `reviewed`
   - UI shows: "Reviewed" badge + "Send to Client" button

7. **User sends to client**
   - `processing_state`: `completed` (unchanged)
   - `user_status`: `sent_to_client`
   - `sent_to_client_at`: `"2025-10-28T..."`
   - `sent_to_client_email`: `"client@example.com"`
   - UI shows: "✅ Sent to client@example.com on Oct 28"

8. **User archives**
   - `processing_state`: `completed` (unchanged)
   - `user_status`: `archived`
   - UI shows: Grayed out, "Restore" button

---

## Next Steps

1. ✅ Review this plan with team
2. Create migration file (`007_separate_status_fields.sql`)
3. Update `database.py` with new functions
4. Update `background_tasks.py` to use new states
5. Update API responses to include both fields
6. Update frontend to read new fields (with fallback)
7. Test thoroughly in staging
8. Deploy to production
9. Monitor for issues
10. (Later) Deprecate old `status` field

---

## Questions to Resolve

1. Should `draft` status exist? (For forms user hasn't submitted yet)
2. What happens to `ready_to_send`? Map to `reviewed` or `ready`?
3. Should we track WHO sent the report? (admin user ID)
4. Should archived submissions be hidden by default in dashboard?
5. Can user un-archive? Or is archive permanent?

---

## Estimated Effort

- Database migration: 30 min
- Backend updates: 2-3 hours
- Frontend updates: 2-3 hours (depends on complexity)
- Testing: 1-2 hours
- **Total: 6-9 hours** (1-2 days)

**Priority:** Medium-High (reduces confusion, enables user workflows)
