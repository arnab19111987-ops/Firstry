# FirstTry Benchmark Harness - S3/R2 Integration Guide

## Overview

The benchmark harness now supports optional artifact archival to Amazon S3 or Cloudflare R2 storage. Benchmark reports are automatically uploaded for long-term storage, trend analysis, and CI/CD integration.

## Features

✅ **Secure Credential Management**
- Environment variable-based configuration (no hardcoded secrets)
- Support for AWS S3 and Cloudflare R2 endpoints
- Graceful degradation if boto3 not installed

✅ **Flexible Storage**
- Supports any S3-compatible storage (AWS S3, Cloudflare R2, MinIO, etc.)
- Organized key structure by repository and timestamp
- JSON reports with full metadata

✅ **Zero Impact**
- S3 upload is optional and non-blocking
- Failures don't affect benchmark execution
- Report generation continues even if upload fails

## Setup

### 1. Install boto3 (Optional)

S3 integration requires the `boto3` package:

```bash
pip install boto3
```

Without boto3, S3 integration will be silently skipped with a warning.

### 2. Configure Environment Variables

Set these environment variables before running benchmarks:

```bash
# Required: Credentials
export S3_ACCESS_KEY_ID="your-access-key-id"
export S3_SECRET_ACCESS_KEY="your-secret-access-key"

# Required: Storage details
export S3_ENDPOINT_URL="https://your-s3-endpoint.com"
export S3_BUCKET_NAME="your-bucket-name"

# Optional: Configuration
export S3_REGION="auto"              # Default: "auto"
export S3_PREFIX="benchmarks"        # Default: "benchmarks"
export S3_ENABLED="true"             # Default: "true"
```

### 3. AWS S3 vs Cloudflare R2

#### AWS S3
```bash
export S3_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
export S3_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
export S3_ENDPOINT_URL="https://s3.amazonaws.com"
export S3_BUCKET_NAME="my-benchmarks"
export S3_REGION="us-east-1"
```

#### Cloudflare R2
```bash
export S3_ACCESS_KEY_ID="7500dd16ef9fa65388c2eb37ff23d0a1"
export S3_SECRET_ACCESS_KEY="e3090f0c5b2ec021aa979c91e7816a810bafb6c6b77fffc36de06d6bd3c5c022"
export S3_ENDPOINT_URL="https://c208c6f7ff71df1b5cf4488638d3e6bd.r2.cloudflarestorage.com"
export S3_BUCKET_NAME="firsttry-bench"
```

## Usage

### Upload Reports During Benchmarking

```bash
# Run benchmark and upload to S3
./scripts/ft_bench_run.sh --upload-s3

# With other options
./scripts/ft_bench_run.sh --tier lite --upload-s3

# Pro tier with specific settings
./scripts/ft_bench_run.sh --tier pro --regress-pct 15 --upload-s3
```

### Output

When S3 upload succeeds:

```
✓ Benchmark report uploaded to S3
  Key: benchmarks/a1b2c3d4/2025-11-07T05:24:05Z-benchmark.json
  Size: 4521 bytes
  URL: https://your-bucket.r2.cloudflarestorage.com/benchmarks/a1b2c3d4/2025-11-07T05:24:05Z-benchmark.json
```

If upload fails (no S3 configured or boto3 not installed):

```
[SKIP] S3 upload skipped (not configured or unavailable)
```

## Storage Structure

Reports are organized by repository and timestamp:

```
s3://bucket-name/
└── benchmarks/
    └── {repo-id}/
        ├── 2025-11-07T05:24:05Z-benchmark.json
        ├── 2025-11-08T10:15:30Z-benchmark.json
        └── 2025-11-09T15:45:22Z-benchmark.json
```

- **repo-id**: Short SHA256 hash of repository name/path (8 chars)
- **Timestamp**: ISO 8601 format with UTC timezone

## Python API Usage

### Basic Usage

```python
from tools.ft_bench_s3 import S3ArchiveManager

# Load config from environment variables
manager = S3ArchiveManager()

if manager.is_available():
    # Upload from JSON file
    result = manager.upload_from_file(
        local_path=".firsttry/bench_proof.json",
        repo_root="/workspaces/Firstry",
        run_type="benchmark"
    )
    
    if result.success:
        print(f"Uploaded to: {result.url}")
    else:
        print(f"Upload failed: {result.error}")
```

### Advanced Usage

```python
from tools.ft_bench_s3 import S3ArchiveManager, S3Config

# Custom configuration
config = S3Config(
    access_key_id="your-key",
    secret_access_key="your-secret",
    endpoint_url="https://your-endpoint.com",
    bucket_name="my-bucket",
    region="auto",
    prefix="benchmarks/prod"
)

manager = S3ArchiveManager(config)

# Upload report data directly
report_data = {
    "schema": 1,
    "timestamp": "2025-11-07T05:24:05Z",
    # ... full report ...
}

result = manager.upload_benchmark_report(
    report_data=report_data,
    repo_root="/workspaces/Firstry",
    run_type="benchmark"
)

# List recent reports for a repository
reports = manager.list_reports(
    repo_root="/workspaces/Firstry",
    max_keys=10
)

for key in reports:
    print(f"Found: {key}")

# Download a report
report = manager.download_report(key=reports[0])
if report:
    print(f"Report: {report['timestamp']}")
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Benchmark

on: [push, pull_request]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run benchmark with S3 upload
        env:
          S3_ACCESS_KEY_ID: ${{ secrets.S3_ACCESS_KEY_ID }}
          S3_SECRET_ACCESS_KEY: ${{ secrets.S3_SECRET_ACCESS_KEY }}
          S3_ENDPOINT_URL: ${{ secrets.S3_ENDPOINT_URL }}
          S3_BUCKET_NAME: ${{ secrets.S3_BUCKET_NAME }}
        run: |
          ./scripts/ft_bench_run.sh --tier lite --upload-s3
      
      - name: Comment PR with results
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('.firsttry/bench_proof.md', 'utf-8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: report
            });
```

### GitLab CI

```yaml
benchmark:
  image: python:3.11
  script:
    - pip install boto3
    - ./scripts/ft_bench_run.sh --tier lite --upload-s3
  artifacts:
    paths:
      - .firsttry/bench_proof.json
      - .firsttry/bench_proof.md
    reports:
      dotenv: .firsttry/bench_report.env
  environment:
    name: benchmarks
```

### Pre-commit Hook

```yaml
- repo: local
  hooks:
    - id: ft-bench-s3
      name: FirstTry Benchmark with S3
      entry: bash -c 'S3_ENABLED=1 ./scripts/ft_bench_run.sh --tier lite --upload-s3'
      language: script
      pass_filenames: false
      stages: [manual]
```

## Monitoring & Analysis

### Trend Analysis Script

```python
from tools.ft_bench_s3 import S3ArchiveManager
import json

manager = S3ArchiveManager()

# List all reports for a repo
reports = manager.list_reports("/workspaces/Firstry", max_keys=100)

# Download and analyze trends
times = []
for key in sorted(reports)[-10:]:  # Last 10 reports
    report = manager.download_report(key)
    if report and "runs" in report and "warm" in report["runs"]:
        warm_time = report["runs"]["warm"].get("elapsed_s")
        if warm_time:
            times.append(warm_time)
            print(f"{key}: {warm_time:.2f}s")

if len(times) > 1:
    avg_time = sum(times) / len(times)
    trend = "📈 Getting slower" if times[-1] > avg_time else "📉 Improving"
    print(f"\nTrend: {trend}")
    print(f"Average: {avg_time:.2f}s")
    print(f"Current: {times[-1]:.2f}s")
```

## Troubleshooting

### boto3 Not Installed

```
[SKIP] S3 upload skipped (boto3 not installed)
```

**Solution:**
```bash
pip install boto3
```

### S3 Not Configured

```
[SKIP] S3 upload skipped (not configured or unavailable)
```

**Solution:** Verify environment variables are set:
```bash
echo $S3_ACCESS_KEY_ID
echo $S3_ENDPOINT_URL
echo $S3_BUCKET_NAME
```

### Connection Failed

```
[WARN] S3 upload failed: Connection error
```

**Solutions:**
1. Verify credentials are correct
2. Check endpoint URL is accessible
3. Ensure bucket exists and you have permissions
4. Test with AWS CLI: `aws s3 ls --endpoint-url YOUR_URL`

### Credential Exposure

⚠️ **NEVER commit credentials to git!**

If you accidentally commit credentials:
1. Revoke them immediately in your S3 provider
2. Generate new credentials
3. Remove commits from git history (force push)
4. Use environment variables only

## Security Best Practices

✅ **DO:**
- Use environment variables for credentials
- Store credentials in `.env` files (add to `.gitignore`)
- Use IAM roles in CI/CD environments
- Rotate credentials regularly
- Restrict bucket access with policies
- Enable bucket versioning

❌ **DON'T:**
- Hardcode credentials in scripts
- Commit `.env` files
- Share access keys in Slack/email
- Use overly permissive IAM policies
- Reuse credentials across services

## Examples

### Production Setup

```bash
# .env (add to .gitignore)
export S3_ACCESS_KEY_ID="your-key"
export S3_SECRET_ACCESS_KEY="your-secret"
export S3_ENDPOINT_URL="https://r2.example.com"
export S3_BUCKET_NAME="firsttry-benchmarks"
export S3_PREFIX="prod"

# Load and run
source .env
./scripts/ft_bench_run.sh --tier lite --upload-s3
```

### Development Setup

```bash
# Disable S3 for local development
export S3_ENABLED="false"
./scripts/ft_bench_run.sh

# Or skip boto3 entirely if not installed
./scripts/ft_bench_run.sh
```

### Docker

```dockerfile
FROM python:3.11

RUN pip install boto3

ENV S3_ENDPOINT_URL="https://r2.example.com"
ENV S3_BUCKET_NAME="benchmarks"

COPY . /app
WORKDIR /app

CMD ["./scripts/ft_bench_run.sh", "--upload-s3"]
```

## Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `S3_ACCESS_KEY_ID` | ✓ | - | S3 access key |
| `S3_SECRET_ACCESS_KEY` | ✓ | - | S3 secret key |
| `S3_ENDPOINT_URL` | ✓ | - | S3 endpoint URL |
| `S3_BUCKET_NAME` | ✓ | - | Bucket name |
| `S3_REGION` | - | `auto` | AWS region |
| `S3_PREFIX` | - | `benchmarks` | Key prefix |
| `S3_ENABLED` | - | `true` | Enable/disable S3 |

### Upload Result Fields

```json
{
  "success": true,
  "url": "https://bucket.r2.com/benchmarks/abc123/2025-11-07.json",
  "key": "benchmarks/abc123/2025-11-07.json",
  "size_bytes": 4521,
  "upload_time_ms": 234.5,
  "error": null
}
```

## Support

For issues or questions:
1. Check environment variables are correctly set
2. Verify S3 credentials and permissions
3. Test S3 connectivity with AWS CLI
4. Review logs for detailed error messages
5. Ensure boto3 is installed: `pip show boto3`

---

**Version:** 1.0.0  
**Status:** Production Ready  
**Last Updated:** 2025-11-07
