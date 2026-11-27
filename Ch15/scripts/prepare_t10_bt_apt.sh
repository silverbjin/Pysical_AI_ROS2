#!/usr/bin/env bash
# Dedicated CI container only; never modify owner apt.
set -Eeuo pipefail
[[ $# == 1 && -f /work/native/Ch13/scripts/reuse_13_7/prepare_bt_deps.sh ]] || exit 2
e="$1"
mkdir -p "$e"
cat > "$e/bt-exact-lock.txt" <<'LOCK'
ros-jazzy-py-trees 2.6.0-1noble.20260911.044440 70b3b3f0188823ec8823d138fa2b45f984f5e12cb48a16ab1de0ca7a474627f5
ros-jazzy-py-trees-ros 2.6.0-1noble.20261006.034533 ad720943b8e008ea4c1bbf5b57926576b2dffd8e046b65875b0a85f41f7b4489
ros-jazzy-py-trees-ros-interfaces 2.1.2-1noble.20260911.113643 7efb8737c16f719c587c45bf634a673f23eea7375c0bff74c7a0faea28238876
python3-pydot 1.4.2-2 6d212d8cce24cfea0a5c976739a3505c0de562c080c24bdd79344333d11fcbf1
python3-pyparsing 3.1.1-1 ec2395b1fe34a7a828f5cfabc4262217f6a86fb6ecb993fc18fbad3fc9edabba
LOCK
while read -r pkg ver hash; do
  grep -Fq "$pkg=$ver" /work/native/Ch13/scripts/reuse_13_7/prepare_bt_deps.sh
  grep -Fq "$hash  ${pkg}_${ver}_" /work/native/Ch13/scripts/reuse_13_7/prepare_bt_deps.sh
done < "$e/bt-exact-lock.txt"
check_index() {
  local missing=0
  while read -r pkg ver hash; do
    if apt-cache show "$pkg=$ver" 2>/dev/null | grep -Fx "SHA256: $hash"; then
      printf 'EXACT_INDEX_PASS %s %s %s\n' "$pkg" "$ver" "$hash"
    else
      printf 'EXACT_INDEX_MISSING %s %s %s\n' "$pkg" "$ver" "$hash"
      missing=1
    fi
  done < "$e/bt-exact-lock.txt"
  return "$missing"
}
apt-cache policy ros-jazzy-py-trees ros-jazzy-py-trees-ros ros-jazzy-py-trees-ros-interfaces python3-pydot python3-pyparsing > "$e/bt-apt-policy-before.txt"
# Historical Nav2 parity also requires snapshot even if BT happens to be available.
if ! check_index > "$e/bt-index-before.log" || ! apt-cache show ros-jazzy-nav2-controller 2>/dev/null | grep -E '^Version: 1\.3\.13-' > /dev/null; then
  apt-get install -y --no-install-recommends curl gnupg ca-certificates
  key=/etc/apt/keyrings/ros-snapshots-archive-keyring.gpg
  mkdir -p /etc/apt/keyrings
  curl --fail --silent --show-error --location --connect-timeout 10 --max-time 60 \
    'https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x4B63CF8FDE49746E98FA01DDAD19BAB3CBF125EA' > /tmp/t10-snapshot-key.asc
  fingerprint="$(gpg --batch --show-keys --with-colons /tmp/t10-snapshot-key.asc | awk -F: '$1=="fpr" && !found {print $10; found=1}')"
  test "$fingerprint" = 4B63CF8FDE49746E98FA01DDAD19BAB3CBF125EA
  gpg --batch --yes --dearmor -o "$key" /tmp/t10-snapshot-key.asc
  chmod 644 "$key"
  printf '%s\n' "$fingerprint" > "$e/bt-snapshot-key.txt"
  source=/etc/apt/sources.list.d/ch15-t10-snapshot.sources
  cat > "$source" <<'SOURCE'
Types: deb
URIs: http://snapshots.ros.org/jazzy/2026-10-05/ubuntu
Suites: noble
Components: main
Architectures: amd64
Signed-By: /etc/apt/keyrings/ros-snapshots-archive-keyring.gpg
SOURCE
  cat > /etc/apt/preferences.d/ch15-t10-snapshot <<'PREF'
Package: *
Pin: origin snapshots.ros.org
Pin-Priority: 1
PREF
  cp "$source" "$e/bt-snapshot-source.txt"
  apt-get -o Dir::Etc::sourcelist="$source" -o Dir::Etc::sourceparts=- \
    -o APT::Get::List-Cleanup=0 -o Acquire::Retries=1 -o Acquire::http::Timeout=20 \
    -o APT::Update::Error-Mode=any update 2>&1 | tee "$e/bt-snapshot-update.log"
fi
apt-cache policy ros-jazzy-py-trees ros-jazzy-py-trees-ros ros-jazzy-py-trees-ros-interfaces python3-pydot python3-pyparsing > "$e/bt-apt-policy.txt"
check_index | tee "$e/bt-index-final.log"
echo BT_EXACT_INDEX_PASS
