# G09 자산 출처·권리·장기 보존 원장
기준: 검수 원본 main 9431fb535ce7a51416c19c4395fb2ba3fabdad40 / G09 QA 2d6e3c180fb5959597ccb4e5a6060f996c0596a3. 권리 확정은 사용자/출판사 책임자 승인 전 HOLD. 기술적 무결성과 권리를 분리한다.

| 자산 | 검증된 출처 및 기술 증거 | 최종 배포 |
|---|---|---|
| YOLOv8n/s 원본 PT | publisher revision a335eb8d58ded1464e0ff09b3994fc8ae0e6f8fe; expected SHA models/model_manifest.json; 실제 bytes G01 receipt 45744146299 hash verified | AGPL-3.0 publisher declaration; 모델/변환 바이너리 및 관련 소스의 배포 조건 검토 HOLD |
| YOLO ONNX | actual T02 seed parity, G01 45745101023 n e8950e7e6edc29ee614a027ee7a07aa492afbda7f24faad049972be5b7c96546 / s 6b213b04c58fc0df0039d59f00b665b727943ebed2a6a393727a2423a95e50e9; other export SHA distinct | 실제 로컬 생성만; 새 export bytes를 old SHA라고 주장하지 않음 |
| COCO evaluation | fixtures/g01_eval.lock.json, 20 exact images, manifest ffc6cf6fafc0c3c9477060596a838e303115f060d66011a75849a77c86a6086d; per-image license IDs 4/5 | image-level attribution/license 확인, 원본 이미지 재배포 HOLD |
| Gazebo person_standing | osrf/gazebo_models 8163eb4b5e7e21985c6591d1c0bfb56468c0093f; 14 file Git blob + LICENSE, fixtures/g03_scene.lock.json | declared CC BY 3.0 source-level, author and MakeHuman asset notices 확인, 배포 HOLD |
| Ch11/Ch12 | 28 exact vendor files verified; Ch12 controller/bridge reference separately G08 manifest; original Ch01~13 31,894 entries unchanged | owner rights/license review pending; TODO/undeclared not treated as permission |
| G07 smoke PPO/ONNX | original run45763347165 artifact15090667475 ZIP c8defc1a154c3d0ec92ddd3a7fbd70f8d3b012dc21d375acde9f5c5f9be9641d, 2,272,024 bytes, 23/23 internal reverified in G09; ONNX c6bc846346ea156f39b31a84da3e2051e17d377b39b825eb08ba3ef77f51e546, contract 1209b04f0d6f31d12249b7fd355ba4ed7d45789cfee8d94486d869608c48d168 | owner evaluation only, not original trained checkpoint or product; no public release/new training/export |
| CPU/RL/OV | hash locked wheel manifests; CPU/RL actual reinstall; OV separately actual CPU G02; apt and rosdep live resolution not a frozen offline OS snapshot | third-party dependency notices and license review pending, image digest recorded |
| GPU/TensorRT | T05 NOT_IMPLEMENTED/NOT_RUN, FP16/INT8 not actual | optional, don't present as CPU required |

Historic model_manifest status REMOTE_HASH_CONFIRMED_NOT_DOWNLOADED and original reuse.lock rows NOT_COPIED describe earlier audit snapshots. Current actual source receipts/REUSE_MANIFESTs above are authoritative for *technical* availability, not permission. Preserve prior exact manifests and workflows for provenance; do not silently rewrite success receipts.

## Owner evidence retention
G07 original archive downloaded and ZIP + 23 internal hashes checked. Keep exact bytes in authorized local/private backup before retention expires. GitHub Actions artifact links expire; do not assume perpetual retrieval. No model ZIP committed or new public artifact. If missing/expired/corrupt, stop with BLOCKED (no automatic retraining). Store original archive alongside SHA256 separately from reproducibility logs. G09 owner wrapper extracts only after exact ZIP SHA, verifies original 11 payload hashes with existing g07_verify_reuse.py. A new ZIP packaging the same files is not the original accepted ZIP.
