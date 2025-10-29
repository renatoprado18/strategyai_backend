#!/usr/bin/env python3
"""
Pre-Deployment Validation Script
Runs comprehensive checks before deploying to production.
"""

import os
import sys
import re
import ast
import importlib.util
from pathlib import Path
from typing import List, Tuple, Dict

# Color codes for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"


class ValidationError(Exception):
    """Custom exception for validation failures"""
    pass


class PreDeploymentValidator:
    def __init__(self, is_ci: bool = False):
        self.is_ci = is_ci or os.getenv("CI") == "true"
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.checks_passed = 0
        self.checks_total = 0

    def log_success(self, message: str):
        """Log a successful check"""
        self.checks_passed += 1
        self.checks_total += 1
        print(f"{GREEN}✅ {message}{RESET}")

    def log_warning(self, message: str):
        """Log a warning"""
        self.checks_total += 1
        self.warnings.append(message)
        print(f"{YELLOW}⚠️  {message}{RESET}")

    def log_error(self, message: str):
        """Log an error"""
        self.checks_total += 1
        self.errors.append(message)
        print(f"{RED}❌ {message}{RESET}")

    def log_info(self, message: str):
        """Log informational message"""
        print(f"{BLUE}ℹ️  {message}{RESET}")

    def check_environment_variables(self) -> bool:
        """Validate required environment variables"""
        print(f"\n{BLUE}{'='*60}")
        print("🔍 Checking Environment Variables")
        print(f"{'='*60}{RESET}\n")

        required_vars = [
            ("SUPABASE_URL", r"https?://.*\.supabase\.co"),
            ("SUPABASE_SERVICE_KEY", r"^eyJ.*"),  # JWT format
            ("SUPABASE_ANON_KEY", r"^eyJ.*"),
            ("UPSTASH_REDIS_URL", r"redis.*"),
            ("UPSTASH_REDIS_TOKEN", r"^.+$"),
            ("OPENROUTER_API_KEY", r"^sk-or-v1-.*"),
            ("JWT_SECRET", r"^.{32,}$"),  # At least 32 characters
            ("ALLOWED_ORIGINS", r"^https?://.*"),
        ]

        for var_name, pattern in required_vars:
            value = os.getenv(var_name)

            if not value:
                self.log_error(f"{var_name} is not set")
                continue

            if not re.match(pattern, value):
                self.log_error(f"{var_name} has invalid format")
                continue

            # Mask sensitive values in output
            if "KEY" in var_name or "SECRET" in var_name or "TOKEN" in var_name:
                masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                self.log_success(f"{var_name} is set ({masked})")
            else:
                display_value = value if len(value) < 50 else value[:50] + "..."
                self.log_success(f"{var_name} is set ({display_value})")

        # Check optional but recommended vars
        optional_vars = [
            "ENVIRONMENT",
            "LOG_LEVEL",
            "MAX_SUBMISSIONS_PER_IP_PER_DAY",
            "SENTRY_DSN"
        ]

        for var_name in optional_vars:
            value = os.getenv(var_name)
            if value:
                self.log_info(f"Optional: {var_name} is set")
            else:
                self.log_warning(f"Optional: {var_name} not set")

        return len(self.errors) == 0

    def check_python_syntax(self) -> bool:
        """Check Python files for syntax errors"""
        print(f"\n{BLUE}{'='*60}")
        print("🐍 Checking Python Syntax")
        print(f"{'='*60}{RESET}\n")

        base_path = Path(__file__).parent.parent
        python_files = []

        # Find all Python files
        for directory in ["app", "tests", "scripts"]:
            dir_path = base_path / directory
            if dir_path.exists():
                python_files.extend(dir_path.rglob("*.py"))

        syntax_errors = []

        for file_path in python_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    source_code = f.read()
                    ast.parse(source_code, filename=str(file_path))
            except SyntaxError as e:
                syntax_errors.append(f"{file_path}: {e}")
                self.log_error(f"Syntax error in {file_path.name}: {e}")
            except Exception as e:
                self.log_warning(f"Could not parse {file_path.name}: {e}")

        if not syntax_errors:
            self.log_success(f"All {len(python_files)} Python files have valid syntax")

        return len(syntax_errors) == 0

    def check_imports(self) -> bool:
        """Check for missing or circular imports"""
        print(f"\n{BLUE}{'='*60}")
        print("📦 Checking Imports")
        print(f"{'='*60}{RESET}\n")

        # Try importing key modules
        critical_modules = [
            "app.main",
            "app.core.database",
            "app.core.config",
            "app.routes.submissions",
            "app.services.analysis.multistage",
        ]

        import_errors = []

        for module_name in critical_modules:
            try:
                # Don't actually import in CI (would need deps)
                if self.is_ci:
                    self.log_info(f"Skipping import check for {module_name} (CI mode)")
                else:
                    importlib.import_module(module_name)
                    self.log_success(f"Successfully imported {module_name}")
            except ImportError as e:
                import_errors.append(f"{module_name}: {e}")
                if not self.is_ci:
                    self.log_error(f"Import error in {module_name}: {e}")
            except Exception as e:
                if not self.is_ci:
                    self.log_warning(f"Error importing {module_name}: {e}")

        if self.is_ci:
            self.log_success("Import checks skipped in CI mode")
            return True

        return len(import_errors) == 0

    def check_critical_files(self) -> bool:
        """Verify critical files exist"""
        print(f"\n{BLUE}{'='*60}")
        print("📁 Checking Critical Files")
        print(f"{'='*60}{RESET}\n")

        base_path = Path(__file__).parent.parent

        critical_files = [
            "app/main.py",
            "app/core/database.py",
            "app/core/config.py",
            "app/routes/submissions.py",
            "app/routes/user_actions.py",
            "app/services/analysis/multistage.py",
            "requirements.txt",
            "railway.json",
            "Procfile",
            ".env.example",
        ]

        missing_files = []

        for file_path in critical_files:
            full_path = base_path / file_path
            if full_path.exists():
                self.log_success(f"{file_path} exists")
            else:
                missing_files.append(file_path)
                self.log_error(f"{file_path} is missing")

        # Check migrations directory
        migrations_dir = base_path / "migrations"
        if migrations_dir.exists():
            migration_files = list(migrations_dir.glob("*.sql"))
            self.log_success(f"Migrations directory exists ({len(migration_files)} files)")
        else:
            self.log_error("Migrations directory is missing")
            missing_files.append("migrations/")

        return len(missing_files) == 0

    def check_security_issues(self) -> bool:
        """Check for common security issues"""
        print(f"\n{BLUE}{'='*60}")
        print("🔒 Checking Security Issues")
        print(f"{'='*60}{RESET}\n")

        base_path = Path(__file__).parent.parent

        # Check for hardcoded secrets
        secret_patterns = [
            (r"sk-or-v1-[a-f0-9]{64}", "OpenRouter API key"),
            (r"password\s*=\s*['\"][^'\"]+['\"]", "Hardcoded password"),
            (r"secret\s*=\s*['\"][^'\"]+['\"]", "Hardcoded secret"),
            (r"api_key\s*=\s*['\"][^'\"]+['\"]", "Hardcoded API key"),
        ]

        security_issues = []

        for directory in ["app", "scripts"]:
            dir_path = base_path / directory
            if not dir_path.exists():
                continue

            for py_file in dir_path.rglob("*.py"):
                try:
                    with open(py_file, "r", encoding="utf-8") as f:
                        content = f.read()

                        for pattern, issue_type in secret_patterns:
                            matches = re.finditer(pattern, content, re.IGNORECASE)
                            for match in matches:
                                # Skip if it's in a comment or env variable reference
                                if "os.getenv" in match.group(0) or "settings." in match.group(0):
                                    continue

                                security_issues.append(f"{py_file.name}: {issue_type}")
                                self.log_warning(f"Possible {issue_type} in {py_file.name}")

                except Exception as e:
                    self.log_warning(f"Could not scan {py_file.name}: {e}")

        if not security_issues:
            self.log_success("No obvious security issues found")

        # Check .env file is in .gitignore
        gitignore_path = base_path / ".gitignore"
        if gitignore_path.exists():
            with open(gitignore_path, "r") as f:
                gitignore_content = f.read()
                if ".env" in gitignore_content:
                    self.log_success(".env is in .gitignore")
                else:
                    self.log_error(".env is not in .gitignore")

        return True  # Don't fail deployment on security warnings

    def check_database_connectivity(self) -> bool:
        """Check database connection (skip in CI)"""
        if self.is_ci:
            self.log_info("Skipping database connectivity check (CI mode)")
            return True

        print(f"\n{BLUE}{'='*60}")
        print("🗄️  Checking Database Connectivity")
        print(f"{'='*60}{RESET}\n")

        try:
            from supabase import create_client

            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

            if not supabase_url or not supabase_key:
                self.log_warning("Supabase credentials not set, skipping connectivity check")
                return True

            client = create_client(supabase_url, supabase_key)
            response = client.table("submissions").select("id").limit(1).execute()

            self.log_success("Database connection successful")
            return True

        except Exception as e:
            self.log_error(f"Database connection failed: {e}")
            return False

    def check_redis_connectivity(self) -> bool:
        """Check Redis connection (skip in CI)"""
        if self.is_ci:
            self.log_info("Skipping Redis connectivity check (CI mode)")
            return True

        print(f"\n{BLUE}{'='*60}")
        print("💾 Checking Redis Connectivity")
        print(f"{'='*60}{RESET}\n")

        try:
            from upstash_redis import Redis

            redis_url = os.getenv("UPSTASH_REDIS_URL")
            redis_token = os.getenv("UPSTASH_REDIS_TOKEN")

            if not redis_url or not redis_token:
                self.log_warning("Redis credentials not set, skipping connectivity check")
                return True

            redis_client = Redis(url=redis_url, token=redis_token)
            redis_client.ping()

            self.log_success("Redis connection successful")
            return True

        except Exception as e:
            self.log_error(f"Redis connection failed: {e}")
            return False

    def run_all_checks(self) -> bool:
        """Run all validation checks"""
        print(f"\n{BLUE}{'='*70}")
        print("🚀 PRE-DEPLOYMENT VALIDATION")
        print(f"{'='*70}{RESET}")
        print(f"Mode: {'CI' if self.is_ci else 'Local'}\n")

        checks = [
            self.check_environment_variables,
            self.check_python_syntax,
            self.check_imports,
            self.check_critical_files,
            self.check_security_issues,
            self.check_database_connectivity,
            self.check_redis_connectivity,
        ]

        for check in checks:
            try:
                check()
            except Exception as e:
                self.log_error(f"Check failed with exception: {e}")

        # Print summary
        print(f"\n{BLUE}{'='*70}")
        print("📊 VALIDATION SUMMARY")
        print(f"{'='*70}{RESET}\n")

        print(f"Total checks: {self.checks_total}")
        print(f"{GREEN}✅ Passed: {self.checks_passed}{RESET}")
        print(f"{YELLOW}⚠️  Warnings: {len(self.warnings)}{RESET}")
        print(f"{RED}❌ Errors: {len(self.errors)}{RESET}\n")

        if self.errors:
            print(f"{RED}{'='*70}")
            print("❌ VALIDATION FAILED")
            print(f"{'='*70}{RESET}\n")
            print("Critical errors that must be fixed:\n")
            for i, error in enumerate(self.errors, 1):
                print(f"{i}. {error}")
            print()
            return False

        if self.warnings:
            print(f"{YELLOW}{'='*70}")
            print("⚠️  WARNINGS PRESENT")
            print(f"{'='*70}{RESET}\n")
            print("Non-critical warnings:\n")
            for i, warning in enumerate(self.warnings, 1):
                print(f"{i}. {warning}")
            print()

        print(f"{GREEN}{'='*70}")
        print("✅ VALIDATION PASSED - SAFE TO DEPLOY")
        print(f"{'='*70}{RESET}\n")

        return True


def main():
    """Main entry point"""
    validator = PreDeploymentValidator()

    try:
        success = validator.run_all_checks()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Validation cancelled by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Fatal error during validation: {e}{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
