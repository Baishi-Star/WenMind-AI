# WenMind AI 云端部署文档

> 阶段 1.0.0 云端部署 · 流水线 `WenMind-AI-CI` 四阶段 · 一次提交 → 自动构建与测试 → 自动部署 → 健康检查

## 一、资源清单

| 资源 | 标识 | 说明 |
|---|---|---|
| CodeArts 项目 | `WenMind-AI`（`85e4664e5429454d870924cda02f1f55`） | region `cn-north-4` |
| 代码仓库 | CodeArts Repo `WenMind-AI`（repoId `3116975`） | 默认分支 `main`，push 事件触发（hook_id `1330536`） |
| 流水线 | `WenMind-AI-CI`（`6905fa6151f74988a755b5c1997a868f`） | 四阶段：检查构建 → 单元测试 → 制品归档 → 部署验证 |
| 代码源授权 | 服务扩展点 `wenmind-repo-auth`（CodeArts Repo HTTPS） | 绑定到流水线源后 `git clone` 才有凭据 |
| 制品归档 | OBS 桶 `wenmind-artifacts` + IAM 账户扩展点 | 制品带构建号（git short sha），不允许覆盖同名 |
| 部署目标 | ECS（用户提供 IP/SSH 凭据） | 建议走 CodeArts Deploy 主机集群托管凭据，或流水线密文变量 |
| 前端托管 | ECS 上 nginx（80 端口） | 静态 dist + SPA 回退 + `/api/` 反代 |
| 后端常驻 | systemd 服务 `wenmind` | venv + uvicorn，`127.0.0.1:8000` |
| 数据持久化 | `/opt/wenmind/data/` | `wenmind.db` 与 `submission_uploads/`，部署/回滚全程不覆盖 |

## 二、目录布局（ECS）

```
/opt/wenmind/
├── current -> releases/<tag>      # 当前版本软链，回滚即切回上一 release
├── releases/<tag>/
│   ├── backend/{app, requirements.txt, .env.example}
│   │   └── data -> /opt/wenmind/data   # 持久数据软链
│   ├── frontend/                  # 前端 dist 内容
│   └── deploy/{nginx.conf, wenmind.service}
├── data/                          # 持久：wenmind.db + submission_uploads/
├── env/wenmind.env                # 敏感环境变量（600 权限，systemd EnvironmentFile）
└── venv/                          # Python 虚拟环境（幂等复用）
```

## 三、变量清单（全部走 CodeArts 密文变量，禁止写入库）

| 变量 | 用途 | 注入位置 |
|---|---|---|
| `LLM_MOCK_MODE` | 真实模型开关（生产 `false`） | `/opt/wenmind/env/wenmind.env` |
| `LLM_BASE_URL` | 模型 API 地址 | 同上 |
| `LLM_API_KEY` | 模型 API 密钥（敏感） | 同上 |
| `LLM_MODEL` | 模型名 | 同上 |
| `SECRET_KEY` | JWT 签名密钥（敏感） | 同上 |
| `DATABASE_URL` | SQLite 持久路径 `sqlite:////opt/wenmind/data/wenmind.db` | 同上 |
| `OCR_ENABLED` | 视觉识别开关 | 同上 |
| `OCR_MODEL` | 视觉模型名 | 同上 |
| `DEPLOY_HOST` / `DEPLOY_USER` / `DEPLOY_SSH_KEY` | 部署目标主机与 SSH 私钥（敏感） | 流水线密文参数，仅阶段四引用 |

配置入口：流水线编辑页 → 参数设置 → 新建自定义参数并勾选**私密参数**；或走 CodeArts Deploy 主机集群托管 SSH 凭据。

## 四、部署流程（四阶段）

1. **阶段一 代码检查与构建**：前端 `npm ci --no-audit --no-fund` → `npm run lint` → `npm run build`（产物 `frontend/dist`）；后端 `pip install -r requirements.txt`（华为云镜像源）。
2. **阶段二 单元测试**：后端 `python -m pytest -q`（独立 SQLite，不依赖外部数据库；失败即流水线红，无 continue-on-error）。
3. **阶段三 制品归档**：打包 `wenmind-frontend-<tag>.tar.gz` 与 `wenmind-backend-<tag>.tar.gz`（tag = git short sha，可追溯；同名制品不允许覆盖）→ 上传 OBS `wenmind-artifacts`。
4. **阶段四 部署与验证**：拉取制品 → 传目标主机 → `deploy/deploy.sh <tag>`（幂等：软链切换 + data 不动 + systemd 重启 + nginx reload）→ 健康检查断言 `"code":0`，非 0 即流水线失败。

## 五、健康检查

```bash
curl -fsS http://127.0.0.1:8000/api/v1/health
# 期望: {"code":0,...}
```

- 部署脚本内循环重试 10 次 × 3s，全部失败则输出 `HEALTH_FAIL` 并附 `journalctl -u wenmind` 最近 30 行，以非 0 退出让流水线红掉。
- 外网验证：`http://<ECS公网IP>/api/v1/health`（经 nginx 反代）。

## 六、回滚步骤

```bash
# 方式一：自动回滚到上一个 release
bash /opt/wenmind/current/deploy/rollback.sh

# 方式二：回滚到指定版本
bash /opt/wenmind/current/deploy/rollback.sh <旧tag>
```

回滚只切 `current` 软链 + 重启 `wenmind` + 健康检查；`/opt/wenmind/data/` 全程不动。制品从 OBS 桉 tag 重新拉取即可复现任意历史版本。

## 七、常见错误

| 现象 | 原因 | 处理 |
|---|---|---|
| 流水线报 `DEVPIPE.00011127 服务未开通/系统繁忙` | Pipeline/Build 服务未开通，或 API 临时繁忙 | 控制台确认服务开通；偶发繁忙先换传参方式再重试，稳定复现则按内容排查（shell 值禁换行/禁内嵌双引号） |
| 「下载代码」报 `auth info is empty` | 代码源扩展点未绑定 | 流水线源节点选中 `wenmind-repo-auth` 并保存；判定以 `sources.params.endpoint_id` 非空为准 |
| 阶段二 pip 安装超时 | 执行环境走了系统代理 | 统一使用华为云镜像源 `-i https://repo.huaweicloud.com/repository/pypi/simple`；代理环境加 `--proxy ""` |
| 健康检查失败、外网不通 | 安全组未放行 22/80（及脚本内 600s 长请求被网关截断） | 安全组放行 22（流水线部署）与 80（对外服务）；nginx `proxy_read_timeout 600s` 覆盖 AI 长请求 |
| 部署后数据丢失 | data 目录被覆盖 | 检查 release 内 `backend/data` 软链是否指向 `/opt/wenmind/data`；制品打包已排除 data |
| 阶段四报 `DEPLOY_VARS_MISSING` | 部署目标密文变量未配置 | 在流水线参数设置中配置 `DEPLOY_HOST/DEPLOY_USER/DEPLOY_SSH_KEY`（私密参数） |

## 八、截图留证清单（工程实践证明）

1. 流水线四阶段全绿总览页（运行详情）
2. 阶段一构建日志关键行（npm lint/build 通过）
3. 阶段二 pytest 通过日志（passed 数量）
4. 阶段三制品归档日志（两个 tar.gz 文件名含 tag）
5. 阶段四部署日志（`HEALTH_OK tag=...`）
6. `curl /api/v1/health` 返回 `{"code":0,...}`
7. ECS 上 `systemctl status wenmind` 与 nginx 页面在线截图