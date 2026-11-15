#!/usr/bin/env bash
# WenMind AI 幂等部署脚本（在目标 ECS 上执行）
# 用法: deploy.sh <release_tag> <制品包所在目录>
# 幂等保证: 重复执行结果一致; /opt/wenmind/data 持久目录永不覆盖
set -euo pipefail

TAG="${1:?usage: deploy.sh <release_tag> <artifact_dir>}"
SRC="${2:?usage: deploy.sh <release_tag> <artifact_dir>}"

BASE=/opt/wenmind
REL="$BASE/releases/$TAG"

mkdir -p "$BASE/releases" "$BASE/data" "$BASE/env"

# 1. 解压制品（backend/{app,requirements.txt,.env.example} + frontend/dist 内容）
rm -rf "$REL"
mkdir -p "$REL/backend" "$REL/frontend"
tar -xzf "$SRC/wenmind-backend-$TAG.tar.gz" -C "$REL/backend"
tar -xzf "$SRC/wenmind-frontend-$TAG.tar.gz" -C "$REL/frontend"

# 2. 持久数据软链: 代码内 BASE_DIR/data -> /opt/wenmind/data
#    SQLite (wenmind.db) 与上传文件 (data/submission_uploads) 均落在持久目录, 部署不覆盖
ln -sfn "$BASE/data" "$REL/backend/data"

# 3. 切换当前版本软链（原 current 保留, 回滚即切回）
ln -sfn "$REL" "$BASE/current"

# 4. 依赖安装（幂等, 华为云镜像源）
if [ ! -d "$BASE/venv" ]; then
  python3 -m venv "$BASE/venv"
fi
"$BASE/venv/bin/pip" install --upgrade pip -i https://repo.huaweicloud.com/repository/pypi/simple --quiet
"$BASE/venv/bin/pip" install -r "$REL/backend/requirements.txt" -i https://repo.huaweicloud.com/repository/pypi/simple --quiet

# 5. systemd 常驻
cp "$REL/deploy/wenmind.service" /etc/systemd/system/wenmind.service
systemctl daemon-reload
systemctl enable wenmind >/dev/null 2>&1
systemctl restart wenmind

# 6. nginx 托管前端 + /api 反代
cp "$REL/deploy/nginx.conf" /etc/nginx/conf.d/wenmind.conf
nginx -t
systemctl reload nginx

# 7. 健康检查: 断言返回包含 "code":0, 否则非 0 退出让流水线红掉
for i in $(seq 1 10); do
  if curl -fsS http://127.0.0.1:8000/api/v1/health | grep -q '"code":0'; then
    echo "HEALTH_OK tag=$TAG"
    exit 0
  fi
  sleep 3
done
echo "HEALTH_FAIL tag=$TAG"
curl -sS http://127.0.0.1:8000/api/v1/health || true
journalctl -u wenmind -n 30 --no-pager || true
exit 1