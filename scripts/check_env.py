#!/usr/bin/env python3
"""
Environment Variable Checker
Verifies Railway environment variables are configured correctly
"""

import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("STRATEGY AI - ENVIRONMENT CONFIGURATION CHECK")
print("=" * 60)

# Check ALLOWED_ORIGINS
allowed_origins = os.getenv("ALLOWED_ORIGINS", "NOT SET")
print(f"\n1. ALLOWED_ORIGINS:")
print(f"   Raw value: {repr(allowed_origins)}")
if allowed_origins != "NOT SET":
    origins_list = allowed_origins.split(",")
    print(f"   Parsed as {len(origins_list)} origins:")
    for i, origin in enumerate(origins_list, 1):
        print(f"      {i}. '{origin.strip()}'")
else:
    print("   ⚠️  WARNING: Not set, using defaults")

# Check OPENROUTER_API_KEY
api_key = os.getenv("OPENROUTER_API_KEY", "NOT SET")
print(f"\n2. OPENROUTER_API_KEY:")
if api_key == "NOT SET":
    print("   ❌ NOT SET - AI analysis will fail!")
elif api_key == "your_key_here":
    print("   ❌ PLACEHOLDER VALUE - Replace with real key!")
elif api_key.startswith("sk-or-"):
    print(f"   ✅ Set correctly: {api_key[:20]}...")
else:
    print(f"   ⚠️  Unusual format: {api_key[:20]}...")

# Check rate limit
rate_limit = os.getenv("MAX_SUBMISSIONS_PER_IP_PER_DAY", "3")
print(f"\n3. MAX_SUBMISSIONS_PER_IP_PER_DAY: {rate_limit}")

print("\n" + "=" * 60)
print("RAILWAY DEPLOYMENT INSTRUCTIONS")
print("=" * 60)
print("\nIn your Railway dashboard, set these environment variables:\n")

print("ALLOWED_ORIGINS (comma-separated, NO SPACES):")
print("   https://your-vercel-app.vercel.app,https://www.your-domain.com")
print("\nOPENROUTER_API_KEY:")
print("   sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
print("\nMAX_SUBMISSIONS_PER_IP_PER_DAY:")
print("   3")

print("\n⚠️  IMPORTANT: After changing variables, Railway will auto-redeploy")
print("=" * 60)
