# CI Parity Integration Guide

This guide shows how to integrate the CI Parity System into your CI/CD workflows.

---

## GitHub Actions Integration

### Complete Workflow Example

```yaml
name: CI Parity

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

permissions:
  contents: read
  pull-requests: write

jobs:
  parity-bootstrap:
    name: Bootstrap Parity Environment
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Cache Parity Environment
        uses: actions/cache@v3
        with:
          path: .venv-parity
          key: venv-parity-${{ runner.os }}-py3.11-${{ hashFiles('requirements-dev.txt', 'ci/parity.lock.json') }}
          restore-keys: |
            venv-parity-${{ runner.os }}-py3.11-
      
      - name: Bootstrap Parity Environment
        run: ./scripts/ft-parity-bootstrap.sh
      
      - name: Upload Parity Environment
        uses: actions/upload-artifact@v3
        with:
          name: venv-parity
          path: .venv-parity/
          retention-days: 1

  parity-selfcheck:
    name: Parity Self-Check (Preflight)
    runs-on: ubuntu-latest
    needs: parity-bootstrap
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Download Parity Environment
        uses: actions/download-artifact@v3
        with:
          name: venv-parity
          path: .venv-parity/
      
      - name: Parity Self-Check
        run: |
          chmod +x .venv-parity/bin/*
          . .venv-parity/bin/activate
          . .venv-parity/parity-env.sh
          python -c "from firsttry.ci_parity.parity_runner import main; import sys; sys.exit(main(['--self-check', '--explain']))"
      
      - name: Upload Self-Check Report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: selfcheck-report
          path: artifacts/parity_report.json

  parity-full:
    name: CI Parity Full Run
    runs-on: ubuntu-latest
    needs: parity-selfcheck
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Download Parity Environment
        uses: actions/download-artifact@v3
        with:
          name: venv-parity
          path: .venv-parity/
      
      - name: Run Full Parity
        run: |
          chmod +x .venv-parity/bin/*
          . .venv-parity/bin/activate
          . .venv-parity/parity-env.sh
          FT_NO_NETWORK=1 python -c "from firsttry.ci_parity.parity_runner import main; import sys; sys.exit(main(['--parity', '--explain']))"
      
      - name: Upload Parity Report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: parity-report
          path: artifacts/parity_report.json
      
      - name: Upload Coverage Report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: coverage-report
          path: artifacts/coverage.xml
      
      - name: Comment PR with Parity Results
        if: github.event_name == 'pull_request' && always()
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = JSON.parse(fs.readFileSync('artifacts/parity_report.json', 'utf8'));
            
            let comment = '## CI Parity Report\\n\\n';
            
            if (report.ok) {
              comment += '✅ **All gates passed!**\\n\\n';
            } else {
              comment += '❌ **Parity failed**\\n\\n';
              comment += '### Failures\\n\\n';
              report.failures.forEach(f => {
                comment += `- **${f.code}** (${f.gate}): ${f.msg}\\n`;
                if (f.hint) comment += `  - *Hint:* ${f.hint}\\n`;
              });
            }
            
            comment += '\\n### Tool Versions\\n\\n';
            Object.entries(report.tool_versions || {}).forEach(([tool, version]) => {
              comment += `- ${tool}: ${version}\\n`;
            });
            
            comment += '\\n### Performance\\n\\n';
            Object.entries(report.durations_sec || {}).forEach(([tool, duration]) => {
              comment += `- ${tool}: ${duration.toFixed(2)}s\\n`;
            });
            
            comment += `\\n### Coverage\\n\\n`;
            comment += `- Current: ${(report.thresholds.coverage_total * 100).toFixed(1)}%\\n`;
            comment += `- Threshold: ${(report.thresholds.coverage_min * 100).toFixed(1)}%\\n`;
            
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.name,
              body: comment
            });

  parity-matrix:
    name: Parity Matrix (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    needs: parity-selfcheck
    strategy:
      fail-fast: false
      matrix:
        python-version: ['3.10', '3.11']
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Bootstrap Parity Environment
        run: ./scripts/ft-parity-bootstrap.sh
      
      - name: Run Parity Matrix
        run: |
          . .venv-parity/bin/activate
          . .venv-parity/parity-env.sh
          FT_NO_NETWORK=1 python -c "from firsttry.ci_parity.parity_runner import main; import sys; sys.exit(main(['--parity', '--matrix']))"
      
      - name: Upload Matrix Report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: parity-report-py${{ matrix.python-version }}
          path: artifacts/parity_report.json
```

---

## GitLab CI Integration

### Complete Pipeline Example

```yaml
# .gitlab-ci.yml

stages:
  - bootstrap
  - selfcheck
  - parity
  - report

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"
  FT_NO_NETWORK: "1"

cache:
  paths:
    - .cache/pip
    - .venv-parity/

bootstrap:parity:
  stage: bootstrap
  image: python:3.11-slim
  script:
    - ./scripts/ft-parity-bootstrap.sh
  artifacts:
    paths:
      - .venv-parity/
      - .venv-parity/parity-env.sh
    expire_in: 1 hour

selfcheck:parity:
  stage: selfcheck
  image: python:3.11-slim
  dependencies:
    - bootstrap:parity
  script:
    - . .venv-parity/bin/activate
    - . .venv-parity/parity-env.sh
    - python -c "from firsttry.ci_parity.parity_runner import main; import sys; sys.exit(main(['--self-check', '--explain']))"
  artifacts:
    when: always
    paths:
      - artifacts/parity_report.json
    expire_in: 1 week

parity:full:
  stage: parity
  image: python:3.11-slim
  dependencies:
    - bootstrap:parity
  script:
    - . .venv-parity/bin/activate
    - . .venv-parity/parity-env.sh
    - python -c "from firsttry.ci_parity.parity_runner import main; import sys; sys.exit(main(['--parity', '--explain']))"
  artifacts:
    when: always
    paths:
      - artifacts/parity_report.json
      - artifacts/coverage.xml
    reports:
      coverage_report:
        coverage_format: cobertura
        path: artifacts/coverage.xml
    expire_in: 1 week

parity:matrix:py310:
  stage: parity
  image: python:3.10-slim
  dependencies:
    - bootstrap:parity
  script:
    - ./scripts/ft-parity-bootstrap.sh
    - . .venv-parity/bin/activate
    - . .venv-parity/parity-env.sh
    - python -c "from firsttry.ci_parity.parity_runner import main; import sys; sys.exit(main(['--parity', '--matrix']))"
  artifacts:
    when: always
    paths:
      - artifacts/parity_report.json

parity:matrix:py311:
  stage: parity
  image: python:3.11-slim
  dependencies:
    - bootstrap:parity
  script:
    - ./scripts/ft-parity-bootstrap.sh
    - . .venv-parity/bin/activate
    - . .venv-parity/parity-env.sh
    - python -c "from firsttry.ci_parity.parity_runner import main; import sys; sys.exit(main(['--parity', '--matrix']))"
  artifacts:
    when: always
    paths:
      - artifacts/parity_report.json

report:parity:
  stage: report
  image: python:3.11-slim
  dependencies:
    - parity:full
  script:
    - cat artifacts/parity_report.json
    - python - <<'PY'
      import json
      with open("artifacts/parity_report.json") as f:
          report = json.load(f)
      if not report["ok"]:
          print("\\n❌ Parity failed:")
          for failure in report["failures"]:
              print(f"  {failure['code']}: {failure['msg']}")
          exit(1)
      print("\\n✅ All gates passed!")
      PY
```

---

## Jenkins Integration

### Jenkinsfile Example

```groovy
pipeline {
    agent any
    
    environment {
        FT_NO_NETWORK = '1'
    }
    
    stages {
        stage('Bootstrap Parity') {
            steps {
                sh './scripts/ft-parity-bootstrap.sh'
            }
        }
        
        stage('Parity Self-Check') {
            steps {
                sh '''
                    . .venv-parity/bin/activate
                    . .venv-parity/parity-env.sh
                    python -c "from firsttry.ci_parity.parity_runner import main; import sys; sys.exit(main(['--self-check', '--explain']))"
                '''
            }
        }
        
        stage('Parity Full') {
            steps {
                sh '''
                    . .venv-parity/bin/activate
                    . .venv-parity/parity-env.sh
                    python -c "from firsttry.ci_parity.parity_runner import main; import sys; sys.exit(main(['--parity', '--explain']))"
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'artifacts/parity_report.json,artifacts/coverage.xml', allowEmptyArchive: true
                    publishCoverage adapters: [coberturaAdapter('artifacts/coverage.xml')]
                }
            }
        }
        
        stage('Parity Matrix') {
            matrix {
                axes {
                    axis {
                        name 'PYTHON_VERSION'
                        values '3.10', '3.11'
                    }
                }
                stages {
                    stage('Matrix Run') {
                        steps {
                            sh '''
                                pyenv install -s ${PYTHON_VERSION}
                                pyenv local ${PYTHON_VERSION}
                                ./scripts/ft-parity-bootstrap.sh
                                . .venv-parity/bin/activate
                                . .venv-parity/parity-env.sh
                                python -c "from firsttry.ci_parity.parity_runner import main; import sys; sys.exit(main(['--parity', '--matrix']))"
                            '''
                        }
                    }
                }
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: 'artifacts/*.json', allowEmptyArchive: true
        }
    }
}
```

---

## Exit Code Reference

| Code | Gate | Meaning | Action |
|------|------|---------|--------|
| 0 | - | All green | Ship it! |
| 101 | preflight | Version drift | Install correct versions |
| 102 | preflight | Config drift | Update lock or restore config |
| 103 | preflight | Plugin missing | Install missing plugin |
| 104 | preflight | Collection drift | Update tests or lock |
| 105 | preflight | Env mismatch | Set required env vars |
| 106 | preflight | Changed-only forbidden | Remove --changed-only flag |
| 211 | lint | Ruff failed | Run `ruff check --fix .` |
| 212 | types | MyPy failed | Fix type errors |
| 221 | tests | Pytest failed | Fix failing tests |
| 222 | tests | Test timeout | Optimize slow tests |
| 231 | coverage | Coverage too low | Add tests |
| 241 | security | Bandit failed | Fix security issues |
| 242 | security | Severity gate | Fix HIGH/MEDIUM issues |
| 301 | artifacts | Missing artifact | Check tool execution |
| 310 | build | Build failed | Fix build errors |
| 311 | import | Import failed | Install package correctly |

---

## Best Practices

### 1. Cache Optimization

```yaml
# GitHub Actions
- name: Cache Parity Environment
  uses: actions/cache@v3
  with:
    path: .venv-parity
    key: venv-parity-${{ runner.os }}-py${{ matrix.python-version }}-${{ hashFiles('requirements-dev.txt', 'ci/parity.lock.json') }}
```

### 2. Parallel Execution

Run self-check in parallel with other fast gates, then run full parity:

```yaml
jobs:
  fast-gates:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        gate: [selfcheck, lint, types]
```

### 3. Fail Fast

Use `fail-fast: true` in matrix builds during development, `false` in production to see all failures.

### 4. Artifact Retention

Keep parity reports for at least 30 days for forensics:

```yaml
- uses: actions/upload-artifact@v3
  with:
    retention-days: 30
```

### 5. Network Sandbox

Always set `FT_NO_NETWORK=1` in CI to catch flaky tests:

```yaml
env:
  FT_NO_NETWORK: "1"
```

---

## Troubleshooting

### Issue: Bootstrap fails in CI

**Solution**: Ensure Python and pip are available:

```yaml
- name: Set up Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.11'
```

### Issue: Self-check fails with version drift

**Solution**: Update `requirements-dev.txt` to match `ci/parity.lock.json`.

### Issue: Tests timeout in CI

**Solution**: Increase timeout in `ci/parity.lock.json`:

```json
{
  "tools": {
    "pytest": {
      "timeout_sec": 1200
    }
  }
}
```

### Issue: Coverage report missing

**Solution**: Ensure pytest runs with coverage flags in lock file.

---

**Updated:** November 11, 2025  
**See Also:** CI_PARITY_VALIDATED.md
