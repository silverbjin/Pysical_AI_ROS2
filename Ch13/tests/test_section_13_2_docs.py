from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def test_lab_guide_contains_reproducible_engine_workflows_and_expected_results():
    text = (DOCS / "LAB_13_2_GUIDE_KO.md").read_text(encoding="utf-8")
    for required in (
        "colcon build",
        "check_urdf",
        "gazebo.launch.py",
        "mujoco.launch.py",
        "verify_gazebo_13_2.py",
        "verify_mujoco_13_2.py",
        "20개",
        "미구현",
    ):
        assert required in text


def test_reuse_manifest_records_base_and_source_commits_and_no_legacy_changes():
    text = (DOCS / "REUSE_MANIFEST.md").read_text(encoding="utf-8")
    assert "1451f54a64374f2ff150a39429cc89e9e3b07696" in text
    assert "c261f5552edf124d1000a23fb25b6c07cadeb807" in text
    for chapter in ("Ch05", "Ch06", "Ch09", "Ch12"):
        assert chapter in text
    assert "직접 수정하지 않음" in text


def test_report_separates_verified_features_from_future_proposals_and_failures():
    text = (DOCS / "SECTION_13_2_REPORT_KO.md").read_text(encoding="utf-8")
    for required in (
        "검증 완료",
        "미구현 제안",
        "MoveIt 2",
        "PPO",
        "MujocoSystemInterface",
        "단일 명령 소유권",
        "robot_description",
        "미검증",
    ):
        assert required in text
