# 차기 Gazebo CI 검수 범위 — Ch05, Ch09~Ch11

## 실행 환경

GitHub Actions 워크플로: Book next Gazebo runtime Ch05, Ch09-Ch11.

재사용 Docker 이미지: ghcr.io/silverbjin/pysical-ai-book-gazebo@sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f

- 소스 SHA, 실제 컨테이너 이미지 ID, 각 챕터의 종료코드와 최초 실패 단계 STAGE를 GitHub Artifact로 저장한다.
- Ch05, Ch09, Ch10, Ch11은 각각 독립 컨테이너와 ROS_DOMAIN_ID, GZ_PARTITION을 사용한다.
- Gazebo 서버는 headless로 실행한다. GUI 및 WSLg 시각적 검수는 별도다.

## Ch05 실습 대응 범위

LAB_5_2: 원본 Xacro·controller YAML로 실제 Gazebo 월드에 로봇을 생성하고, controller_manager와 joint_state_broadcaster, arm_controller가 모두 active인지 검사한다. /clock 및 명령 토픽 subscriber 존재도 검사한다.

LAB_5_3 및 5_4: 원본의 'ros2 run manipulation_basics simple_controller'를 단 한 번 실행한다. 실제 JointTrajectory joint2 목표 0.5rad 메시지 수신과 /joint_states의 joint2 실측 변화량 0.15rad 이상을 함께 요구한다. 이 기준은 실측 움직임 증명이며 위치 오차의 정밀 인수 기준은 아니다.

**차이**: 원본 'manipulation_system.launch.py'는 GUI Gazebo/RViz를 포함한다. 본 CI는 동일 URDF·YAML·제어기를 서버 전용 명령과 spawner로 구동한다. 즉 원본 Launch 자체의 GUI·동기화 검수는 수행하지 않는다.

Ch05 5.5의 GUI RViz 미러링, 5.6의 사인파 및 3회 독립 시동, 실제 하드웨어 시험은 NOT_RUN.

## Ch09~Ch11 검수 범위

각 절의 별도 my_quadruped_bot workspace에서 원본 Xacro 12개 관절 이름·limit를 확인하고, 원본 empty_world.sdf를 Gazebo 서버에 올린다. ros_gz_sim으로 실제 로봇 엔티티가 생성되고 /clock 브리지 수신에 성공해야 한다.

**미실행**: Ch09 안정적인 기립/정적 밸런스, Ch10 IK 제원 정합성 및 실제 보행, Ch11 센서 출력·EKF/SLAM lifecycle·지도 저장 및 루프 폐합. Ch10 README에 기록된 Xacro와 IK 제원 불일치를 통과 판정으로 감추지 않는다.

## 판정 정책

- PASS: 실제 실행한 계약의 모든 관찰값과 종료코드 통과.
- FAIL: 원본 월드, Xacro, 빌드, 스폰 또는 컨트롤러/센서 실측값 검증 실패.
- BLOCKED: 연결 권한·Docker 이미지 접근·외부 의존성 등 환경 장애.
- NOT_RUN: 현재 실행하지 않은 다른 절·GUI·고급 동적 시나리오.

전체 챕터 PASS로 승격하지 않는다. 실패 시 먼저 ci-results/next/ChXX/stages.log, gazeboserver.log, spawn.log 및 개별 evidence를 확인하고 실패한 챕터만 재검증한다.

## 현장 GUI 인수

강사 WSL2 Ubuntu 24.04에서 실습 가이드 그대로 Ch05 5.2→5.6과 Ch09→Ch11 각 실습 순서로 재현한다. 각 장의 workspace는 독립적으로 source하고 다른 장의 컨트롤러 및 ROS/Gazebo 프로세스를 정리한 뒤 진행한다. 캡처 화면과 joint_states·TF·센서·동작 판정 증거를 남긴다. CI가 GUI 성공을 대체하지 않는다.
