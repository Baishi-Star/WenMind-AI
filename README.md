# WenMind AI · 文思智评

> 让每一次作文评价，都成为下一次写作成长的起点。

面向高中生、高中语文教师与系统管理员的 AI 个性化写作成长系统。
通过多 Agent 协同评价、写作知识库检索、评分证据追溯、学生申诉与教师复核、争议驱动的规则优化，
以及跨作文能力画像，构建"可解释、可质疑、可复核、可持续改进"的写作成长闭环。

**当前版本：v1.0.0（决赛交付）。**
已具备 35 张 SQLite 数据表、真实评价驱动的成长趋势、教师复核优先的双轨口径、
个性化训练任务与完成结果、教师班级学情分析，以及教师进入学生个人成长详情。
真实模型已完成 6 Agent 端到端评价验收；Mock 仍用于自动化测试和离线演示。

> **真实性边界**：成长趋势全部来自数据库中的真实评价点，不使用随机数；少于 3 篇明确显示“数据积累中”。
> 教师复核后的最终诊断优先于 AI 原始诊断，未复核评价标记 `ai_unreviewed`；跨量规版本时提示版本差异。
> 量规采用三维 0–20（内容 content、表达 expression、发展 development）；审题（topic）保留但不计分，
> 未计分能力不展示虚构数值。60 分制总分按量规基准校准合成（非三维简单相加），
> 校准前 `raw_total` 与校准参数随报告公开，AI 原始分与教师最终分双轨保存、互不覆盖。
> 训练建议由近期弱项规则生成，不是 AI 推荐结论；班级统计同样基于真实评价、复核和确认标签。
> 真实模型评价仍属于教学诊断参考，质量审核为 `needs_review` 时必须由教师复核，不自动成为正式分数。

## 快速启动（Windows 推荐）

双击项目根目录的 **`start.bat`** 即可：

1. 检查 Node.js、npm、Python 环境；
2. 首次运行时自动创建后端虚拟环境、安装后端依赖并生成 `.env`；
3. 首次运行时自动执行前端 `npm install`；
4. 分别打开 `WenMind Backend` 与 `WenMind Frontend` 两个服务窗口；
5. 等待后端健康检查和前端页面均就绪后，自动用默认浏览器打开产品首页 `http://127.0.0.1:5173/`；演示登录入口为 `/login`。

使用期间请保持两个服务窗口开启。需要停止时双击 **`stop.bat`**。
如果 8000 或 5173 端口已有服务监听，脚本会跳过重复启动，直接检查并打开页面。

### 统一视觉与演示路径

当前全站统一为**浅色内容主题**：页面背景、卡片、表单、按钮和图表 tooltip 均使用浅灰白、蓝紫主色与青绿色强调；
深色仅用于三角色门户共用的左侧导航栏，作为统一的导航面，不是独立页面主题。

应用启动默认页是 `/` 产品首页。`start.bat` 会打开该地址，不会直接进入登录页。
演示路径：

1. `/` 首页：展示产品定位、能力卡片和“选择演示角色”按钮。
2. 点击“选择演示角色”或顶部“演示角色登录”，进入 `/login`。
3. `/login` 将在同一页完成“角色选择 + 账号密码登录”，不存在额外的第三层登录入口页。
4. 选择学生/教师/管理员，登录成功后进入对应工作台，例如 `/teacher/dashboard`。
5. 头像菜单退出登录会清除令牌并返回 `/login`。

未登录直接访问 `/student/*`、`/teacher/*`、`/admin/*` 时，路由守卫会重定向到
`/login?redirect=原路径`；登录成功后只接受与当前服务端角色匹配的 redirect。

## 一、技术栈

| 层级 | 技术 | 当前状态 |
|---|---|---|
| 前端 | Vue 3 + Vite + JavaScript | 已初始化 |
| UI / 状态 / 路由 | Element Plus、Pinia、Vue Router | 已接入 |
| 图表 / HTTP | ECharts、Axios | Axios 已用于健康检查；ECharts 已安装，图表在阶段 7 使用 |
| 代码规范 | ESLint 9（flat config）+ eslint-plugin-vue | 已配置 |
| 后端 | Python 3.12（线上 Ubuntu 24.04）/ 3.13（本地开发）、FastAPI、Pydantic v2 | 已上线运行 |
| ORM / 数据库 | SQLAlchemy 2.0、SQLite | 35 张表、自动建表与幂等演示数据已完成 |
| 认证与权限 | PBKDF2-SHA256、PyJWT | 注册登录、角色与资源归属校验已完成 |
| 模型接入 | OpenAI-compatible API + Mock 规则引擎 | 真实 DeepSeek 6 Agent 已完成一次全链路验收；Mock 用于测试和离线演示 |

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
│   │   ├── components/         # 页头、模块说明页、后端状态卡、工作台等通用组件
│   │   ├── config/             # 角色菜单（portal.js）与页面功能说明（modules.js）
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
- Python ≥ 3.11（本地开发 3.13.4；线上 Ubuntu 24.04 使用 3.12.3）

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

| 角色 | 用户名 | 初始密码来源 | 显示名 |
|---|---|---|---|
| 学生 | `demo_student` | `DEMO_PASSWORD` | 演示学生一 |
| 学生 | `demo_student2` | `DEMO_PASSWORD` | 演示学生二 |
| 学生 | `demo_student3` | `DEMO_PASSWORD` | 演示学生三 |
| 教师 | `demo_teacher` | `DEMO_PASSWORD` | 演示教师 |
| 管理员 | `demo_admin` | `DEMO_PASSWORD` | 演示管理员 |

演示账号密码由后端 `.env` 的 `DEMO_PASSWORD` 提供，源码不再硬编码凭据。
未配置该变量时，首次初始化会生成随机演示密码并输出到后端启动日志。
当前本地开发库已按 `Demo@2026` 初始化，仅用于演示；生产部署必须重新设置并修改密码。
上述账号、演示班级、3 个作文题目和 3 篇示例作文均设置 `is_demo=true`，数据库只保存 PBKDF2-SHA256 哈希。
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

执行链路：`评价任务 → RAG 检索 → 审题 Agent → 内容 Agent → 表达 Agent → 发展 Agent → 综合反馈 Agent → 质量审核 Agent → 后端证据核验 → 结果入库`。
所有 Agent 输出必须通过 Pydantic Schema；真实模型输出解析或校验失败时最多重试一次。

| 能力 | 实现 |
|---|---|
| 任务状态 | `pending → processing → completed / failed`，记录开始、完成与错误信息 |
| 运行记录 | `agent_runs` 保存 Agent、模型、Prompt 版本、耗时、状态、输入摘要和结构化输出 |
| 检索记录 | `retrieval_logs` 保存查询、检索模式及 Top-K 来源 |
| 综合报告 | `evaluation_reports` 保存执行模式、总结、训练建议和质量审核 |
| 证据核验 | 精确位置通过；唯一匹配可修正；多匹配或不存在标 `unverified` |
| 评分边界 | 三维 0–20（内容/表达/发展）；60 分制总分按量规基准校准合成并公开 `raw_total`；教师复核前维度 `final_score` 为空 |

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
- 复核不会修改或删除 AI 原始文本；`original_score` 与 `original_total_score` 永不被覆盖。
- 教师提交复核时按同一校准规则重算并写入 `final_total_score`：维持原评价时等于 AI 原始总分，调整维度分后随之联动，双轨总分均可追溯。

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

### 成长画像、训练与班级分析（阶段 8）

成长数据来自 `evaluations`、`dimension_scores`、`appeals`、`review_records`、`feedback_items` 和训练记录：

- 有教师复核时，优先采用复核快照 `revised_score_json` 中的教师最终值。
- 无教师复核时使用 AI 原始诊断值，并明确标记“AI 未复核”。
- 每条趋势点保留 `evaluation_id`、`essay_id`、量规版本、复核状态和复核结论。
- 少于 3 篇有效评价返回 `data_accumulating`，页面显示“数据积累中”，不预测长期趋势。
- 样本跨越多个量规版本时提示版本差异，不把规则变化全部解释为能力变化。
- 内容、表达、发展输出 0–20 趋势；审题没有独立量规分值，返回 `not_scored`，不拆分或伪造数值；跨量规版本时提示口径差异。
- 成长画像是可重建缓存：`growth_profiles` 保存当前画像，`growth_snapshots` 按评价保存真实趋势快照。

个性化训练由近期有效评价的弱项规则生成，任务包含目标、推荐理由、训练内容、来源评价和完成状态。
学生提交训练结果后写入 `training_task_details.result_text`，并计入成长画像的训练完成统计。

教师班级分析接口：`GET /teacher/classes/{class_id}/analytics`，统计班级维度均值、分布、薄弱比例、
学生样本、教师确认争议、AI 反馈问题分布、申诉状态和规则化教学建议。
教师可通过班级学生列表进入 `/teacher/students/{student_id}/growth` 查看个人成长档案。

新增接口：`GET /growth/profile`、`GET /growth/history`、`GET /training/tasks`、
`POST /training/tasks/{task_id}/complete`、`GET /teacher/classes/{class_id}/analytics`。

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
| 学生 | `/student/dashboard`、`/student/essays`、`/student/essays/new`、`/student/evaluations`、`/student/appeals`、`/student/growth` |
| 教师 | `/teacher/dashboard`、`/teacher/reviews`、`/teacher/appeals`、`/teacher/analytics`、`/teacher/disputes`、`/teacher/rubrics` |
| 管理员 | `/admin/dashboard`、`/admin/knowledge`、`/admin/agents` |

工作台与核心业务页面使用真实接口数据；少数尚未接入的模块以功能说明页呈现，不展示虚构业务数据。已下线的旧入口（如 `/student/tasks`、`/teacher/classes`、`/admin/model`）会自动重定向到保留页面。

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
# 后端全量接口、业务、权限与异常测试
cd backend
./.venv/Scripts/python.exe -m pytest

# 前端代码检查、生产构建、API 契约与浏览器冒烟
cd frontend
npm run lint
npm run build
npm run test:contract
npm run test:e2e
```

`test:contract` 会读取运行中的后端 OpenAPI，比对全部前端 API 调用路径。
`test:e2e` 使用本机 Chrome/Edge 验证三角色登录退出、28 个角色路由、空白页和控制台错误，
可通过 `E2E_CHROME`、`E2E_BASE_URL`、`E2E_DEMO_PASSWORD` 覆盖默认环境。

```bash
# 写作任务链路自检：教师建任务→发布→学生可见→学生提交→教师看到提交
cd backend
./.venv/Scripts/python.exe scripts/verify_task_flow.py          # 跑完自动清理本次任务与提交
./.venv/Scripts/python.exe scripts/verify_task_flow.py --keep   # 保留验收数据
```

脚本需后端已在 `127.0.0.1:8000` 运行；演示密码取 `backend/.env` 的 `DEMO_PASSWORD`（缺省 `Demo@2026`）。
每一步输出 `PASS/FAIL` 与关键字段，任一步失败会打印后端返回体的 `HTTP 状态码 / code / message`
并在末尾输出 `SUMMARY`；默认清理本次创建的任务、提交与关联作文。

## 八、环境变量与安全约定

- 后端密钥只写入 `backend/.env`，该文件已被 `.gitignore` 忽略，**禁止提交真实密钥**。
- 前端环境变量仅存放非敏感配置，任何 `VITE_*` 变量都会进入构建产物，**严禁写入模型密钥**。
- `LLM_MOCK_MODE=true` 为默认值；切换真实调用需配置
  `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`，将 `LLM_MOCK_MODE` 置为 `false`，并重启后端。
- 推理模型建议设置 `LLM_JSON_MODE=true` 与 `LLM_MAX_TOKENS=8192`；
  Token 预算不足会导致推理阶段耗尽预算、JSON 被截断，评价会明确失败而不是伪造结果。
- 模型配置在进程启动时读取，修改 `.env` 后不热加载；切换后应检查健康检查返回 `llm.mode=remote`。
- 健康检查接口仅返回模型"配置完整度"，不返回密钥内容。

## 九、版本状态与后续方向

| 版本 | 状态 |
|---|---|
| v1.0.0（决赛交付） | 三维 0–20 评价、60 分制基准校准总分、教师复核双轨、成长画像、规则治理与部署脚本均已落地；后端 pytest 全绿、前端 lint/build 通过 |
| 后续方向 | 长期趋势建模、量规版本回归样例扩充、教师端批量复核效率优化、云端监控与告警 |

交付材料骨架见 `ppt/`、`project/`、`readme/`、`codedao_proof/` 四个目录。
## 十、云端部署

> 详细流程见 [docs/deployment.md](docs/deployment.md)。部署脚本与模板见 [deploy/](deploy/)。

- **流水线**：`WenMind-AI-CI`（CodeArts Pipeline，push 事件自动触发，`hook_id=1330536`）。
- **四阶段**：① 代码检查与构建（前端 lint/build + 后端依赖安装，华为云镜像源）→ ② 单元测试（`pytest -q`，失败即红）→ ③ 制品归档（`wenmind-frontend-<tag>.tar.gz` / `wenmind-backend-<tag>.tar.gz`，tag = git short sha，上传 OBS 不允许覆盖）→ ④ 部署与验证（幂等部署 + systemd + nginx 反代 + 健康检查断言 `"code":0`，非 0 即流水线红）。
- **部署布局**：源码位于 `/opt/wenmind-src`（线上更新执行 `git pull --ff-only`）；数据持久目录 `/opt/wenmind/data/`（SQLite 与上传文件，部署/回滚全程不覆盖）；后端由 systemd 单元 `wenmind.service` 常驻（`EnvironmentFile=/opt/wenmind/env/wenmind.env`，权限 600）；前端由 nginx `sites-enabled/wenmind.conf` 托管并反代 `/api`；回滚执行 `deploy/rollback.sh`。
- **敏感信息**：全部走 CodeArts 密文参数（私密参数），脚本只引用变量名，禁止写入库。
- **在线地址**：`http://<ECS公网IP>/`（部署后替换为实际地址；健康检查 `http://<ECS公网IP>/api/v1/health` 应返回 `{"code":0,...}`）。
## 十一、额外数据集与开源组件说明

**数据集来源**

| 数据 | 来源 | 是否入库 | 说明 |
|---|---|---|---|
| 演示账号与班级 | `backend/app/db/seed.py` 幂等初始化 | 是（本地库） | 3 名学生 + 1 名教师 + 1 名管理员、1 个演示班级、量规与示例题目 |
| 知识库文档 | 管理员通过 `/knowledge/upload` 上传（PDF/DOCX/TXT） | 是（元数据与切片） | 原始文件在 `backend/data/uploads/`，索引在 `backend/data/vector_index/` |
| 写作样例图片 | 项目根目录 `作文/`（本地私有资料） | 否 | 仅用于本地人工验收，不参与线上评测统计，已被 `.gitignore` 规则覆盖 |

**主要开源组件**

| 组件 | 版本线 | 许可 | 用途 |
|---|---|---|---|
| Vue 3 / Vite | 3.5 / 6.x | MIT | 前端框架与构建 |
| Element Plus | 2.9 | MIT | UI 组件库 |
| Pinia / Vue Router / Axios | 3.x / 4.x / 1.x | MIT | 状态、路由与 HTTP |
| ECharts | 6.x | Apache-2.0 | 成长与班级统计图表 |
| FastAPI / uvicorn | 0.1xx / 0.3x | MIT / BSD | 后端框架与 ASGI 服务 |
| SQLAlchemy / Pydantic | 2.0 / v2 | MIT | ORM 与数据校验 |
| PyJWT | 2.x | MIT | JWT 签发与校验 |
| FAISS | 1.x | MIT | 本地向量索引（非语义检索时明确标注） |

模型推理与视觉识别调用外部 OpenAI-compatible API，服务与密钥均不随仓库分发。

## 十二、码道（CodeArts Doer）在项目开发中的应用总结

本项目在开发全过程中使用华为云码道（CodeArts Doer）作为 AI 编程助手，主要应用在以下环节：

- **需求拆解与阶段计划**：把决赛交付目标拆成可验收的阶段任务与清单。
- **后端工程**：FastAPI 路由与服务分层、SQLAlchemy 模型与幂等 seed、多 Agent 编排、RAG 检索与证据核验、评分口径与校准模块。
- **前端工程**：Vue 3 门户、路由与权限守卫、Element Plus 页面与 ECharts 图表。
- **质量与验收**：pytest 用例、浏览器端到端校验脚本、接口契约比对与构建门禁。
- **部署与文档**：流水线 definition、幂等部署脚本、README 与交付材料骨架。

**责任边界**：码道的产出为代码、脚本与文档；评价分数、教师复核结论与统计结果全部来自系统真实运行数据，
不存在由助手合成的截图、控制台数据或“已验证”记录。真实使用过程材料（插件截图、控制台数据、时间线）
见 `codedao_proof/` 目录清单与占位说明，需由项目方补充实际材料。