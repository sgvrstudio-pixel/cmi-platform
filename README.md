## 致谢与声明
本项目基于 [ jinz0009/cmi-platform](https://github.com/jinz0009/cmi-platform) 进行二次开发。
感谢原作者的开源贡献！
# App V2 - Project Documentation

## 🏗️ 一、核心架构分析 (Core Architecture Analysis)

本项目采用 **Streamlit + Pandas + SQLAlchemy** 技术栈，属于典型的单体脚本式架构（Monolithic Script-based Architecture），适合快速迭代和中小型业务场景。

### 1. 分层架构说明

| 层级 | 技术/组件 | 职责说明 |
|:---|:---|:---|
| **UI 交互层** | `streamlit` (`st.tabs`, `st.form`, `st.dataframe`) | 提供多标签页导航（询价查询、杂费查询、后台管理）、表单输入、表格展示与下载按钮。 |
| **业务逻辑层** | 自定义函数 (`build_*_conditions`, `t()`, `safe_rerun()`) | 动态拼接 SQL 条件、中文字段模糊匹配、多语言翻译、安全刷新页面。角色权限控制（`user["role"] == "admin"`）在此层实现。 |
| **数据访问层** | `sqlalchemy.text` + `pandas.read_sql` | 通过 SQLAlchemy 引擎执行原生 SQL，结果直接转为 DataFrame 供 Streamlit 渲染或计算。 |
| **数据存储层** | 关系型数据库（MySQL/PostgreSQL） | 核心表：`users`（用户）、`quotations`（报价单）、`misc_costs`（杂费）、`deleted_quotations`（软删除归档）。 |

### 2. 关键设计特征 (Key Design Features)

1.  **角色隔离查询**：非管理员默认按 `user["region"]` 过滤，管理员可跨地区查询。
2.  **动态 SQL 构建器**：通过 `build_normalized_contains_conditions()` 将前端输入转为安全的 `LIKE :param` 条件，避免 SQL 注入。
3.  **软删除机制**：删除报价单时先 `INSERT INTO deleted_quotations`，再 `DELETE FROM quotations`，保留审计痕迹。
4.  **状态管理**：依赖 Streamlit Session State（或 Cookie）维护登录用户信息 `user = {"username", "role", "region"}`。

---

## 🔄 二、数据流转流程 (Data Flow Process)

### 1. 流程图示意

```mermaid
graph LR
    A[用户登录] --> B{角色判断}
    B -->|admin| C[全地区/全表权限]
    B -->|user| D[仅当前 region 过滤]
    
    E[表单输入/筛选条件] --> F[动态 SQL 拼接]
    F --> G[pd.read_sql 执行查询]
    G --> H[DataFrame 返回]
    H --> I[Streamlit 表格渲染]
    H --> J[Pandas 统计计算<br>均值/极值/分组聚合]
    H --> K[openpyxl 导出 Excel]
    
    L[新增录入] --> M[SQL INSERT]
    M --> N[数据库持久化]
    N --> O[safe_rerun() 刷新 UI]
    
    P[管理员删除] --> Q[INSERT INTO deleted_quotations]
    Q --> R[DELETE FROM quotations]
    R --> S[软删除归档完成]
```

### 2. 详细流转说明

*   **认证与会话 (Auth & Session)**：
    *   用户登录成功后，`user` 字典写入 `st.session_state`。后续所有查询/录入自动携带 `username`, `role`, `region`。

*   **查询流 (Query Flow)**：
    *   前端输入 → 条件校验 → 动态构建 `WHERE` 子句（支持多字段模糊匹配）→ SQLAlchemy 执行 → Pandas 转 DataFrame → 渲染表格 + 统计指标 + 导出按钮。

*   **录入流 (Entry Flow)**：
    *   表单提交 → 参数校验 → `INSERT INTO quotations/misc_costs` → 事务提交 → 成功提示 → `safe_rerun()` 重置状态并刷新列表。

*   **管理流 (Admin Flow)**：
    *   多选 ID → 批量 `INSERT ... SELECT FROM quotations WHERE id IN (...)` 归档 → 批量删除原表数据 → 刷新。

---

## 🛠️ 三、二次开发建议 (Development Suggestions)

### ✅ 架构优化方向（推荐优先处理）

| 现状 | 优化方案 | 收益 |
|:---|:---|:---|
| UI 与逻辑强耦合 | 将 `build_*` 函数、统计逻辑抽离至 `core/queries.py`，UI 层仅负责调用 | 提升可测试性，便于后续迁移到 FastAPI/Flask |
| 同步阻塞查询 | 对大数据集查询添加分页（`LIMIT/OFFSET`）或流式加载 | 避免 Streamlit 页面卡顿或超时 |
| Session State 管理分散 | 封装 `auth.py` 统一处理登录态、过期刷新、权限校验装饰器 | 降低状态泄漏风险，支持多端并发 |
| 硬编码表名/字段 | 引入配置字典或 ORM（如 SQLAlchemy Core/SQLModel）映射 | 便于后期数据库迁移或字段重命名 |

### 🚀 功能扩展建议

1.  **权限细化**：当前仅 `admin/user` 两级，可扩展为 `region_manager`、`readonly` 等角色，配合 RBAC 中间件。
2.  **操作审计日志**：新增 `audit_logs` 表，记录 `INSERT/UPDATE/DELETE` 的 `user`, `table`, `old_value`, `new_value`, `timestamp`。
3.  **可视化看板**：利用 `st.metric` + `plotly`/`altair` 将价格统计、区域分布、项目进度转为交互式图表。
4.  **异步任务队列**：若导出 Excel 数据量 >10万行，改用 `celery` 或 `streamlit-async` 后台生成，前端轮询下载链接。
5.  **API 化封装**：将核心查询逻辑暴露为 RESTful API（FastAPI），便于对接移动端、BI 工具或第三方系统。

---

## 📦 四、推荐目录结构 (Recommended Directory Structure)

```text
app_v2/
├── core/
│   ├── db.py          # SQLAlchemy engine & session config
│   ├── queries.py     # SQL builders, stats logic
│   └── auth.py        # login, session state, role check
├── ui/
│   ├── components.py  # st_card, st_table, download_btn
│   ├── pages/         # search_quotations.py, misc_costs.py, admin.py
│   └── main.py        # streamlit entry point
├── config/
│   └── settings.yaml  # DB URL, regions, currency options
├── tests/             # unit tests for queries & auth
└── requirements.txt
```


以下是完整的本地测试步骤：

### 1. 安装必要的 Python 依赖

打开终端（或命令行），确保你使用的是 Python 3.8 或更高版本。运行以下命令安装代码中引用到的所有第三方库：

```bash
pip install streamlit pandas requests PyMuPDF SQLAlchemy psycopg2-binary openpyxl

```

*(注：这里使用 `psycopg2-binary` 是因为它是 PostgreSQL 的 Python 驱动，本地安装最方便；`openpyxl` 用于支持 Excel 的导出功能。)*

### 3. 配置数据库与环境变量

代码中依赖了 PostgreSQL 数据库以及 DeepSeek-OCR2 API。Streamlit 推荐使用 `.streamlit/secrets.toml` 文件来管理本地密钥。

在 `app_streamlit.py` 同级目录下，创建一个名为 `.streamlit` 的文件夹，并在其中创建 `secrets.toml` 文件，写入以下内容：

```toml
# .streamlit/secrets.toml

# 必填：你的 PostgreSQL 数据库连接串
# 格式：postgresql+psycopg2://用户名:密码@主机地址:端口/数据库名
DB_URL = "postgresql+psycopg2://your_user:your_password@localhost:5432/your_dbname"

# 选填：如果你想测试 PDF OCR 录入功能，请填入真实的 API 信息
DS_OCR2_API_KEY = "你的_API_KEY"
DS_OCR2_API_URL = "https://api.your-provider.com/v1/chat/completions"
DS_OCR2_MODEL = "deepseek-ocr2"

```

*如果你还没有 PostgreSQL 数据库，最快的免费测试方案是去 [Neon.tech](https://neon.tech/) 或 [Supabase](https://supabase.com/) 注册一个免费的 Serverless Postgres 数据库，然后把连接串复制到上面的 `DB_URL` 中。*

### 4. 启动应用

在终端中，进入 `app_streamlit.py` 所在的目录，运行以下命令启动服务：

```bash
streamlit run app_streamlit.py

```

终端会输出一段本地访问地址（通常是 `http://localhost:8501`），你的默认浏览器会自动打开该页面。

### 5. 使用系统

* **初始登录**：代码在连接数据库后会自动初始化表结构，并创建一个默认管理员账号。
* **用户名**：`admin`
* **密 码**：`admin`


* **切换语言**：可以在页面右上角测试系统的中英文切换功能。
* **功能测试**：登录后，你可以测试手动添加设备、添加杂费，进入“管理员后台”创建普通用户账号并分配地区，然后使用新账号登录来验证权限和地区隔离功能。

### v3 主要优化：

按 DeepSeek-OCR-2 官方方案先识别 Markdown，再本地解析表格。
同时支持 Markdown、HTML 表格及 JSON 回退。
自动过滤 Subtotal、GST、Total Payable 等非报价明细。
增加分页并发、429/5xx 重试、单页失败容错和进度显示。
自适应 PDF 渲染分辨率，不再静默截断超页文件。
更换 PDF 时自动清理旧 OCR 状态。
改进中英文表头到数据库字段的自动映射。
保留金额小数格式，避免 3,200.00 被转换成 3200.0。