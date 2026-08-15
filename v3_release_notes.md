# CMI Quotation Platform v3.0.0 Release Notes

**发布日期：** 2026-08-15  
**发布类型：** OCR 识别链路重构与稳定性升级  
**主要组件：** `app_v2.py` / DeepSeek-OCR-2 PDF 报价单录入

## 1. 发布概述

v3.0.0 对 PDF 报价单 OCR 链路进行了系统性重构。新版不再依赖模型一次性生成复杂 JSON，而是先使用 DeepSeek-OCR-2 完成页面级文档识别，再由应用本地完成表格解析、字段映射、数据清洗和业务校验。

本次升级重点解决了实际运行中 DeepSeek-OCR-2 返回定位标记和扁平化伪 HTML 时，系统无法识别报价明细的问题，同时增强了多页 PDF、接口限流、部分页面失败、不同表格格式和 Streamlit 状态管理的可靠性。

## 2. 核心优化

### 2.1 OCR 识别架构重构

- 主识别流程调整为“PDF 页面渲染 → DeepSeek-OCR-2 文档识别 → 本地结构化解析”。
- 使用 DeepSeek-OCR-2 的 document-to-Markdown 提示方式，减少模型直接生成复杂业务 JSON 时的格式漂移。
- 仅在检测到报价表特征、但本地解析失败时，才触发结构化 JSON 回退，避免不必要的二次调用。
- 字段映射改为本地、可审计的确定性规则，不再为了字段映射额外调用模型。

### 2.2 多种模型返回格式兼容

新版可识别以下返回格式：

- 标准 Markdown pipe table。
- 标准 HTML `<table>/<tr>/<td>` 表格。
- API 直接返回的结构化 JSON。
- Markdown 代码块或夹杂说明文字的 JSON。
- DeepSeek 定位格式，例如 `table[[x1, y1, x2, y2]]`、`text[[...]]`、`sub_title[[...]]`。
- 没有 `<tr>/<td>` 行列标签、整张表被压在单个 `<table>` 文本节点内的扁平化伪 HTML。

### 2.3 扁平化报价表专用解析

- 新增 DeepSeek grounded flat-table 专用解析器。
- 能从连续文本中恢复：序号、设备描述、数量、设备单价、折扣和总金额。
- 支持带序号和不带序号两种报价明细表。
- 修复 `SPECIFICATIONSQTYUNIT` 等表头粘连导致无法检测 `QTY` 的问题。
- 修复 `44K...1380.00...` 的歧义拆分：能够正确识别为第 4 行、设备名称以 `4K` 开头、数量为 `1`、单价为 `380.00`。
- 解析成功时记录 `recognition_mode: grounded_flat_table`，便于问题追踪。

### 2.4 表格清洗和字段映射增强

- 自动识别中英文表头，并映射至现有数据库字段。
- 增强以下表头的识别：
  - `ITEM & DESCRIPTION`
  - `ITEM DESCRIPTION & TECHNICAL SPECIFICATIONS`
  - `UNIT PRICE (SGD)`
  - `UNIT (SGD)`
  - `TOTAL AMOUNT (SGD)`
  - `TOTAL (SGD)`
  - `DISC.` / `DISCOUNT`
- 自动过滤非明细行，包括：
  - Subtotal / Net Subtotal
  - GST / VAT / Tax
  - Discounts / Evaluation Waivers
  - Retail Value / Original Value
  - Total Amount Due / Total Payable / Grand Total
- 保留 `3,200.00`、`0.00` 等金额文本格式，避免 HTML 解析后变成 `3200.0`。
- 多个原始列映射到同一数据库字段时，优先保留已有非空值。
- 无法确认的值统一标记为“请核查”，保留人工复核流程。

### 2.5 PDF 页面处理优化

- 增加 PDF 文件头、空文件、无页面、加密文件校验。
- 页面按配置 DPI 渲染，并根据最大图片边长自动缩放。
- 超过最大页数时明确报错，不再静默截断后续页面。
- 保留页面编号、渲染尺寸和原生文本字符数等诊断信息。
- 默认配置：
  - DPI：220
  - 最大页数：20
  - 最大图片边长：3200 px

### 2.6 API 稳定性优化

- 多页 PDF 支持并发识别，默认并发数为 2。
- 对 HTTP 429 和 5xx 错误实施指数退避重试。
- 支持 `Retry-After` 响应头。
- 单页失败不会直接导致整份 PDF 结果丢失；成功页面仍可继续处理，并向用户显示失败页警告。
- 当所有页面均失败时，汇总并返回逐页错误原因。
- 兼容多种 OpenAI-compatible 响应结构：
  - `choices[0].message.content`
  - `choices[0].text`
  - 分段 content 数组
  - `result` / `json` / `text` / `ocr_text` / `output_text`
- 本地或无需认证的 OCR 服务可不设置 API Key；远程服务仍可使用 Bearer Token。

### 2.7 Streamlit 操作体验优化

- 增加逐页 OCR 进度显示。
- 显示已完成页数、当前完成页面和失败页面提示。
- 通过文件 SHA-256 指纹识别新上传文件。
- 更换 PDF 时自动清除上一份文件的 OCR、映射、编辑和最终导入状态，避免旧结果串入新文件。
- 重新执行同一文件 OCR 时，先清理旧的中间结果。
- 原始识别内容、页面识别模式、表格数量和警告信息保留在诊断 JSON 中。

## 3. 已修复问题

| 问题 | v3.0.0 修复结果 |
| --- | --- |
| DeepSeek 返回扁平化 `<table>` 时 `raw_tables` 为空 | 增加 grounded flat-table 专用解析器 |
| 表头粘连为 `SPECIFICATIONSQTYUNIT`，未触发回退 | 放宽表格信号检测并直接支持粘连表头 |
| 第 4 行 `4K` 被误认为序号的一部分 | 按预期序号拆分序号与产品名 |
| Subtotal、GST、Total 可能进入报价明细 | 增加汇总行识别和过滤规则 |
| HTML 数字被转换为浮点显示格式 | 优先按原始 HTML 单元格文本解析 |
| 单个页面失败导致整份 PDF 失败 | 改为页面级容错和部分成功返回 |
| 超过页数上限时静默丢弃页面 | 改为明确阻止并提示实际页数与上限 |
| API 429/5xx 临时错误直接失败 | 增加可配置的指数退避重试 |
| 更换文件后仍显示上一份 OCR 结果 | 增加文件指纹和状态自动清理 |
| 不同服务商返回结构不同导致内容提取失败 | 扩展 API 返回格式兼容逻辑 |
| 每页都要求模型直接返回复杂 JSON，稳定性不足 | 改为 Markdown 优先、本地解析、按需 JSON 回退 |

## 4. 配置项

现有配置继续有效：

```text
DS_OCR2_API_URL
DS_OCR2_API_KEY
DS_OCR2_MODEL
```

新增可选配置及默认值：

| 配置项 | 默认值 | 允许范围 | 说明 |
| --- | ---: | ---: | --- |
| `DS_OCR2_DPI` | 220 | 120-360 | PDF 页面渲染 DPI |
| `DS_OCR2_MAX_PAGES` | 20 | 1-100 | 单个 PDF 最大页数 |
| `DS_OCR2_MAX_IMAGE_SIDE` | 3200 | 1200-5000 | 渲染图片最大边长 |
| `DS_OCR2_MAX_TOKENS` | 8192 | 1024-32768 | 单次模型输出 token 上限 |
| `DS_OCR2_TIMEOUT` | 300 | 30-900 | 单次 API 超时时间，单位为秒 |
| `DS_OCR2_RETRIES` | 2 | 0-5 | 429/5xx 最大重试次数 |
| `DS_OCR2_CONCURRENCY` | 2 | 1-6 | PDF 页面并发识别数 |
| `DS_OCR2_RETRY_BACKOFF` | 1.5 | 0.2-10.0 | 指数退避基础秒数 |

错误或超范围配置会自动回落或限制在安全范围内。

## 5. 测试与验证结果

| 测试对象 | 验证结果 |
| --- | --- |
| `sample1.pdf` | 成功渲染 2 页；第一页恢复 4 条报价明细；第二页条款未误识别为报价表 |
| `sample2.pdf` | 成功渲染 1 页；侧栏布局恢复 4 条报价明细 |
| 生产日志中的扁平化 DeepSeek 响应 | 成功恢复 4 条明细，识别模式为 `grounded_flat_table` |
| `4K`/序号歧义场景 | 正确识别第 4 行及 `4K Ultra-HD...` 产品名称 |
| 汇总区域 | Subtotal、GST、Total Amount Due、Total Payable 均被排除 |
| 标准 Markdown 表格 | 通过 |
| 标准 HTML 表格 | 通过，并保持金额文本格式 |
| JSON 代码块及多种 API 响应结构 | 通过 |
| HTTP 429 重试 | 模拟测试通过 |
| JSON 回退 | 模拟测试通过 |
| Python 语法检查 | 通过 |

## 6. 部署影响

- 数据库表结构没有变化，不需要执行数据库迁移脚本。
- 原有人工字段映射、人工修改、全局信息填写、数据校验和确认入库流程保持不变。
- 原有 `DS_OCR2_API_URL`、`DS_OCR2_API_KEY`、`DS_OCR2_MODEL` 配置兼容。
- 建议部署环境包含：`requests`、`PyMuPDF`、`pandas` 和 `lxml`。
- 更新代码后需要重新部署或重启 Streamlit 应用。
- 建议部署后分别使用一份单页报价单和一份多页报价单执行冒烟测试。

## 7. 生产运行建议

- OCR 结果仍须经过人工确认后才能入库，尤其要核对设备名称、型号、单价、小数点、货期和维保期限。
- `DS_OCR2_CONCURRENCY` 应根据模型服务可用 slot 数和显存容量设置；模型服务 slot 较少时建议保持默认值 2。
- 生产环境建议关闭请求体 DEBUG 日志或对图片 Data URL 做脱敏，避免 Base64 编码的报价单页面进入长期日志。
- 如 OCR 服务频繁返回 429，可降低并发数或适当提高重试退避时间。

## 8. 已知限制

- OCR 正确率仍受原始 PDF 清晰度、字体大小、表格复杂度和模型服务版本影响。
- 扁平表专用解析器主要覆盖包含数量、单价和总金额的常见报价明细结构；非常规表格会进入 JSON 回退或要求人工处理。
- 扫描质量较差、严重倾斜、手写或多层嵌套表格仍可能需要人工修正。
- 默认最多处理 20 页；如需处理更长文件，应评估 API 成本、延迟和模型服务容量后调整配置。

## 9. 升级步骤

1. 备份当前应用代码和 Streamlit 配置。
2. 部署 v3.0.0 对应的 `app_v2.py`。
3. 检查 OCR API URL、模型名称和认证配置。
4. 确认运行环境已安装所需依赖。
5. 重启或重新部署 Streamlit 应用。
6. 使用 `sample1.pdf` 和 `sample2.pdf` 进行冒烟测试。
7. 确认原始 JSON 中第一页出现 `table_count: 1`，扁平返回场景出现 `recognition_mode: grounded_flat_table`。
8. 完成人工复核和测试库导入后，再开放生产使用。

---

**版本结论：** v3.0.0 保持现有数据库和业务录入流程不变，重点提升 DeepSeek-OCR-2 返回格式兼容性、表格恢复准确性、多页处理稳定性和生产可观测性。
