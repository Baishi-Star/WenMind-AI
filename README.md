# WenMind AI · 文思智评

> 让每一次作文评价，都成为下一次写作成长的起点。

面向高中生、高中语文教师与系统管理员的 AI 个性化写作成长系统。
通过多 Agent 协同评价、写作知识库检索、评分证据追溯、学生申诉与教师复核、争议驱动的规则优化，
以及跨作文能力画像，构建"可解释、可质疑、可复核、可持续改进"的写作成长闭环。

**当前进度：阶段 1 —— 工程初始化（前后端骨架 + 健康检查 + 前后端真实连通）。**
本阶段不包含登录、作文、Agent、RAG 等业务功能，将在后续阶段逐一实现。

## 一、技术栈

| 层级 | 技术 | 当前状态 |
|---|---|---|
| 前端 | Vue 3 + Vite + JavaScript | 已初始化 |
| UI / 状态 / 路由 | Element Plus、Pinia、Vue Router | 已接入 |
| 图表 / HTTP | ECharts、Axios | Axios 已用于健康检查；ECharts 已安装，图表在阶段 7 使用 |
| 代码规范 | ESLint 9（flat config）+ eslint-plugin-vue | 已配置 |
| 后端 | Python 3.13、FastAPI、Pydantic v2 | 已初始化 |
| ORM / 数据库 | SQLAlchemy 2.0、SQLite | 依赖已安装，数据模型在阶段 2 建立 |
| 模型接入 | OpenAI-compatible API 适配层 | 阶段 3 实现，当前默认 Mock 模式 |

## 二、目录结构

```text
CodeArts Agent/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── api/                # 路由聚合与各业务接口（当前：health）
│   │   ├── core/               # 配置、日志、异常、中间件
│   │   ├── models/             # SQLAlchemy 模型（阶段 2 起）
│   │   ├── schemas/            # Pydantic 模型（统一响应、健康检查）
│   │   ├── services/           # 业务服务（后续阶段）
│   │   ├── agents/             # Orchestrator 与专业 Agent（阶段 4）
│   │   ├── rag/                # 文档解析、切片、向量检索（阶段 5）
│   │   ├── db/                 # 数据库连接与初始化（阶段 2）
│   │   ├── utils/              # 通用工具
│   │   └── main.py             # 应用入口
│   ├── tests/                  # pytest 接口测试
│   ├── .env.example            # 环境变量模板（不含密钥）
│   ├── pytest.ini
│   └── requirements.txt
├── frontend/                   # Vue 3 前端
│   ├── public/favicon.svg
│   ├── src/
│   │   ├── api/                # Axios 实例与接口封装
│   │   ├── assets/             # 静态资源
│   │   ├── components/         # 通用组件（HealthPanel）
│   │   ├── layouts/            # 全局布局
│   │   ├── router/             # 路由与标题管理
│   │   ├── stores/             # Pinia（应用/健康检查状态）
│   │   ├── styles/             # 全局样式与设计变量
│   │   ├── utils/              # 格式化工具
│   │   └── views/              # 页面（student / teacher / admin 已占位）
│   ├── .env.development
│   ├── .env.example
│   ├── eslint.config.js
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── .editorconfig
├── .gitignore
└── README.md
```

## 三、环境要求

- Node.js ≥ 20（本机验证版本 v24.15.0）
- npm ≥ 10（本机验证版本 11.12.1）
- Python ≥ 3.11（本机验证版本 3.13.4）

## 四、后端启动

```bash
cd backend

# 1. 创建虚拟环境（Windows Git Bash）
python -m venv .venv
# Windows PowerShell 激活：.venv\Scripts\Activate.ps1
# Windows Git Bash 激活：source .venv/Scripts/activate
# macOS / Linux 激活：source .venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 准备环境变量（首次运行）
cp .env.example .env        # Windows CMD 使用 copy .env.example .env

# 4. 启动服务（默认 8000 端口）
uvicorn app.main:app --reload
```

启动后可访问：

- 健康检查：<http://127.0.0.1:8000/api/v1/health>
- 接口文档：<http://127.0.0.1:8000/docs>

## 五、前端启动

```bash
cd frontend
npm install
npm run dev
```

访问 <http://localhost:5173>：

- `/`：产品首页，展示后端在线状态。
- `/system/status`：后端连接测试页，点击"重新检测"通过 Axios 调用真实后端接口。

前端通过 Vite 代理将 `/api/*` 转发到 `VITE_PROXY_TARGET`（默认 `http://127.0.0.1:8000`），
开发环境无跨域问题；直接访问后端时由后端 `BACKEND_CORS_ORIGINS` 白名单控制。

## 六、统一响应结构

所有接口返回统一结构，前端 Axios 拦截器按 `code` 判定成功与失败：

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "request_id": "由中间件注入",
  "timestamp": "2026-11-06T00:00:00Z"
}
```

业务错误码：`0` 成功、`40000` 请求错误、`40100` 未认证、`40300` 无权限、
`40400` 资源不存在、`40900` 冲突、`42200` 参数校验失败、`50000` 服务器内部错误、`50300` 上游服务不可用。
HTTP 状态码与语义保持一致，异常堆栈只写入服务端日志。

## 七、测试与检查

```bash
# 后端接口测试
cd backend
pytest

# 前端代码检查与构建
cd frontend
npm run lint
npm run build
```

## 八、环境变量与安全约定

- 后端密钥只写入 `backend/.env`，该文件已被 `.gitignore` 忽略，**禁止提交真实密钥**。
- 前端环境变量仅存放非敏感配置，任何 `VITE_*` 变量都会进入构建产物，**严禁写入模型密钥**。
- `LLM_MOCK_MODE=true` 为默认值，表示尚未接入真实模型；切换真实调用前需配置
  `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`，并将 `LLM_MOCK_MODE` 置为 `false`。
- 健康检查接口仅返回模型"配置完整度"，不返回密钥内容。

## 九、后续阶段

| 阶段 | 内容 |
|---|---|
| 阶段 2 | 用户与角色模型、JWT 登录、三端布局与路由守卫、演示账号 |
| 阶段 3 | 作文提交、评价任务状态机、LLM 适配层与 Mock 模式 |
| 阶段 4 | Orchestrator 与审题/内容/结构/语言/综合/质量审核 Agent |
| 阶段 5 | 知识库上传解析、FAISS 检索与检索测试页 |
| 阶段 6 | 评价报告、原文证据校验与高亮、学生申诉、教师复核 |
| 阶段 7 | 争议统计、规则版本管理、成长画像、训练推荐、班级分析 |
| 阶段 8 | 测试补全、部署文档、演示数据与提交打包 |