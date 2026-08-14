## 致谢与声明
本项目基于 [ jinz0009/cmi-platform](https://github.com/jinz0009/cmi-platform) 进行二次开发。
感谢原作者的开源贡献！


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
