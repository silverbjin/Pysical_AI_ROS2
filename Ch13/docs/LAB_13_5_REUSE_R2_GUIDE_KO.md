# R2 최소 연결 실행 가이드

현재 PC의 고정 A checkout·격리 venv·Jazzy를 사용하는 R2 기술 검증 실습이다. Ch05–12 빌드는 필요 없다. 새 컴퓨터용 배포/자산 설치 절차는 R5에서 정리한다.

## 실행 흐름

1. 엔진이 실행 중이지 않은 상태에서 `build_r2.sh`로 새 두 패키지만 빌드한다.
2. `audit_r2_install.py`로 실제 설치 byte·보완 코드·원본 자산을 확인한다.
3. 새 UUID evidence를 지정해 `run_r2_probe.py`를 실행한다. --launch를 지정하면 설치 launch가 ingress/gateway/platform을 시작하고 부모가 회수를 확인한다.
4. 원본home 유지→명시arm→짧은전진→0명령·정착→회전→0명령·정착→작은팔joint1목표·원복→raw손실·고장유지→정상회수를 확인한다.
5. 실행 종료 뒤 `verify_r2_probe.py`로 보존한500Hz정지창을 독립 판별한다. 실행 중 build/test/분석을 병행하지 않는다.

Ubuntu-24.04 WSL shell의 현재 경로 예:

```bash
reuse_repo=/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_reuse
bash "$reuse_repo/Ch13/scripts/reuse_13_5/build_r2.sh"
reuse_run=$(python3 -c 'import uuid; print(uuid.uuid4())')
reuse_evidence="$reuse_repo/Ch13/evidence/section_13_5_reuse/$reuse_run"
bash "$reuse_repo/Ch13/scripts/reuse_13_5/env_r2.sh" "$reuse_repo/Ch13/scripts/reuse_13_5/audit_r2_install.py" "$reuse_evidence/install_audit.json"
bash "$reuse_repo/Ch13/scripts/reuse_13_5/env_r2.sh" "$reuse_repo/Ch13/scripts/reuse_13_5/run_r2_probe.py" --repo-root "$reuse_repo" --evidence "$reuse_evidence" --launch
bash "$reuse_repo/Ch13/scripts/reuse_13_5/env_r2.sh" "$reuse_repo/Ch13/scripts/reuse_13_5/verify_r2_probe.py" "$reuse_evidence"
```

`env_r2.sh`는 프로세스에만 localhost/domain135와 격리Python을 적용한다. 전역 설정·드라이버·우선순위는 변경하지 않는다. 현재PC경로가고정돼있으므로다른환경에서는경로를맞춘다. sudo나전체Isaac학습환경은필요하지않다.

`platform.yaml`은 현재 고정 명세다. runtime 상수는 안전코어에서 관리하며 YAML만 편집해 운전조건을 바꾸는 기능은 제공하지 않는다. 속도명령 slew는sim시간기준(vx0.30,wz0.50/sim초)이며 실제몸체가속도상한검증은별도다. watchdog은wall0.30초를사용한다.

## 명령·상태 해석

- 입력은 `TwistStamped`, frame `reuse/nav_base`, engine `/clock` 기준 stamp다. 일반 system-time now를 engine stamp로 대신하지 않는다.
- R2입력은수동시험raw경로다. Nav2/smoother는R3에서연결한다. upstream다리/팔토크토픽에직접속도를보내지않는다.
- gateway와platform은각각명시arm한다. FAULT뒤에는각reset후새관측·0명령을받고다시arm한다. 입력복귀만으로움직이지않는다.
- `/engine_state`는실제3D몸체, `/odometry`는실제xy/yaw의명시적평면projection이다. TF의nav_base→base가원본z/roll/pitch를보존한다.
- 팔독립성검사는정지중joint1작은offset하나만확인한다. 임의6축조작·MoveIt·파지실습이아니다.
- `/ch13/reuse/platform/shutdown`은최신실측정착·0명령일때만정상종료를승인한다. 기본40sim초상한으로종료된실행은정상인수PASS가아니다.
- `work/ch13_reuse_engine.lock`의PID문자열은마지막기록이다. 활성소유권은flock과실제프로세스/실행명으로판별하며기록PID만으로다른프로세스를종료하지않는다.

## 결과 확인

`probe_summary.json`의PASS, 실제이동거리,최초receipt기준손실반응,고장유지,launch자식3개의clean exit·부모exit0/reaped와engine의RX/upstreamthread join을각각확인한다. `edu_stop_verification.json`의PASS도별도로확인한다. 최소1wall초와0.5sim초를모두만족할때까지기다리며느린simulation자체를정착실패로세지않는다.

새패키지의현재검사:

```bash
bash "$reuse_repo/Ch13/scripts/reuse_13_5/env_r2.sh" -m unittest discover -s "$reuse_repo/Ch13/ros2_ws/src/ch13_navigation_reuse/test" -v
```

현재45개검사와설치launch실제전진·회전·정지·손실·회수가성공했다. [최신단계3보고서](SECTION_13_5_REUSE_R2_STAGE_3_KO.md)에완료범위와실패보존을분리했다. [게시완료기록](SECTION_13_5_REUSE_R2_STAGE_4_PUBLICATION_KO.md)도확인한다. 기존Task8/R1실패를새PASS로바꾸지않는다.


ROS launch CLI는 시스템Python을 사용하며 추론/노드의Python은 launch의 `python` 인자로 기존venv를 쓴다. probe는 이를 각각 지정한다. 직접CLI실행시 `/usr/bin/python3 /opt/ros/jazzy/bin/ros2 launch ...`를 사용한다. launch의exit0만으로성공을판정하지않고engine.json의COMPLETED/normal_shutdown_requested와정착·probe·자식회수결과를모두확인한다.

보고서 자동생성: 성공UUID에 대해 `write_r2_completion_report.py "$reuse_evidence"`를 실행한다. 현재고정45검사로그와정지/실행PASS·source snapshot·동일boot회수를대조해단계3문서를생성한다. `refresh_r2_records.py`는source/evidence해시목록만갱신하며게이트수치를바꾸지않는다.
