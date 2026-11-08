# WenMind AI · 文思智评

> 让每一次作文评价，都成为下一次写作成长的起点。

面向高中生、高中语文教师与系统管理员的 AI 个性化写作成长系统。
通过多 Agent 协同评价、写作知识库检索、评分证据追溯、学生申诉与教师复核、争议驱动的规则优化，
以及跨作文能力画像，构建"可解释、可质疑、可复核、可持续改进"的写作成长闭环。

**当前进度：阶段 7 —— 教师人工复核与评价规则优化已完成。**
已具备 27 张 SQLite 数据表、学生申诉工作台、教师人工复核、六类争议归因、真实复核统计、
规则建议生成、教师审批、回归测试和量规版本发布。

> **真实性边界**：当前验收使用 **Mock 规则引擎**，不冒充真实模型语义推理。
> AI 原始维度分和反馈文本始终保留，教师修改通过叠加表独立存储；教师调整只写 `final_score`。
> 统计仅来自教师确认的复核标签，申诉量不等同于模型错误率，小样本会明确提示。
> 回归测试当前只验证规则结构、维度上限和历史样本存在性，**不等于语义回归通过**。
> 本阶段已真实生成并发布 `v1.1`，`v1.0` 归档保留，新评价已改为绑定 `v1.1`。

## 快速启动（Windows 推荐）

双击项目根目录的 **`start.bat`** 即可：

1. 检查 Node.js、npm、Python 环境；
2. 首次运行时自动创建后端虚拟环境、安装后端依赖并生成 `.env`；
3. 首次运行时自动执行前端 `npm install`；
4. 分别打开 `WenMind Backend` 与 `WenMind Frontend` 两个服务窗口；
5. 等待后端健康检查和前端页面均就绪后，自动用默认浏览器打开 `http://127.0.0.1:5173/login`。

使用期间请保持两个服务窗口开启。需要停止时双击 **`stop.bat`**。
如果 8000 或 5173 端口已有服务监听，脚本会跳过重复启动，直接检查并打开页面。

## 一、技术栈

| 层级 | 技术 | 当前状态 |
|---|---|---|
| 前端 | Vue 3 + Vite + JavaScript | 已初始化 |
| UI / 状态 / 路由 | Element Plus、Pinia、Vue Router | 已接入 |
| 图表 / HTTP | ECharts、Axios | Axios 已用于健康检查；ECharts 已安装，图表在阶段 7 使用 |
| 代码规范 | ESLint 9（flat config）+ eslint-plugin-vue | 已配置 |
| 后端 | Python 3.13、FastAPI、Pydantic v2 | 已初始化 |
| ORM / 数据库 | SQLAlchemy 2.0、SQLite | 27 张表、自动建表与幂等演示数据已完成 |
| 认证与权限 | PBKDF2-SHA256、PyJWT | 注册登录、角色与资源归属校验已完成 |
| 模型接入 | OpenAI-compatible API + Mock 规则引擎 | 多 Agent 已接入，当前验收使用显式 Mock 模式 |

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
│   │   ├── components/         # 页头、待接入页、后端状态卡、工作台等通用组件
│   │   ├── config/             # 角色菜单（portal.js）与页面 API 契约（modules.js）
│   │   ├── layouts/            # DefaultLayout 公共布局、PortalLayout 三端门户布局
│   │   ├── router/             # 全部页面路由、登录守卫与角色守卫
│   │   ├── stores/             # Pinia（app 健康检查、auth 演示角色会话）
│   │   ├── styles/             # 蓝紫教育科技主题与统一卡片/表格/表单样式
│   │   ├── utils/              # 格式化工具
│   │   └── views/              # auth 登录页 + student 8 页 + teacher 8 页 + admin 6 页
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

### 数据库结构与演示账号

数据库文件默认位于 `backend/data/wenmind.db`。服务启动时自动建表并幂等写入演示数据；
也可在 `backend` 目录手动执行 `python -m app.db.init_db`。已有用户数据时不会重复插入。

| 模块 | 数据表 |
|---|---|
| 用户与班级 | `users`、`classes`、`enrollments` |
| 作文 | `essay_prompts`、`essays` |
| 评价与证据 | `evaluations`、`dimension_scores`、`feedback_items`、`agent_runs` |
| 申诉与复核 | `appeals`、`review_records` |
| 规则与版本 | `rubric_versions`、`rule_proposals` |
| 知识库 | `kb_documents`、`kb_chunks` |
| 成长与训练 | `growth_profiles`、`growth_snapshots`、`training_tasks` |

所有表均有主键和时间字段；业务外键、作文/评价状态索引、班级学生唯一约束、量规版本唯一约束、
评价维度唯一约束等已在 Model 中定义。`evaluations` 分离保存 `original_total_score` 与
`final_total_score`，为后续 AI 原始评价与教师复核双轨存储提供约束。

| 角色 | 用户名 | 初始密码 | 显示名 |
|---|---|---|---|
| 学生 | `demo_student` | `Demo@2026` | 演示学生一 |
| 学生 | `demo_student2` | `Demo@2026` | 演示学生二 |
| 学生 | `demo_student3` | `Demo@2026` | 演示学生三 |
| 教师 | `demo_teacher` | `Demo@2026` | 演示教师 |
| 管理员 | `demo_admin` | `Demo@2026` | 演示管理员 |

上述账号、演示班级、3 个作文题目和 3 篇示例作文均设置 `is_demo=true`。
密码仅用于本地演示，生产部署必须修改；数据库只保存 PBKDF2-SHA256 哈希。
公开 `/auth/register` 只能注册学生，不能自助注册教师或管理员。

### 阶段 3 业务接口

统一前缀为 `/api/v1`，除注册、登录和健康检查外均需 `Authorization: Bearer <token>`。

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/auth/register` | 注册学生账号 |
| POST | `/auth/login` | 登录并返回 JWT |
| GET | `/auth/me` | 当前用户信息 |
| GET / POST | `/essays` | 按归属分页查询 / 学生提交作文 |
| GET | `/essays/{essay_id}` | 作文详情，校验学生或授权班级归属 |
| GET / POST | `/classes` | 按角色查询 / 教师或管理员创建班级 |
| GET | `/classes/{class_id}` | 班级详情与归属校验 |
| POST | `/evaluations/{essay_id}` | 创建真实 `pending` 评价任务，防止活动任务重复创建 |
| GET | `/evaluations/{evaluation_id}` | 评价任务状态与双轨分数字段 |
| GET | `/health` | 健康检查 |

### 知识库与 RAG（阶段 4）

处理链路：`文件上传 → 格式/大小校验 → PDF/DOCX/TXT 解析 → 文本清洗 → 段落优先切片 → 向量化 → FAISS 索引 → Top-K 检索`。
原始文件保存在 `backend/data/uploads/`，索引与向量器保存在 `backend/data/vector_index/`，
文档和切片元数据保存在 SQLite。FAISS 索引通过内存序列化读写，兼容当前含中文的 Windows 路径。

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/knowledge/upload` | 管理员上传并同步完成解析、切片和索引 |
| GET | `/knowledge/documents` | 文档、解析状态、切片数量和失败原因 |
| DELETE | `/knowledge/documents/{document_id}` | 删除文档、切片并重建剩余索引 |
| POST | `/knowledge/search` | Top-K 检索，可选 `evaluation_id` 关联评价任务 |
| GET | `/knowledge/status` | 索引数量、持久化和向量化模式 |

检索结果包含 `document_id`、`document_name`、`chunk_id`、`content`、`score` 和 `metadata`，
`metadata` 中保留来源与页码或章节。`score` 是相似度分数，不是准确率或可信度百分比。

向量化模式由环境变量控制：

- `EMBEDDING_MODE=auto`：远程配置完整时使用 OpenAI-compatible Embedding，否则使用本地 TF-IDF。
- `EMBEDDING_MODE=remote`：强制远程，配置或调用失败会明确报错，不静默降级。
- `EMBEDDING_MODE=local_tfidf`：本地字符 n-gram 词汇向量 + FAISS，**明确标记为非语义检索**。
- 远程配置项：`EMBEDDING_BASE_URL`、`EMBEDDING_API_KEY`、`EMBEDDING_MODEL`，密钥只放后端 `.env`。

### 多 Agent 作文评价（阶段 5）

执行链路：`评价任务 → RAG 检索 → 审题 Agent → 内容 Agent → 结构 Agent → 语言 Agent → 综合反馈 Agent → 质量审核 Agent → 后端证据核验 → 结果入库`。
所有 Agent 输出必须通过 Pydantic Schema；真实模型输出解析或校验失败时最多重试一次。

| 能力 | 实现 |
|---|---|
| 任务状态 | `pending → processing → completed / failed`，记录开始、完成与错误信息 |
| 运行记录 | `agent_runs` 保存 Agent、模型、Prompt 版本、耗时、状态、输入摘要和结构化输出 |
| 检索记录 | `retrieval_logs` 保存查询、检索模式及 Top-K 来源 |
| 综合报告 | `evaluation_reports` 保存执行模式、总结、训练建议和质量审核 |
| 证据核验 | 精确位置通过；唯一匹配可修正；多匹配或不存在标 `unverified` |
| 评分边界 | 仅 1–5 诊断等级，无加权总分；教师复核前 `final_score` 为空 |

| 模式 | 模型与输出 | Token 用量 | 用途 |
|---|---|---|---|
| `LLM_MOCK_MODE=true` | `mock-rule-based-v1`，可解释文本规则，明确非语义推理 | `null`，不伪造 | 本地流程测试与故障降级演示 |
| `LLM_MOCK_MODE=false` | `LLM_MODEL` 指定的真实 OpenAI-compatible 模型 | 保存真实 API `usage` | 真实语义评价，仍须证据校验和教师复核 |

真实模型配置：`LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`、`LLM_TIMEOUT_SECONDS`。
`LLM_JSON_MODE=true` 可在供应商支持时启用 JSON response format；密钥只允许放在后端 `.env`。

接口新增：`GET /evaluations`、`POST /evaluations/{essay_id}`、`POST /evaluations/{evaluation_id}/execute`、
`GET /evaluations/{evaluation_id}`、`GET /evaluations/{evaluation_id}/runs`、
`GET /evaluations/{evaluation_id}/retrievals`。

### 学生端作文交互（阶段 6）

学生业务链已真实连通：`题目选择 → 草稿 → 提交 → 多 Agent 评价 → 反馈与原文证据 → 多轮追问 → 申诉 → 进度查询`。

- `GET /essays/prompts`：作文题目与写作要求。
- `POST /essays`、`PUT /essays/{essay_id}`：新建草稿、编辑草稿和正式提交；已提交作文保留评价历史。
- `GET /evaluations/{evaluation_id}`：综合报告、Agent、RAG、维度诊断值和 `feedback_items`。
- `GET/POST /evaluations/{evaluation_id}/questions`：多轮追问历史与发起追问。
- `GET/POST /appeals`、`GET /appeals/{appeal_id}`：学生提交申诉和查询进度。
- `evaluation_questions` 保存问题、回答、证据、执行模式和模型信息；`appeal_items` 保存争议评价项及证据快照。

原文高亮只使用后端已核验的位置和引用，未核验内容会标注待核验，不会插入学生原文冒充真实写作内容。
追问尊重学生的个性表达；Mock 仅作流程说明，真实语义回答需配置 LLM。

### 教师申诉复核与规则优化（阶段 7）

真实业务链：`学生申诉 → 教师查看原文/证据/AI 评价 → 人工复核 → 争议归因 → 重复争议统计
→ 生成待审核建议 → 教师审批 → testing 新版本 → 回归测试 → 发布并归档旧版本`。

**双轨保存约束**

- AI 原始维度分保存在 `dimension_scores.original_score`，反馈原文保存在 `feedback_items.content`。
- 教师最终维度分写入 `final_score`；修改/删除反馈写入 `feedback_review_changes` 叠加记录。
- 教师新增反馈与综合意见写入 `teacher_feedback_items`，复核原因、审核人和时间写入 `review_records`。
- 复核不会修改或删除 AI 原始文本，也不直接计算加权总分。

**争议归因**
六类标签由教师确认后写入 `review_issue_tags`：事实性错误、评分偏差、表达误判、评价遗漏、
建议不合理、其他。页面预归类明确标注为规则辅助（非真实模型），教师可自由修改。

**统计与规则治理**
- 统计只聚合教师确认标签，支持时间、班级、类型筛选，并提示小样本限制。
- 同一标签达到 `RULE_PROPOSAL_MIN_CASES`（默认 3）后生成待审核建议；
  `rule_proposal_details` 保存当前规则快照、典型案例、预期效果和审批信息。
- 教师通过建议后生成 `testing` 量规版本；`rubric_version_governance` 保存审批人、父版本和测试结果。
- 回归测试当前仅检查规则结构、维度上限和历史样本存在性，**不是语义重评**；
  测试通过才能发布，发布后旧版本归档，历史评价仍保留旧版本 ID，新评价绑定最新发布版本。

主要接口：`GET /teacher/appeals`、`GET /teacher/appeals/{id}`、`POST /teacher/appeals/{id}/review`、
`GET /teacher/analytics/appeal-patterns`、`GET/POST /teacher/rule-proposals`、
`POST /teacher/rule-proposals/{id}/approve|reject`、`GET /teacher/rubric-versions`、
`POST /teacher/rubric-versions/{id}/regression-test|publish`。

## 五、前端启动

```bash
cd frontend
npm install
npm run dev
```

访问 <http://localhost:5173>：

- `/`：产品首页，展示后端在线状态。
- `/system/status`：后端连接测试页，点击"重新检测"通过 Axios 调用真实后端接口。
- `/login`：演示角色登录页，选择学生、教师或管理员进入对应工作台。

角色页面路由（未选择演示角色时访问会自动跳转 `/login`，跨角色访问会回到本角色工作台）：

| 角色 | 路由 |
|---|---|
| 学生 | `/student/dashboard`、`/student/essays`、`/student/essays/new`、`/student/evaluations`、`/student/revision`、`/student/appeals`、`/student/growth`、`/student/training` |
| 教师 | `/teacher/dashboard`、`/teacher/classes`、`/teacher/assignments`、`/teacher/reviews`、`/teacher/appeals`、`/teacher/analytics`、`/teacher/disputes`、`/teacher/rubrics` |
| 管理员 | `/admin/dashboard`、`/admin/knowledge`、`/admin/agents`、`/admin/model`、`/admin/prompts`、`/admin/logs` |

除工作台中的真实后端健康状态外，上述业务页面均为明确标注的界面框架，不包含虚构业务数据。

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
| 下一阶段（成长与班级分析） | 成长画像、训练推荐、班级学情分析与跨评价统计 |
| 阶段 8 | 测试补全、部署文档、演示数据与提交打包 |