"""The source-first test environment must not multiply filesystem lookups."""
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[5]
spec=importlib.util.spec_from_file_location('reuse_test_runner',ROOT/'Ch13/scripts/reuse_13_6/run_tests.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)


def test_deduplication_preserves_first_source_precedence(tmp_path):
    source=str(tmp_path/'source');installed=str(tmp_path/'installed')
    assert runner.unique_import_paths([source,installed,source+'/',source])==[source,installed]


def test_equivalent_relative_paths_do_not_accumulate(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert runner.unique_import_paths(['','.',str(tmp_path)])==['']
