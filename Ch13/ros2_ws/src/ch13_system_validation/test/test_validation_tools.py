from pathlib import Path
import pytest
from ch13_system_validation.tools import validate_build


@pytest.mark.parametrize('value', ['/home/jinho/ch13_reuse_13_7_build',
 '/home/jinho/ch13_reuse_13_7_build/install','/home/jinho',
 '/home/jinho/ch13_reuse_13_6_build','/home/jinho/ch13_reuse_r2_build'])
def test_protected_build_and_ancestors_rejected(value):
    with pytest.raises(ValueError):validate_build(value)


def test_separate_build_allowed():
    assert validate_build('/home/jinho/ch13_reuse_13_8_build')==Path('/home/jinho/ch13_reuse_13_8_build')
