# S3 Integration Setup for Development

This guide helps you set up S3 integration locally for testing and development.

## Quick Start

### Using Cloudflare R2 (Recommended for Testing)

Cloudflare R2 offers a free tier perfect for development:

1. **Create R2 Bucket**
   - Go to https://dash.cloudflare.com
   - Navigate to R2 Storage
   - Create bucket: `firsttry-benchmark-dev`

2. **Generate API Token**
   - Go to Account Settings → API Tokens
   - Create token with R2 permissions
   - Save credentials

3. **Set Environment Variables**
   ```bash
   export S3_ACCESS_KEY_ID="your-token-id"
   export S3_SECRET_ACCESS_KEY="your-token-secret"
   export S3_ENDPOINT_URL="https://your-account.r2.cloudflarestorage.com"
   export S3_BUCKET_NAME="firsttry-benchmark-dev"
   ```

4. **Install boto3**
   ```bash
   pip install boto3
   ```

5. **Test Connection**
   ```bash
   python tools/ft_bench_s3.py
   ```

### Using LocalStack (Docker)

For local S3 emulation without external dependencies:

```bash
# Start LocalStack S3
docker run -p 4566:4566 localstack/localstack

# Set endpoints to local S3
export S3_ACCESS_KEY_ID="test"
export S3_SECRET_ACCESS_KEY="test"
export S3_ENDPOINT_URL="http://localhost:4566"
export S3_BUCKET_NAME="test-benchmark"
export AWS_DEFAULT_REGION="us-east-1"

# Create bucket
aws s3 mb s3://test-benchmark --endpoint-url http://localhost:4566

# Test
python tools/ft_bench_s3.py
```

## Running Benchmarks with S3

### Without S3 (Default)
```bash
./scripts/ft_bench_run.sh
```

### With S3 Upload
```bash
export S3_ACCESS_KEY_ID="your-key"
export S3_SECRET_ACCESS_KEY="your-secret"
export S3_ENDPOINT_URL="https://your-endpoint.com"
export S3_BUCKET_NAME="your-bucket"

./scripts/ft_bench_run.sh --upload-s3
```

### Disable S3 Explicitly
```bash
export S3_ENABLED=false
./scripts/ft_bench_run.sh
```

## Testing

### Unit Tests

```bash
# Run all tests (S3 integration is optional)
python -m pytest tests/ -v

# Run just harness tests
python -m pytest tests/test_bench_harness.py -v
```

### Integration Tests

```bash
# Test with LocalStack
docker run -d -p 4566:4566 localstack/localstack
sleep 5

# Create test bucket
aws s3 mb s3://test --endpoint-url http://localhost:4566

# Run benchmark with S3
export S3_ENDPOINT_URL="http://localhost:4566"
export S3_BUCKET_NAME="test"
export S3_ACCESS_KEY_ID="test"
export S3_SECRET_ACCESS_KEY="test"

./scripts/ft_bench_run.sh --skip-cold --upload-s3

# Verify upload
aws s3 ls s3://test/benchmarks/ --endpoint-url http://localhost:4566
```

## Troubleshooting

### "boto3 not found"
```bash
pip install boto3
```

### "Connection refused"
- Check endpoint URL is correct
- Ensure S3 service is accessible
- For LocalStack, verify container is running

### "Access denied"
- Verify credentials are correct
- Check bucket permissions
- Try with LocalStack for testing

### Credentials Leak
If you accidentally expose credentials:
1. Revoke them immediately in your S3 provider
2. Generate new credentials
3. Remove from shell history: `history -c`
4. Search git: `git log --source --all -S "YOUR_KEY"`

## Environment File Template

Create `.env.s3` (never commit):

```bash
# Cloudflare R2
export S3_ACCESS_KEY_ID="..."
export S3_SECRET_ACCESS_KEY="..."
export S3_ENDPOINT_URL="https://....r2.cloudflarestorage.com"
export S3_BUCKET_NAME="firsttry-benchmark-dev"

# Optional
export S3_REGION="auto"
export S3_PREFIX="dev"
export S3_ENABLED="true"
```

Usage:
```bash
source .env.s3
./scripts/ft_bench_run.sh --upload-s3
```

## CI/CD Setup

### GitHub Actions Secrets

1. Go to Settings → Secrets and variables → Actions
2. Add secrets:
   - `S3_ACCESS_KEY_ID`
   - `S3_SECRET_ACCESS_KEY`
   - `S3_ENDPOINT_URL`
   - `S3_BUCKET_NAME`

3. Use in workflow:
```yaml
- name: Benchmark with S3
  env:
    S3_ACCESS_KEY_ID: ${{ secrets.S3_ACCESS_KEY_ID }}
    S3_SECRET_ACCESS_KEY: ${{ secrets.S3_SECRET_ACCESS_KEY }}
    S3_ENDPOINT_URL: ${{ secrets.S3_ENDPOINT_URL }}
    S3_BUCKET_NAME: ${{ secrets.S3_BUCKET_NAME }}
  run: ./scripts/ft_bench_run.sh --upload-s3
```

## References

- **Cloudflare R2**: https://developers.cloudflare.com/r2/
- **boto3 docs**: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
- **AWS S3**: https://aws.amazon.com/s3/
- **LocalStack**: https://github.com/localstack/localstack
