# G04 T10 Native CI — Python 환경 경계 실패 및 최소 수정
## RED 원본
- Run 45916811032, job 140237898527, source 5359de80409bd96ba72fe3e9f650ebba3deb794f, overall failure.
- Artifact 15162113924, size 83906, server-reported ZIP SHA256 da2b6813218da5cceeec45421949be692cded1c613b0376a36e0d4b5c87a2f23. 로그 6430행 분석; ZIP 자체 재해시 미실시.
- 00:32:41 UTC apt setup python3-typeguard (4.1.5-1) 성공. 00:33:32 pinned pip installs success; 00:33:33 pip check: generate-parameter-library-py 0.7.7 requires typeguard, which is not installed. Exit 1. EGL, asset materialization, native build, install, physics all NOT_RUN.
- 원인 가설: ROS Docker inherited PYTHONPATH makes ROS distributions visible to isolated venv without their apt dependency paths. Actual path evidence will be captured in next run; no need to add a pip typeguard version or remove pip check.
- apt installed Nav2 1.3.14 versus historical 1.3.13, MoveIt 2.12.4. This is a new environment, not historical acceptance.
## GREEN 변경
- Only Ch15 CI script: remove PYTHONPATH/PYTHONHOME at venv creation, pip install/check/freeze and EGL smoke, disable user-site; record inherited path, enforce distribution ownership in venv, separately verify system typeguard and yaml imports.
- Original Ch13 env.sh and sitecustomize remain unchanged for actual native runtime. No threshold/asset lock changes. No physical acceptance claimed.
- Same actual CI run once on new source; fresh dependencies necessary because original job ephemeral. G03/T11 not rerun. If next failure is different, retain first failure and inspect new boundary. No blind retries.
## 상태
T10 native L2 pending; G04 PARTIAL_PASS_T11; L3 NOT_RUN; F01 BLOCKED; main merge/publication HOLD.
