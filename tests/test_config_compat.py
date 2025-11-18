import pytest

from firsttry.config import Config, FirstTryConfig

pytestmark = pytest.mark.filterwarnings("ignore:.*FirstTryConfig.*:DeprecationWarning")


def test_firsttryconfig_alias_exists() -> None:
    assert FirstTryConfig is Config
