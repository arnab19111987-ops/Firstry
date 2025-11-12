# Contributing to FirstTry

Thank you for your interest in contributing to FirstTry! We appreciate your help in making this project better.

## Code of Conduct

We follow the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).  
Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

## Getting Started

### Development Setup

1. **Fork the repository**
   ```bash
   gh repo fork arnab19111987-ops/Firstry --clone
   cd Firstry
   ```

2. **Install dependencies**
   ```bash
   python -m pip install -e ".[dev]"
   ```

3. **Run pre-commit checks locally**
   ```bash
   ft pre-commit
   ```

4. **Run tests**
   ```bash
   pytest tests/
   ```

## Making Changes

### Branch Naming

- Feature: `feat/description`
- Bug fix: `fix/description`
- Documentation: `docs/description`
- Performance: `perf/description`

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `security`

**Examples:**
```
feat(cache): add warm cache support with testmon
fix(cli): resolve exit code issue in pre-commit hook
docs(readme): update installation instructions
security: remove hardcoded default secret
```

### Pull Requests

1. **Create a new branch** from `main`
2. **Make your changes** with clear, focused commits
3. **Run local checks** before submitting:
   ```bash
   ft pre-commit
   make audit-supply  # If changing dependencies
   ```
4. **Write or update tests** for any code changes
5. **Update documentation** if needed
6. **Submit a pull request** with:
   - Clear title and description
   - Link to any related issues
   - Screenshots/examples if applicable

### Code Style

- **Python:** Follow PEP 8 (enforced by ruff and black)
- **Type hints:** Use type annotations (checked by mypy)
- **Docstrings:** Use for public APIs
- **Tests:** Add tests for new features and bug fixes

### Testing Guidelines

- Write unit tests for new functions/classes
- Add integration tests for new features
- Ensure existing tests pass
- Aim for meaningful test coverage

## Review Process

1. Automated checks must pass (CI/CD pipeline)
2. Code review by maintainers
3. Address any feedback
4. Approval and merge

## What to Contribute

### Good First Issues

Look for issues tagged with `good first issue` or `help wanted`.

### Areas We Welcome Contributions

- Bug fixes
- Performance improvements
- Documentation improvements
- Test coverage expansion
- New features (discuss in an issue first)
- Security improvements

### Before Starting Major Work

For significant changes:
1. Open an issue to discuss your idea
2. Wait for maintainer feedback
3. Get approval before investing significant time

## Questions?

- **General Questions:** Open a [discussion](https://github.com/arnab19111987-ops/Firstry/discussions)
- **Bug Reports:** Open an [issue](https://github.com/arnab19111987-ops/Firstry/issues)
- **Security Issues:** Email security@firsttry.dev (see [SECURITY.md](SECURITY.md))

## License

By contributing to FirstTry, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).

---

Thank you for contributing! 🎉
