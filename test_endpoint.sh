#!/bin/bash
echo "=== Testing Form Enrichment Endpoint ==="
echo ""

echo "Test 1: With 'url' field (frontend format)"
curl -X POST https://web-production-c5845.up.railway.app/api/form/enrich \
  -H "Content-Type: application/json" \
  -d '{"url":"google.com","email":"test@test.com"}' \
  -w "\nHTTP_CODE: %{http_code}\n" 2>&1 | head -10
echo ""

echo "Test 2: With 'website' field (backend format)"  
curl -X POST https://web-production-c5845.up.railway.app/api/form/enrich \
  -H "Content-Type: application/json" \
  -d '{"website":"google.com","email":"test@test.com"}' \
  -w "\nHTTP_CODE: %{http_code}\n" 2>&1 | head -10
echo ""

echo "Test 3: Missing email (should fail gracefully)"
curl -X POST https://web-production-c5845.up.railway.app/api/form/enrich \
  -H "Content-Type: application/json" \
  -d '{"website":"google.com"}' \
  -w "\nHTTP_CODE: %{http_code}\n" 2>&1 | head -10
echo ""

echo "=== Testing Complete ==="
