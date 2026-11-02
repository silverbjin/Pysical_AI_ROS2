# R4 S1 — 실제 RGB-D·팔 후보·시각 계약 중간 보고

작성일: 2026-11-02 KST. **R4 진행 중이며 실제 비전 목표 접근 PASS는 아직 아니다.**

## 구현과 부품 결과

실제MuJoCo Renderer의320×240 RGB/axial-depth를쓴다. camera15simHz, 처리cap10wallHz 기본/15wallHz선택이다. 느린sim에서실제wallHz를설정Hz로위장하지않고원본capture stamp와capture wall/CPP최초receipt를각각보존한다. RGB와depth/info/capture-meta를동일source stamp로묶고내용hash와실제GID를검사한다. 과거TF≤100simms,원본사진age≤300wallms/source≤300simms를유지한다.

13.4의수정하지않은geometry/contracts를별도선택빌드로재사용했다. 실제장면의붉은작업물색/깊이검출이며YOLO/일반물체인식이아니다. Renderer에서환경group5를보이도록명시해실제사진의빈작업물RED를해결했다. 실제RGB-D를역투영한표면점검사와소유권/원본시각/정착준비/IK/mapcollision이통과했다.

팔은실제mount/관절한계/FK/Jacobian position-only IK로검사하고최대체인길이0.885010m에서여유를뺀거리후보를쓴다.0.4m를복사하지않는다. Map footprint충돌과Nav2 ComputePathToPose비용으로고르며정지후실제root자세에서IK를다시검사한다. 팔명령/파지는실행하지않는다. 명시적vision lease를요구하면관측손실/중복소유자에latch·zero하고입력복귀로재개하지않는다.

**78/78 전체 검사 PASS,23.794초.** [로그](../evidence/section_13_5_reuse/r4_preflight/tests_78.log). 모델정답을쓴debug_candidates.json은IK준비점검일뿐visionPASS로세지않는다.

## 실제첫통합과추가보완

`581e5c05`는실제카메라140프레임중유효관측134건/관측reject0을기록했지만이동전gateway의FUTURE_SOURCE:base로시작조건이실패했다. 실패와정상회수를보존했다. 실제RGB첫사진/깊이/TF/point/hash는해당UUID에있다.

R3와같은유계수신순서보류를gateway에도적용했다. 실제clock이기존25simms범위로따라올때만입력으로쓰며원본receipt를바꾸지않는다. 보류50wallms초과또는100simms이상미래는fault다. 비유한값/축/frame/상태오류는보류전즉시차단한다. 관련RED→GREEN과기존future/중복/교체/만료/정지회귀를유지했다. Guard본래age/future수치는바꾸지않았다.

계측은upstream loop의4.626wall초공백/CPU0.00087초를보였다. 원본loop가time.time으로period를계산해절대시계역행에수초sleep을요청할수있는경계를별도RED로검사했다. 원본파일은변경하지않고run의time namespace만단조시계proxy로바꿨다. sleep요청은2ms물리주기이내로제한하고절대시계변화는기록한다. 물리dt/정책50Hz/관측/가중치/모터cap은동일하다. 실제공백의유일원인을아직단정하지않으며다음물리실행의계측으로확인한다. OS/WSL시각·드라이버·우선순위는변경하지않았다.

다음실제trial에서RGB-D→과거TF→후보/경로비용→Nav2terminal→실제root/정착/작업영역→READY를확인한다. R5최종동결전실패/보완은모두별도UUID로보존한다.
