# Level 2 확장 시연 — 과거 운반·놓기 기록 읽기

이자료는실행시점v28의동일engine에서파지→귀환→내려놓기까지진행한기록해설이다. 최신버전의안정적완주실습이나현재합격증거로제시하지않는다. 학생기본명령은 [START_HERE](START_HERE_13_8_KO.md)다.

사례: **621d134d-be0a-405c-af20-e5ac913940b7**. source_manifest SHA7522c22eb7d6a7715837cb8cc2d278b67606b8b647738bf89d724d12bf998c99/v28. 원래BTterminal은SUCCESS, trial.success는false다. 서로다른판정을동시에읽는것이시연의핵심이다.

```bash
bash Ch13/scripts/reuse_13_8/env.sh Ch13/scripts/reuse_13_8/inspect_case.py \
 --case Ch13/evidence/section_13_8_system/621d134d-be0a-405c-af20-e5ac913940b7
```

|기록에서 확인할 순서|실제확인범위|
|---|---|
|navigate/find|경사접촉·원통새관측·접근완료|
|pick|최소101.245mm상승,2.22sim초hold,양finger접촉100%,물리Pick PASS|
|return/CARRY|물체시작·끝수평변위3.918m,접촉비율100%.누적경로길이와구분|
|place|수령지지·개방·detach·후퇴·놓은뒤유지확인|
|finish|worker/소유프로세스회수와기록종료|

임무259.912sim초/630.094wall초,로봇귀환오차55.231mm였다. 운반중세계높이하락23.360mm가추가20mm기준을넘어transport FAIL이었다. 물체수령위치/지지/개방은true다. 세계높이하락과물체놓침을동일하게해석하지않는다. 교육용완화시간·위치수치에한사례가들어와도반복성공률이나유지중인물리witness통과를입증하지않는다. 원래판정을바꾸지않는다.

기본trial/BT/manifest 등의작은기록은저장소자료로읽는다. raw.tar.gz와source archive는로컬보존본이있으며**Git clone에모든대형raw/rosbag가포함된다고가정하지않는다.** 추가raw가필요하면원본hash가포함된raw_manifest와보존본을함께받아새폴더로복원한다. 없는bag를재생했다고주장하지않는다. [과거평가보고](SECTION_13_8_LEVEL23_EVALUATION_REPORT_KO.md)에정확한동결·압축hash와판정이있다.

과제: ①완료한동작순서 ②BT SUCCESS와trial FAIL이공존한이유 ③로봇귀환오차와물체수령위치의차이 ④최신코드재현성증거가아닌이유를설명한다. raw재생은별도domain의읽기전용분석만허용하며live권한/팔명령에연결하지않는다.
