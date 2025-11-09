#!/usr/bin/env python3
"""
Script to convert all print() statements to proper logger calls in Python files.
"""
import os
import re
from pathlib import Path

# Files to process (remaining ones with print statements)
FILES_TO_PROCESS = [
    "app/routes/reports.py",
    "app/routes/reports_confidence.py",
    "app/services/data/apify_research.py",
    "app/services/data/apify_scrapers.py",
    "app/services/analysis/multistage.py",
    "app/core/model_config.py",
    "app/routes/intelligence.py",
    "app/routes/chat.py",
    "app/routes/auth.py",
    "app/routes/admin.py",
    "app/services/pdf_generator.py",
    "app/services/intelligence/dashboard.py",
    "app/services/analysis/enhanced.py",
    "app/services/analysis/deep_dive.py",
    "app/services/analysis/confidence_scorer.py",
    "app/services/ai/chat.py",
    "app/core/security/rate_limiter.py",
    "app/core/security/prompt_sanitizer.py",
]

def has_logging_import(content):
    """Check if file already has logging import"""
    return 'import logging' in content

def has_logger_definition(content):
    """Check if file already has logger definition"""
    return 'logger = logging.getLogger(__name__)' in content

def add_logging_import(content):
    """Add logging import and logger definition to file"""
    lines = content.split('\n')

    # Find the last import line
    last_import_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            last_import_idx = i

    # Add logging import after last import
    if not has_logging_import(content):
        lines.insert(last_import_idx + 1, 'import logging')
        last_import_idx += 1

    # Add logger definition
    if not has_logger_definition(content):
        # Find first non-import, non-comment, non-docstring line
        insert_idx = last_import_idx + 1
        while insert_idx < len(lines) and (
            lines[insert_idx].strip() == '' or
            lines[insert_idx].strip().startswith('#')
        ):
            insert_idx += 1

        lines.insert(insert_idx, '')
        lines.insert(insert_idx + 1, 'logger = logging.getLogger(__name__)')

    return '\n'.join(lines)

def convert_print_to_logger(content):
    """Convert print() statements to appropriate logger calls"""
    lines = content.split('\n')
    modified_lines = []

    for line in lines:
        # Skip lines that don't contain print(
        if 'print(' not in line or line.strip().startswith('#'):
            modified_lines.append(line)
            continue

        # Determine logger level based on content
        if '[ERROR]' in line or 'ERROR' in line:
            level = 'error'
            # Check if we should add exc_info=True
            if 'except' in '\n'.join(lines[max(0, len(modified_lines) - 5):len(modified_lines)]):
                # This print is in an exception handler
                line = line.replace('print(', f'logger.{level}(')
                # Add exc_info=True if not already there
                if ', exc_info=True)' not in line:
                    line = line.rstrip(')')
                    if line.endswith(')'):
                        line = line[:-1] + ', exc_info=True)'
                    else:
                        line += ', exc_info=True)'
            else:
                line = line.replace('print(', f'logger.{level}(')
        elif '[WARNING]' in line or 'WARNING' in line or 'WARN' in line:
            level = 'warning'
            line = line.replace('print(', f'logger.{level}(')
        elif '[DEBUG]' in line or 'DEBUG' in line:
            level = 'debug'
            line = line.replace('print(', f'logger.{level}(')
        else:
            # Default to info
            level = 'info'
            line = line.replace('print(', f'logger.{level}(')

        # Remove traceback.print_exc() calls
        if 'traceback.print_exc()' in line:
            continue

        modified_lines.append(line)

    return '\n'.join(modified_lines)

def process_file(filepath):
    """Process a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Skip if no print statements
        if 'print(' not in content:
            print(f"⏭️  Skipping {filepath} (no print statements)")
            return 0

        original_content = content

        # Add logging import if needed
        content = add_logging_import(content)

        # Convert print to logger
        content = convert_print_to_logger(content)

        # Only write if content changed
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            # Count conversions
            count = original_content.count('print(')
            print(f"✅ Converted {filepath}: {count} print statements")
            return count
        else:
            print(f"⏭️  No changes needed for {filepath}")
            return 0

    except Exception as e:
        print(f"❌ Error processing {filepath}: {e}")
        return 0

def main():
    """Main function"""
    total = 0
    for file_path in FILES_TO_PROCESS:
        count = process_file(file_path)
        total += count

    print(f"\n✨ Total: Converted {total} print statements across {len(FILES_TO_PROCESS)} files")

if __name__ == '__main__':
    main()
