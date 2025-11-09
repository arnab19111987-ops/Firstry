import pytest

pytestmark = pytest.mark.filterwarnings(
    "ignore:.*FirstTryConfig.*:DeprecationWarning"
)


def test_firsttryconfig_alias_exists():
    from firsttry.config import FirstTryConfig, Config

    assert FirstTryConfig is Config
