# API Documentation Scripts

This directory contains utility scripts for generating and managing API documentation.

## Available Scripts

### `generate_docs.py`

Generates comprehensive API documentation in multiple formats.

**Features:**
- OpenAPI JSON schema (for Swagger UI)
- OpenAPI YAML schema (for other tools)
- Markdown documentation (human-readable)
- Postman collection (for API testing)

**Usage:**

```bash
# Generate all formats (default)
python scripts/generate_docs.py

# Generate specific formats
python scripts/generate_docs.py --formats json,markdown

# Specify custom output directory
python scripts/generate_docs.py --output-dir api-docs

# Specify API host for examples
python scripts/generate_docs.py --host https://api.strategyai.com
```

**Options:**
- `--output-dir`: Output directory (default: `docs/`)
- `--formats`: Comma-separated list of formats (default: `all`)
  - Available: `json`, `yaml`, `markdown`, `postman`
- `--host`: API host URL for examples (default: `http://localhost:8000`)

**Output Files:**
- `openapi.json` - OpenAPI 3.0 schema in JSON format
- `openapi.yaml` - OpenAPI 3.0 schema in YAML format
- `API_DOCUMENTATION.md` - Comprehensive markdown documentation
- `postman_collection.json` - Postman Collection v2.1

**Requirements:**
```bash
# Optional: For YAML generation
pip install pyyaml
```

**Examples:**

```bash
# Development environment
python scripts/generate_docs.py --host http://localhost:8000

# Staging environment
python scripts/generate_docs.py --host https://staging-api.strategyai.com

# Production environment
python scripts/generate_docs.py --host https://api.strategyai.com --output-dir public/docs
```

## Generated Documentation Usage

### Swagger UI

1. Generate OpenAPI JSON:
   ```bash
   python scripts/generate_docs.py --formats json
   ```

2. Serve with Swagger UI:
   ```bash
   # Using Docker
   docker run -p 8080:8080 -v $(pwd)/docs:/docs \
     -e SWAGGER_JSON=/docs/openapi.json swaggerapi/swagger-ui
   ```

3. Access at: http://localhost:8080

### ReDoc

```bash
# Using npx
npx redoc-cli serve docs/openapi.json

# Using Docker
docker run -p 8080:80 -v $(pwd)/docs:/usr/share/nginx/html/docs \
  redocly/redoc
```

### Postman

1. Generate Postman collection:
   ```bash
   python scripts/generate_docs.py --formats postman
   ```

2. Import in Postman:
   - Open Postman
   - Click "Import"
   - Select `docs/postman_collection.json`
   - Set environment variables:
     - `base_url`: Your API URL
     - `jwt_token`: Your authentication token

## CI/CD Integration

### GitHub Actions

Add to `.github/workflows/docs.yml`:

```yaml
name: Generate API Docs
on:
  push:
    branches: [main]

jobs:
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt pyyaml
      - name: Generate docs
        run: python scripts/generate_docs.py --host https://api.strategyai.com
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./docs
```

### Pre-commit Hook

Add to `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: generate-api-docs
      name: Generate API Documentation
      entry: python scripts/generate_docs.py
      language: system
      pass_filenames: false
      files: 'app/(routes|models|core)/.*\.py$'
```

## Best Practices

1. **Regenerate after changes**: Run after updating routes or schemas
2. **Version control**: Commit generated docs for easy diffing
3. **Automate**: Use CI/CD to keep docs always up-to-date
4. **Review**: Check generated docs in PR reviews
5. **Publish**: Deploy to GitHub Pages, ReadTheDocs, or similar

## Troubleshooting

**Issue: ImportError when running script**
```bash
# Solution: Install dependencies
pip install -r requirements.txt
```

**Issue: YAML generation fails**
```bash
# Solution: Install PyYAML
pip install pyyaml
```

**Issue: ModuleNotFoundError for app modules**
```bash
# Solution: Run from project root
cd /path/to/strategy-ai-backend
python scripts/generate_docs.py
```

## Contributing

When adding new endpoints:
1. Add comprehensive docstrings with examples
2. Use FastAPI's `summary`, `description`, and `responses` parameters
3. Run documentation generator to verify
4. Review generated docs for clarity
5. Update examples if needed
