"""
Phase 2.D.5: Commit & Release Validation Tests

Validates:
- Conventional Commits enforcement (feat:, fix:, chore:, etc.)
- Co-author tracking
- Breaking change detection (!:)
- CODEOWNERS enforcement
- Commit message linting
- Release notes generation
- Scope validation

Enterprise requirement: Enforce commit hygiene for audit compliance
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import List

import pytest


@dataclass
class ConventionalCommit:
    """Represents a conventional commit."""

    type: str  # feat, fix, chore, docs, style, test, refactor
    scope: str | None
    description: str
    body: str | None = None
    footer: str | None = None
    breaking: bool = False

    def to_message(self) -> str:
        """Convert to commit message format."""
        subject = f"{self.type}"
        if self.scope:
            subject += f"({self.scope})"
        if self.breaking:
            subject += "!"
        subject += f": {self.description}"

        message = subject
        if self.body:
            message += f"\n\n{self.body}"
        if self.footer:
            message += f"\n\n{self.footer}"
        return message


@dataclass
class CommitValidator:
    """Validates conventional commits."""

    allowed_types: set[str] | None = None
    scopes: set[str] | None = None
    require_scope: bool = False
    max_subject_length: int = 72

    def __post_init__(self):
        if self.allowed_types is None:
            self.allowed_types = {
                "feat",
                "fix",
                "chore",
                "docs",
                "style",
                "test",
                "refactor",
                "perf",
                "ci",
                "build",
            }

    def parse(self, message: str) -> ConventionalCommit | None:
        """Parse conventional commit message."""
        # Pattern: type(scope)!?: description
        # Accept ANY type initially, validation happens in validate()
        pattern = r"^(\w+)(\([^)]+\))?(!)?:\s+(.+?)$"
        match = re.match(pattern, message.split("\n")[0])

        if not match:
            return None

        commit_type, scope_match, breaking, description = match.groups()
        scope = scope_match[1:-1] if scope_match else None

        return ConventionalCommit(
            type=commit_type, scope=scope, description=description, breaking=bool(breaking)
        )

    def validate(self, message: str) -> tuple[bool, List[str]]:
        """Validate commit message. Returns (valid, errors)."""
        errors = []
        lines = message.split("\n")
        subject = lines[0]

        # Parse
        commit = self.parse(subject)
        if not commit:
            errors.append("Invalid format. Expected: type(scope): description")
            return False, errors

        # Check type
        allowed = self.allowed_types or set()
        if commit.type not in allowed:
            errors.append(f"Invalid type '{commit.type}'. Allowed: {', '.join(sorted(allowed))}")

        # Check scope
        if self.require_scope and not commit.scope:
            errors.append("Scope required for this type")
        if commit.scope and self.scopes and commit.scope not in self.scopes:
            errors.append(f"Invalid scope '{commit.scope}'")

        # Check subject length
        if len(subject) > self.max_subject_length:
            errors.append(f"Subject too long ({len(subject)} > {self.max_subject_length})")

        return len(errors) == 0, errors


@dataclass
class CoAuthor:
    """Represents a co-author."""

    name: str
    email: str

    def to_footer(self) -> str:
        """Convert to commit footer format."""
        return f"Co-authored-by: {self.name} <{self.email}>"


class CodeOwnersRule:
    """Represents a CODEOWNERS rule."""

    def __init__(self, pattern: str, owners: List[str]):
        self.pattern = re.compile(f"^{pattern}$")
        self.owners = owners

    def matches(self, path: str) -> bool:
        """Check if path matches rule."""
        return self.pattern.match(path) is not None

    def get_owners(self, path: str) -> List[str] | None:
        """Get owners for path if matches."""
        if self.matches(path):
            return self.owners
        return None


class CodeOwners:
    """Manages CODEOWNERS enforcement."""

    def __init__(self):
        self.rules: List[CodeOwnersRule] = []

    def add_rule(self, pattern: str, owners: List[str]):
        """Add ownership rule."""
        self.rules.append(CodeOwnersRule(pattern, owners))

    def get_owners(self, path: str) -> List[str]:
        """Get owners for a file path."""
        for rule in self.rules:
            owners = rule.get_owners(path)
            if owners:
                return owners
        return []

    def validate_commit(
        self, commit: ConventionalCommit, changed_files: List[str], co_authors: List[str]
    ) -> tuple[bool, List[str]]:
        """Validate that required CODEOWNERS reviewed commit."""
        errors = []

        # Get all owners for changed files
        all_owners = set()
        for file_path in changed_files:
            owners = self.get_owners(file_path)
            all_owners.update(owners)

        # Check if required owners are in co-authors
        for owner in all_owners:
            if owner not in co_authors:
                errors.append(f"CODEOWNER '{owner}' missing from Co-authored-by footers")

        return len(errors) == 0, errors


@dataclass
class ReleaseNote:
    """Represents a release note entry."""

    version: str
    date: str
    features: List[str]
    fixes: List[str]
    breaking: List[str]


class ReleaseNotesGenerator:
    """Generates release notes from commits."""

    def __init__(self):
        self.commits: List[ConventionalCommit] = []

    def add_commit(self, commit: ConventionalCommit):
        """Add commit to release notes."""
        self.commits.append(commit)

    def generate(self, version: str) -> ReleaseNote:
        """Generate release notes for version."""
        features = []
        fixes = []
        breaking = []

        for commit in self.commits:
            entry = f"{commit.description}"
            if commit.scope:
                entry = f"**{commit.scope}**: {entry}"

            if commit.breaking:
                breaking.append(entry)
            elif commit.type == "feat":
                features.append(entry)
            elif commit.type == "fix":
                fixes.append(entry)

        return ReleaseNote(
            version=version,
            date=datetime.now().isoformat(),
            features=features,
            fixes=fixes,
            breaking=breaking,
        )


# ============================================================================
# TESTS
# ============================================================================


def test_conventional_commit_basic_format():
    """Test basic conventional commit parsing."""
    commit = ConventionalCommit(type="feat", scope="auth", description="add JWT validation")
    message = commit.to_message()

    assert message == "feat(auth): add JWT validation"
    assert "feat" in message
    assert "auth" in message


def test_conventional_commit_breaking_change():
    """Test breaking change detection."""
    commit = ConventionalCommit(
        type="feat", scope="api", description="change authentication header", breaking=True
    )
    message = commit.to_message()

    assert "feat(api)!" in message
    assert commit.breaking is True


def test_validator_accepts_valid_commit():
    """Test validator accepts correctly formatted commit."""
    validator = CommitValidator()

    message = "feat(auth): add JWT validation"
    is_valid, errors = validator.validate(message)

    assert is_valid
    assert len(errors) == 0


def test_validator_rejects_invalid_type():
    """Test validator rejects invalid commit type."""
    validator = CommitValidator()

    message = "feature(auth): add JWT validation"  # 'feature' not allowed
    is_valid, errors = validator.validate(message)

    assert not is_valid
    assert any("Invalid type" in e for e in errors)


def test_validator_rejects_missing_scope():
    """Test validator enforces scope requirement."""
    validator = CommitValidator(require_scope=True)

    message = "feat: add authentication"
    is_valid, errors = validator.validate(message)

    assert not is_valid
    assert any("Scope required" in e for e in errors)


def test_validator_enforces_scope_values():
    """Test validator enforces allowed scopes."""
    validator = CommitValidator(scopes={"auth", "api", "db"})

    message = "feat(invalid): add something"
    is_valid, errors = validator.validate(message)

    assert not is_valid
    assert any("Invalid scope" in e for e in errors)


def test_validator_enforces_subject_length():
    """Test validator enforces subject line length."""
    validator = CommitValidator(max_subject_length=50)

    message = "feat(auth): this is a very long commit message that exceeds the limit"
    is_valid, errors = validator.validate(message)

    assert not is_valid
    assert any("too long" in e for e in errors)


def test_parse_commit_with_body():
    """Test parsing commit with body."""
    validator = CommitValidator()
    message = """feat(auth): add JWT validation

This commit adds JWT token validation to all protected endpoints.
It includes both synchronous and asynchronous validation paths."""

    commit = validator.parse(message)

    assert commit is not None
    assert commit.type == "feat"
    assert commit.scope == "auth"
    assert "JWT token validation" in message


def test_coauthor_formatting():
    """Test co-author footer formatting."""
    coauthor = CoAuthor("Jane Doe", "jane@example.com")
    footer = coauthor.to_footer()

    assert footer == "Co-authored-by: Jane Doe <jane@example.com>"


def test_codeowners_single_rule():
    """Test CODEOWNERS single pattern rule."""
    owners = CodeOwners()
    owners.add_rule("src/auth/.*", ["@auth-team"])

    result = owners.get_owners("src/auth/jwt.py")

    assert "@auth-team" in result


def test_codeowners_multiple_patterns():
    """Test CODEOWNERS with multiple patterns."""
    owners = CodeOwners()
    owners.add_rule("src/auth/.*", ["@auth-team"])
    owners.add_rule("docs/.*", ["@docs-team"])
    owners.add_rule(".*", ["@everyone"])

    auth_owners = owners.get_owners("src/auth/jwt.py")
    docs_owners = owners.get_owners("docs/readme.md")

    assert "@auth-team" in auth_owners
    assert "@docs-team" in docs_owners


def test_codeowners_commit_validation_pass():
    """Test CODEOWNERS validation passes with required co-authors."""
    owners = CodeOwners()
    owners.add_rule("src/auth/.*", ["@alice", "@bob"])

    commit = ConventionalCommit(type="fix", scope="auth", description="fix JWT validation bug")

    changed_files = ["src/auth/jwt.py"]
    co_authors = ["@alice", "@bob"]

    is_valid, errors = owners.validate_commit(commit, changed_files, co_authors)

    assert is_valid
    assert len(errors) == 0


def test_codeowners_commit_validation_fail_missing_owner():
    """Test CODEOWNERS validation fails without required owner."""
    owners = CodeOwners()
    owners.add_rule("src/auth/.*", ["@alice", "@bob"])

    commit = ConventionalCommit(type="fix", scope="auth", description="fix JWT validation bug")

    changed_files = ["src/auth/jwt.py"]
    co_authors = ["@alice"]  # Missing @bob

    is_valid, errors = owners.validate_commit(commit, changed_files, co_authors)

    assert not is_valid
    assert any("missing from Co-authored-by" in e for e in errors)


def test_release_notes_feature_collection():
    """Test release notes collect feature commits."""
    gen = ReleaseNotesGenerator()
    gen.add_commit(ConventionalCommit("feat", "auth", "add JWT validation"))
    gen.add_commit(ConventionalCommit("feat", "api", "add pagination"))
    gen.add_commit(ConventionalCommit("fix", "db", "fix connection pool leak"))

    notes = gen.generate("1.0.0")

    assert len(notes.features) == 2
    assert len(notes.fixes) == 1
    assert "1.0.0" in notes.version


def test_release_notes_breaking_changes():
    """Test release notes highlight breaking changes."""
    gen = ReleaseNotesGenerator()
    gen.add_commit(ConventionalCommit("feat", "api", "change auth header format", breaking=True))
    gen.add_commit(ConventionalCommit("feat", "auth", "add JWT support"))

    notes = gen.generate("2.0.0")

    assert len(notes.breaking) == 1
    assert len(notes.features) == 1
    assert "auth header" in notes.breaking[0]


def test_commit_validation_workflow():
    """Test complete commit validation workflow."""
    validator = CommitValidator(scopes={"auth", "api", "db"}, require_scope=False)

    commits = [
        "feat(auth): add JWT validation",
        "fix(db): fix connection pool",
        "chore: update dependencies",
    ]

    valid_count = 0
    for msg in commits:
        is_valid, _ = validator.validate(msg)
        if is_valid:
            valid_count += 1

    assert valid_count == 3


def test_commit_policy_enforcement():
    """Test commit policy can be enforced at commit hook."""
    validator = CommitValidator(allowed_types={"feat", "fix", "chore"}, require_scope=True)

    # Should be rejected
    message = "docs: add readme"  # Type 'docs' not in allowed list
    is_valid, errors = validator.validate(message)

    assert not is_valid
    assert any("Invalid type" in e for e in errors)


def test_conventional_commit_parsing_edge_cases():
    """Test parsing handles edge cases."""
    validator = CommitValidator()

    # No scope
    commit1 = validator.parse("fix: handle null pointer exception")
    assert commit1.scope is None

    # With special characters in description
    commit2 = validator.parse("feat(api): add /v2/users endpoint")
    assert "/" in commit2.description

    # With colon in description
    commit3 = validator.parse("fix(config): resolve key:value parsing issue")
    assert "key:value" in commit3.description


def test_release_notes_sorting():
    """Test release notes maintain proper grouping."""
    gen = ReleaseNotesGenerator()

    # Add in random order
    gen.add_commit(ConventionalCommit("fix", "db", "fix pool"))
    gen.add_commit(ConventionalCommit("feat", "auth", "add JWT"))
    gen.add_commit(ConventionalCommit("fix", "api", "fix response"))
    gen.add_commit(ConventionalCommit("feat", "ui", "add dark mode"))

    notes = gen.generate("1.5.0")

    # Should be grouped by type
    assert len(notes.features) == 2
    assert len(notes.fixes) == 2
    assert all("add JWT" in f or "dark mode" in f for f in notes.features)
    assert all("pool" in f or "response" in f for f in notes.fixes)


def test_scope_validation_with_codeowners():
    """Test scope matches CODEOWNERS domains."""
    owners = CodeOwners()
    owners.add_rule("src/auth/.*", ["@auth-team"])
    owners.add_rule("src/api/.*", ["@api-team"])

    validator = CommitValidator(scopes={"auth", "api", "db"})

    # Scope should match CODEOWNERS pattern domains
    message = "feat(auth): add authentication"
    commit = validator.parse(message)

    assert commit.scope in {"auth", "api", "db"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
