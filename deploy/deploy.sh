#!/usr/bin/env bash
# WenMind AI 幂等部署脚本（在目标 ECS 上执行）
# 用法: deploy.sh <release_tag> <制品包所在目录>
# 幂等保证: 重复执行结果一致; /opt/wenmind/data 持久目录永不覆盖
# 说明: 本脚本只在目标服务器执行, 不承担构建与打包职责。
set -euo pipefail

TAG="${1:?usage: deploy.sh <release_tag> <artifact_dir>}"
SRC="${2:?usage: deploy.sh <release_tag> <artifact_dir>}"

BASE=/opt/wenmind
REL="$BASE/releases/$TAG"

mkdir -p "$BASE/releases" "$BASE/data" "$BASE/env"

# 0. 定位部署配置来源: 优先制品内 deploy/, 否则回退到脚本所在目录
DEPLOY_SRC="$SRC/deploy"
if [ ! -f "$DEPLOY_SRC/wenmind.service" ]; then
  DEPLOY_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
if [ ! -f "$DEPLOY_SRC/wenmind.service" ] || [ ! -f "$DEPLOY_SRC/nginx.conf" ]; then
  echo "DEPLOY_CONF_MISSING src=$DEPLOY_SRC"
  exit 1
fi

# 1. 解压制品（backend/{app,requirements.txt,.env.example} + frontend/dist 内容）, 并固化部署配置
rm -rf "$REL"
mkdir -p "$REL/backend" "$REL/frontend" "$REL/deploy"
tar -xzf "$SRC/wenmind-backend-$TAG.tar.gz" -C "$REL/backend"
tar -xzf "$SRC/wenmind-frontend-$TAG.tar.gz" -C "$REL/frontend"
cp -f "$DEPLOY_SRC/wenmind.service" "$DEPLOY_SRC/nginx.conf" "$REL/deploy/"

# 2. 持久数据软链: 代码内 BASE_DIR/data -> /opt/wenmind/data
#    SQLite (wenmind.db) 与上传文件 (data/submission_uploads) 均落在持久目录, 部署不覆盖
ln -sfn "$BASE/data" "$REL/backend/data"

# 3. 切换当前版本软链（原 current 保留, 回滚即切回）
ln -sfn "$REL" "$BASE/current"

# 4. 环境变量占位模板: 仅首次生成, 权限 600, 不含任何真实密钥
#    真实值由运维填写; systemd 通过 EnvironmentFile=/opt/wenmind/env/wenmind.env 读取
ENV_FILE="$BASE/env/wenmind.env"
if [ ! -f "$ENV_FILE" ]; then
  umask 077
  cat > "$ENV_FILE" <<'WENMIND_ENV_TEMPLATE'
# WenMind AI 生产环境变量（占位模板）
# 由运维填写真实值，禁止提交到仓库；systemd 通过 EnvironmentFile 读取本文件。
APP_NAME="WenMind AI"
APP_VERSION=1.0.0
APP_ENV=production
DEBUG=false
API_V1_PREFIX=/api/v1
HOST=127.0.0.1
PORT=8000
LOG_LEVEL=INFO
BACKEND_CORS_ORIGINS=
JWT_SECRET_KEY=
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=120
DEMO_PASSWORD=
DEMO_LOGIN_ENABLED=false
LLM_MOCK_MODE=false
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
LLM_TIMEOUT_SECONDS=120
LLM_JSON_MODE=true
LLM_AGENT_MAX_TOKENS=6000
LLM_AGENT_RETRY_MAX_TOKENS=12000
LLM_VISION_MAX_TOKENS=32768
LLM_VISION_TIMEOUT_SECONDS=180
EMBEDDING_MODE=auto
EMBEDDING_BASE_URL=
EMBEDDING_API_KEY=
EMBEDDING_MODEL=
OCR_ENABLED=false
OCR_BASE_URL=
OCR_API_KEY=
OCR_MODEL=
OCR_TIMEOUT_SECONDS=180
DATABASE_URL=sqlite:///./data/wenmind.db
WENMIND_ENV_TEMPLATE
fi
chmod 600 "$ENV_FILE"

# 5. 依赖安装（幂等, 华为云镜像源）
if [ ! -d "$BASE/venv" ]; then
  python3 -m venv "$BASE/venv"
fi
"$BASE/venv/bin/pip" install --upgrade pip -i https://repo.huaweicloud.com/repository/pypi/simple --quiet
"$BASE/venv/bin/pip" install -r "$REL/backend/requirements.txt" -i https://repo.huaweicloud.com/repository/pypi/simple --quiet

# 6. systemd 常驻
cp "$REL/deploy/wenmind.service" /etc/systemd/system/wenmind.service
systemctl daemon-reload
systemctl enable wenmind >/dev/null 2>&1
systemctl restart wenmind

# 7. nginx 托管前端 + /api 反代
cp "$REL/deploy/nginx.conf" /etc/nginx/conf.d/wenmind.conf
nginx -t
systemctl reload nginx

# 8. 健康检查: 断言返回包含 "code":0, 否则非 0 退出让流水线红掉
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