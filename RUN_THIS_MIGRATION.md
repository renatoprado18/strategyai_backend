# Run This Supabase Migration NOW

## What This Does
Adds data quality tracking columns to the `submissions` table so you can see what data sources worked vs failed.

## Steps to Run

1. **Go to Supabase Dashboard**
   - Open https://supabase.com/dashboard
   - Select your project

2. **Open SQL Editor**
   - Click "SQL Editor" in left sidebar
   - Click "New Query"

3. **Copy and Paste This SQL**
   ```sql
   -- Add data quality tracking columns
   ALTER TABLE submissions
   ADD COLUMN IF NOT EXISTS data_quality_json TEXT,
   ADD COLUMN IF NOT EXISTS processing_metadata TEXT;

   -- Add indexes for performance
   CREATE INDEX IF NOT EXISTS idx_data_quality ON submissions USING gin (data_quality_json jsonb_path_ops);
   CREATE INDEX IF NOT EXISTS idx_processing_metadata ON submissions USING gin (processing_metadata jsonb_path_ops);
   ```

4. **Click "Run"**
   - Should see "Success. No rows returned"

5. **Verify**
   - Click "Table Editor" in sidebar
   - Select "submissions" table
   - Should see 2 new columns: `data_quality_json` and `processing_metadata`

## That's It!

Once deployed, every new submission will automatically track:
- Which Apify sources succeeded vs failed
- Data completeness percentage (0%, 25%, 50%, 75%, 100%)
- Quality tier (minimal, partial, good, full)
- Processing time and model used

The dashboard will show color-coded badges:
- 🟢 Full Data (4/4 sources)
- 🟡 Good Data (3/4 sources)
- 🟠 Partial Data (2/4 sources)
- 🔴 Minimal Data (0-1 sources)

**Existing submissions** will show as "minimal" until reprocessed (which is fine - just reprocess failed ones if needed).
