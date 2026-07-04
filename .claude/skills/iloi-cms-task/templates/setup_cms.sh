#!/usr/bin/env bash
# Idempotent local-CMS setup for macOS arm64.  Adapted from the Uchuva
# project; see the iloi-cms-task SKILL.md for context.
#
# Usage:  TASK_DIR=/path/to/MyTask  ./setup_cms.sh
set -euo pipefail

TASK_DIR="${TASK_DIR:?TASK_DIR not set}"
TASK_NAME="$(basename "$TASK_DIR" | tr '[:upper:]' '[:lower:]')"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CMS_DIR="$ROOT/dev/_cms"
CMS_BRANCH=israeli_cms_beta

# Prereqs ---------------------------------------------------------------------
command -v brew >/dev/null || { echo "Need Homebrew"; exit 1; }
for pkg in colima docker docker-compose docker-buildx; do
  brew list "$pkg" >/dev/null 2>&1 || brew install "$pkg"
done
mkdir -p ~/.docker/cli-plugins
ln -sf /opt/homebrew/opt/docker-buildx/bin/docker-buildx ~/.docker/cli-plugins/docker-buildx

# VM + clone ------------------------------------------------------------------
colima status default >/dev/null 2>&1 || colima start --cpu 4 --memory 6 --disk 25
[ -d "$CMS_DIR" ] || git clone --depth 50 --branch "$CMS_BRANCH" https://github.com/ioi-isr/cms.git "$CMS_DIR"

# Patch Dockerfile to build isolate from source for arm64 ---------------------
if ! grep -q 'build isolate from source' "$CMS_DIR/Dockerfile"; then
  python3 - "$CMS_DIR/Dockerfile" <<'PY'
import re, sys, pathlib
p = pathlib.Path(sys.argv[1])
s = p.read_text()
patched = re.sub(
    r'RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \\\n'
    r'    --mount=type=cache,target=/var/lib/apt,sharing=locked <<EOF\n'
    r'#!/bin/bash -ex\n'
    r'    export DEBIAN_FRONTEND=noninteractive\n'
    r'    CODENAME=.*?'
    r'    sed -i .s@\^cg_root .\*@cg_root = /sys/fs/cgroup@. /etc/isolate\n'
    r'EOF',
    """RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \\\\
    --mount=type=cache,target=/var/lib/apt,sharing=locked <<EOF
#!/bin/bash -ex
    # build isolate from source so this works on arm64
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y libcap-dev libsystemd-dev pkg-config asciidoc-base
    cd /tmp && curl -L https://github.com/ioi/isolate/archive/refs/tags/v2.0.tar.gz | tar xz
    cd isolate-2.0 && make isolate && (make install-isolate || make install)
    groupadd -r isolate || true
EOF""",
    s, count=1, flags=re.DOTALL)
p.write_text(patched)
PY
fi

# Mirror task into the container's mounted source tree -----------------------
mkdir -p "$CMS_DIR/tasks"
rsync -a --delete --exclude='.git' --exclude='gen/_validator_bins' \
  --exclude='gen/generator' --exclude='gen/model' --exclude='gen/_judge_bin' \
  --exclude='_wrong_solutions' --exclude='_verify/brute' --exclude='_verify/dp_ref' \
  --exclude='dev/_cms' \
  "$TASK_DIR/" "$CMS_DIR/tasks/$TASK_NAME/"

# Build image + start stack --------------------------------------------------
cd "$CMS_DIR"
export DOCKER_BUILDKIT=1
docker compose -p "$TASK_NAME"cms -f docker/docker-compose.dev.yml build devcms
docker compose -p "$TASK_NAME"cms -f docker/docker-compose.dev.yml up -d devdb
for _ in 1 2 3 4 5 6 7 8 9 10; do
  docker compose -p "$TASK_NAME"cms -f docker/docker-compose.dev.yml \
    exec -T devdb pg_isready -h localhost >/dev/null 2>&1 && break
  sleep 1
done

# Long-lived devcms container
docker rm -f "${TASK_NAME}cms-devcms-main" 2>/dev/null || true
docker compose -p "$TASK_NAME"cms -f docker/docker-compose.dev.yml \
  run -d --service-ports --name "${TASK_NAME}cms-devcms-main" devcms sleep 86400

# Wire isolate cgroup v2 runtime ---------------------------------------------
docker exec "${TASK_NAME}cms-devcms-main" bash -c '
  sudo rm -rf /run/isolate; sudo mkdir -p /run/isolate /sys/fs/cgroup/isolate
  echo "+cpu +memory +pids +cpuset +io" | sudo tee /sys/fs/cgroup/cgroup.subtree_control >/dev/null
  echo "+cpu +memory +pids +cpuset +io" | sudo tee /sys/fs/cgroup/isolate/cgroup.subtree_control >/dev/null
  echo "/sys/fs/cgroup/isolate" | sudo tee /run/isolate/cgroup >/dev/null
'

# Init DB + import task + create admin + contest + tester user ---------------
docker exec "${TASK_NAME}cms-devcms-main" bash -c "
  set -e
  psql -h devdb -U postgres -d postgres -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='cmsdb' AND pid <> pg_backend_pid();\" >/dev/null 2>&1 || true
  dropdb -h devdb -U postgres cmsdb 2>/dev/null || true
  createdb -h devdb -U postgres cmsdb
  cmsInitDB
  cmsImportTask -L italy_yaml /home/cmsuser/src/tasks/$TASK_NAME 2>&1 | grep -E 'Found|Imported|finished|ERROR'
  cmsAddAdmin admin -p adminpass
"

docker exec -i "${TASK_NAME}cms-devcms-main" python3 - <<PY
from cms.db import SessionGen, Contest, Task, Participation, User
from cmscommon.crypto import build_password
with SessionGen() as s:
    c = Contest(name="utest", description="local",
        allowed_localizations=["he","en"], languages=["C++17 / g++"],
        token_mode="infinite", score_precision=2)
    s.add(c); s.flush()
    t = s.query(Task).filter_by(name="$TASK_NAME").one()
    t.contest_id, t.feedback_level, t.score_mode = c.id, "full", "max"
    t.token_mode, t.score_precision = "infinite", 2
    u = User(first_name="t", last_name="t", username="tester",
             password=build_password("test"), email="t@e.x")
    s.add(u); s.flush()
    s.add(Participation(contest=c, user=u)); s.commit()
    print(f"contest_id={c.id}")
PY

# Start services -------------------------------------------------------------
docker exec -d "${TASK_NAME}cms-devcms-main" bash -c 'cmsLogService 0 >/tmp/log.log 2>&1'
sleep 2
docker exec -d "${TASK_NAME}cms-devcms-main" bash -c 'cmsResourceService -a 2 >/tmp/rs.log 2>&1'

cat <<EOF

================================================================
  CMS is up and importing the task.
================================================================

Container       : ${TASK_NAME}cms-devcms-main
Contest         : utest (id=2)
Contestant UI   : http://localhost:8888  (tester / test)
Admin UI        : http://localhost:8889  (admin / adminpass)

Submit via CLI:
  docker cp my.cpp ${TASK_NAME}cms-devcms-main:/tmp/my.cpp
  docker exec ${TASK_NAME}cms-devcms-main \\
      cmsAddSubmission -c 2 -f '$TASK_NAME.%l:/tmp/my.cpp' -l 'C++17 / g++' tester $TASK_NAME

Export for upload to another CMS (admin UI button or curl):
  curl -sS -b cookies.txt http://localhost:8889/task/<id>/export -o task.zip
EOF
