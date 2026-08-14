# -*- coding: utf-8 -*-
"""
Streamlit App (Postgres / Neon version) — bilingual (CN/EN switchable)
- Keeps database schema unchanged (Chinese column names stay the same).
- User accounts are created by admin only.
- Adds website language switcher for users (中文 / English).
- Adds bilingual keyword/alias search (e.g. 海康 / hikvision / hkvision).
- Removes self-registration completely.
Run:
    streamlit run app_streamlit.py
Streamlit Cloud:
    Secrets:
        DB_URL="postgresql+psycopg2://USER:PASSWORD@HOST/DB?sslmode=require"
        DS_OCR2_API_KEY="YOUR_API_KEY"
        DS_OCR2_API_URL="https://YOUR_PROVIDER/v1/chat/completions"
        DS_OCR2_MODEL="deepseek-ocr2"
"""

import os
import re
import io
import json
import base64
import hashlib
from datetime import date

import streamlit as st
import pandas as pd
import requests
import fitz  # PyMuPDF
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool


# ==================== PAGE CONFIG ====================
st.set_page_config(page_title="CMI Quotation Input & Query Platform", layout="wide")


# ==================== THEME (Wix-like Tech Dark) ====================
THEME_CSS = """
/* Base */
:root{
  --bg0: #070A12;
  --bg1: #0B1020;
  --card: rgba(255,255,255,0.06);
  --card2: rgba(255,255,255,0.08);
  --line: rgba(255,255,255,0.12);
  --text: rgba(255,255,255,0.92);
  --muted: rgba(255,255,255,0.64);
  --muted2: rgba(255,255,255,0.52);
  --brand: #5B8CFF;
  --brand2:#7C4DFF;
  --good:#35D07F;
  --warn:#FFB020;
  --bad:#FF5A65;
  --shadow: 0 12px 40px rgba(0,0,0,0.45);
  --r: 18px;
}

html, body, [data-testid="stAppViewContainer"]{
  background: radial-gradient(1100px 700px at 10% 10%, rgba(124,77,255,0.18), transparent 60%),
              radial-gradient(900px 600px at 80% 20%, rgba(91,140,255,0.20), transparent 55%),
              linear-gradient(180deg, var(--bg0) 0%, var(--bg1) 100%) !important;
  color: var(--text) !important;
}

[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stToolbar"] { right: 1rem; }

.block-container{
  padding-top: 1.2rem !important;
  padding-bottom: 2.2rem !important;
}

[data-testid="stSidebar"]{
  background: rgba(255,255,255,0.03) !important;
  border-right: 1px solid var(--line) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }

h1,h2,h3 { letter-spacing: 0.2px; }
h1 { font-size: 2.0rem !important; }
h2 { font-size: 1.35rem !important; }
p, label, .stCaption { color: var(--muted) !important; }

.stButton > button, .stDownloadButton > button{
  border-radius: 999px !important;
  border: 1px solid rgba(255,255,255,0.14) !important;
  background: linear-gradient(90deg, rgba(91,140,255,0.30), rgba(124,77,255,0.22)) !important;
  color: var(--text) !important;
  box-shadow: 0 10px 26px rgba(0,0,0,0.35);
  padding: 0.55rem 0.95rem !important;
}
.stButton > button:hover, .stDownloadButton > button:hover{
  transform: translateY(-1px);
  border-color: rgba(255,255,255,0.25) !important;
  filter: brightness(1.05);
}
.stButton > button:active, .stDownloadButton > button:active{
  transform: translateY(0px);
  filter: brightness(0.98);
}

[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stTextArea"] textarea{
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid rgba(255,255,255,0.14) !important;
  border-radius: 12px !important;
  color: var(--text) !important;
}
[data-testid="stSelectbox"] div[role="combobox"]{
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid rgba(255,255,255,0.14) !important;
  border-radius: 12px !important;
  color: var(--text) !important;
}

.stTabs [data-baseweb="tab-list"]{
  gap: 0.35rem !important;
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid rgba(255,255,255,0.10) !important;
  padding: 0.35rem !important;
  border-radius: 999px !important;
}
.stTabs [data-baseweb="tab"]{
  background: transparent !important;
  border-radius: 999px !important;
  color: var(--muted) !important;
  border: 1px solid transparent !important;
  padding: 0.5rem 0.9rem !important;
}
.stTabs [aria-selected="true"]{
  background: rgba(255,255,255,0.08) !important;
  color: var(--text) !important;
  border: 1px solid rgba(255,255,255,0.16) !important;
}

[data-testid="stDataFrame"]{
  border-radius: var(--r) !important;
  overflow: hidden !important;
  border: 1px solid rgba(255,255,255,0.10) !important;
  box-shadow: 0 8px 22px rgba(0,0,0,0.35);
}
[data-testid="stDataFrame"] *{
  color: rgba(255,255,255,0.88) !important;
}

.stAlert{
  border-radius: var(--r) !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  background: rgba(255,255,255,0.06) !important;
}

.card{
  background: var(--card);
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: var(--r);
  box-shadow: var(--shadow);
  padding: 1.0rem 1.05rem;
}
.card .title{
  font-weight: 700;
  color: var(--text);
  font-size: 1.05rem;
}
.card .sub{
  color: var(--muted);
  margin-top: 0.15rem;
  font-size: 0.92rem;
}

.hr{
  height: 1px;
  background: rgba(255,255,255,0.10);
  margin: 0.8rem 0 1.0rem 0;
}

[data-testid="collapsedControl"]{
  color: rgba(255,255,255,0.7) !important;
}


/* ==================== Hide Streamlit / GitHub / Deploy Icons ==================== */

/* Hide top-right toolbar container */
[data-testid="stToolbar"] {
  display: none !important;
  visibility: hidden !important;
  opacity: 0 !important;
  pointer-events: none !important;
}

/* Hide Streamlit main menu */
#MainMenu {
  display: none !important;
  visibility: hidden !important;
}

/* Hide footer */
footer {
  display: none !important;
  visibility: hidden !important;
}

/* Hide header action buttons, including GitHub / deploy / overflow icons */
header [data-testid="stToolbar"],
header [data-testid="stDecoration"],
header [data-testid="stStatusWidget"],
header button,
header a {
  display: none !important;
  visibility: hidden !important;
  opacity: 0 !important;
  pointer-events: none !important;
}

/* Hide GitHub-related links/icons if rendered as anchors */
a[href*="github"],
a[href*="GitHub"],
a[aria-label*="GitHub"],
a[title*="GitHub"] {
  display: none !important;
  visibility: hidden !important;
  opacity: 0 !important;
  pointer-events: none !important;
}

/* Hide Streamlit deploy/share/menu related buttons */
button[title*="Deploy"],
button[aria-label*="Deploy"],
button[title*="Share"],
button[aria-label*="Share"],
button[title*="GitHub"],
button[aria-label*="GitHub"],
button[kind="header"] {
  display: none !important;
  visibility: hidden !important;
  opacity: 0 !important;
  pointer-events: none !important;
}

/* Reduce header height after hiding toolbar */
[data-testid="stHeader"] {
  height: 0rem !important;
  min-height: 0rem !important;
  background: transparent !important;
}

/* Avoid blank space at the top */
.block-container {
  padding-top: 1rem !important;
}


"""
st.markdown(f"<style>{THEME_CSS}</style>", unsafe_allow_html=True)


# ==================== I18N ====================
LANG_OPTIONS = {
    "中文": "zh",
    "English": "en"
}

I18N = {
    "zh": {
        "app_title": "CMI 询价录入与查询平台",
        "app_subtitle": "High Tech • Effective Solution • Quick Use",
        "lang_label": "语言",
        "help_title": "使用说明",
        "help_text": "• 普通用户账号由管理员统一创建与分配<br/>• 登录后可批量导入询价记录 / 查询 / 下载结果<br/>• 管理员可创建账号、删除记录、管理用户",
        "login_system": "登录系统",
        "login_sub": "使用你的账号进入询价录入与查询平台",
        "username": "用户名",
        "password": "密码",
        "login_btn": "登录",
        "enter_user_pass": "请输入用户名和密码",
        "wrong_user_pass": "用户名或密码错误",
        "current_user": "当前用户",
        "logout": "退出登录",
        "page_input": "🏠 录入页面",
        "page_device_query": "📋 设备查询",
        "page_misc_query": "💰 杂费查询",
        "page_admin": "👑 管理员后台",
        "input_center": "录入中心",
        "input_center_sub": "支持 Excel 批量录入 + 手工录入（设备 / 杂费）",
        "excel_bulk": "📂 Excel 批量录入",
        "excel_caption": "系统会尝试识别上传文件的表头并给出建议映射。",
        "download_template": "下载模板",
        "upload_excel": "上传 Excel (.xlsx)",
        "preview_fail": "读取预览失败：{}",
        "raw_headers_detected": "检测到的原始表头（用于映射，系统已尝试自动对应一版建议）：",
        "mapping_suggested": "系统已为每一列生成建议映射（你可以直接应用，或修改后提交）。",
        "source_col": "源列: {}",
        "ignore": "Ignore",
        "apply_mapping_preview": "应用映射并预览",
        "mapping_saved": "映射已保存。现在请填写全局必填信息并导入。",
        "mapping_restore_fail": "恢复映射数据失败：{}",
        "mapped_preview": "映射后预览（前 10 行）：",
        "mapping_unavailable": "映射数据无法预览，请重新映射。",
        "open_global_form": "➡️ 填写/查看全局信息并应用导入",
        "global_hint": "若需要对空值统一填充（币种/项目/供应商/询价人），请展开并填写全局信息。",
        "global_info": "#### 全局信息（仅填充空值）",
        "project_name": "项目名称",
        "supplier_name": "供应商名称",
        "enquirer": "询价人",
        "inq_date": "询价日期",
        "currency_fill": "币种（用于填充空值）",
        "apply_global_check": "应用全局并继续校验",
        "global_required": "必须填写：项目名称、供应商名称、询价人和询价日期",
        "global_currency_required": "由于源数据存在空的币种，请选择币种以继续。",
        "global_applied": "已应用全局信息，正在进行总体必填校验...",
        "mapping_lost": "映射数据丢失，无法继续导入。",
        "imported_valid": "✅ 已导入 {} 条有效记录。",
        "import_valid_fail": "导入有效记录时发生错误：{}",
        "no_valid_records": "没有找到满足总体必填条件的记录可导入。",
        "invalid_rows_warn": "以下 {} 条记录缺少总体必填字段，未被导入，请修正后重新导入：",
        "download_invalid": "📥 下载未通过记录（用于修正）",
        "manual_device": "✏️ 手工录入设备",
        "material_name": "设备材料名称",
        "brand_optional": "品牌（可选）",
        "qty_confirm": "数量确认",
        "device_unit_price": "设备单价",
        "labor_unit_price": "人工包干单价",
        "currency": "币种",
        "description": "描述",
        "manual_add_btn": "添加记录（手动）",
        "manual_required": "必填项不能为空：项目名称、供应商名称、询价人、设备材料名称",
        "manual_price_required": "请至少填写 设备单价 或 人工包干单价（两者至少填一项，且大于0）。",
        "manual_add_success": "✅ 手工记录已添加",
        "manual_add_fail": "添加记录失败：{}",
        "manual_misc": "💰 手工录入杂费",
        "misc_category": "杂费类目（例如运输/安装/税费）",
        "amount": "金额",
        "remark_optional": "备注（可选）",
        "occ_date": "发生日期",
        "add_misc_btn": "添加杂费记录",
        "misc_required": "请填写项目名称、杂费类目和金额",
        "misc_add_success": "✅ 杂费记录已添加",
        "misc_add_fail": "添加杂费记录失败：{}",
        "device_query_title": "设备查询",
        "device_query_sub": "按关键词 / 项目 / 供应商 / 品牌 / 地区筛选，并支持导出 Excel",
        "keyword_multi": "关键词（多个空格分词）",
        "search_fields": "搜索字段（留空为默认）",
        "filter_project": "按项目名称过滤",
        "filter_supplier": "按供应商名称过滤",
        "filter_brand": "按品牌过滤",
        "all": "全部",
        "filter_region_admin": "按地区过滤（管理员）",
        "only_region_data": "仅显示您所在地区的数据：{}",
        "search_device_btn": "🔍 搜索设备",
        "query_fail": "查询失败：{}",
        "no_records": "未找到符合条件的记录。",
        "download_result": "下载结果",
        "price_stats": "### 当前查询 — 价格统计概览（基于返回记录）",
        "device_avg": "设备单价 — 均价",
        "device_min": "设备单价 — 最低价",
        "labor_avg": "人工包干单价 — 均价",
        "labor_min": "人工包干单价 — 最低价",
        "device_min_rows": "#### 设备单价 — 历史最低价对应记录（可能多条并列）",
        "labor_min_rows": "#### 人工包干单价 — 历史最低价对应记录（可能多条并列）",
        "group_by_name": "#### 按设备名称分组 — 均价 / 最低价",
        "stats_fail": "计算价格统计时发生异常：{}",
        "search_alias_caption": "支持中英文关键词、品牌别名和常见缩写搜索，例如：海康 / hikvision / hkvision",
        "admin_delete_title": "### ⚠️ 管理员删除（按 id 删除）",
        "admin_select_delete": "选中要删除的记录",
        "admin_confirm_delete": "我确认删除所选记录（不可恢复）",
        "admin_delete_btn": "删除所选记录（管理员）",
        "select_delete_first": "请先选择要删除的记录。",
        "confirm_delete_first": "请勾选确认框以执行删除。",
        "parse_id_fail": "解析所选 id 失败：{}",
        "invalid_id_cancel": "无有效 id，取消删除。",
        "delete_archive_success": "✅ 已删除并归档所选记录。",
        "delete_archive_fail": "删除/归档失败：{}",
        "only_admin_delete": "仅管理员可删除记录。",
        "misc_query_title": "杂费查询",
        "misc_query_sub": "按项目名称检索杂费记录，支持导出 Excel",
        "search_misc_btn": "🔍 搜索杂费",
        "download_misc": "下载杂费结果",
        "admin_panel": "管理员后台",
        "admin_panel_sub": "用户管理：创建 / 查看 / 修改地区 / 删除账号（保护当前用户与默认 admin）",
        "admin_user_mgmt": "👑 管理员后台 — 用户管理",
        "update_region_title": "🛠️ 修改用户地区（Region）",
        "select_user_update": "选择要修改的用户",
        "new_region": "新地区",
        "confirm_update_region": "我确认要修改该用户地区",
        "update_region_btn": "更新地区",
        "user_not_found": "未找到该用户，请刷新页面。",
        "default_admin_warn": "系统默认 admin 不建议修改地区。",
        "confirm_update_first": "请勾选确认框后再更新。",
        "update_region_success": "✅ 已更新用户 {} 的地区为：{}",
        "update_fail": "更新失败：{}",
        "delete_user_title": "🗑️ 删除用户账号",
        "delete_user_caption": "说明：删除账号不会自动删除该用户已录入的报价/杂费数据（数据仍保留在 quotations / misc_costs 表中）。",
        "no_deletable_user": "当前没有可删除的用户（已保护当前登录用户与默认 admin）。",
        "select_delete_user": "选择要删除的用户（可多选）",
        "confirm_delete_user": "我确认删除所选用户（不可恢复）",
        "delete_user_btn": "删除用户",
        "protected_user_error": "所选用户包含受保护账号（当前登录用户或默认 admin），已拒绝删除。",
        "delete_user_success": "✅ 已删除 {} 个用户账号",
        "db_missing": "缺少数据库连接：请在 Streamlit Secrets 或环境变量中设置 DB_URL。",
        "admin_create_user_title": "➕ 新增用户账号",
        "admin_create_user_sub": "普通用户账号由管理员统一创建并分配地区",
        "admin_create_username": "用户名",
        "admin_create_password": "密码",
        "admin_create_region": "地区",
        "admin_create_confirm": "我确认新增该用户账号",
        "admin_create_btn": "创建用户",
        "admin_create_success": "✅ 已创建用户 {}，地区为：{}",
        "admin_create_fail": "创建用户失败：用户名已存在或数据库异常",
        "admin_create_confirm_first": "请勾选确认框后再创建用户",
        "empty_user_pass": "用户名和密码不能为空",
    },
    "en": {
        "app_title": "CMI Quotation Input & Query Platform",
        "app_subtitle": "High Tech • Effective Solution • Quick Use",
        "lang_label": "Language",
        "help_title": "Instructions",
        "help_text": "• Normal user accounts are created and assigned by admin only<br/>• After login, you can batch import quotation records / search / download results<br/>• Admins can create accounts, delete records, and manage users",
        "login_system": "Login",
        "login_sub": "Use your account to access the quotation input and query platform",
        "username": "Username",
        "password": "Password",
        "login_btn": "Login",
        "enter_user_pass": "Please enter username and password",
        "wrong_user_pass": "Incorrect username or password",
        "current_user": "Current User",
        "logout": "Logout",
        "page_input": "🏠 Input",
        "page_device_query": "📋 Device Query",
        "page_misc_query": "💰 Misc Query",
        "page_admin": "👑 Admin Panel",
        "input_center": "Input Center",
        "input_center_sub": "Supports Excel batch import + manual input (devices / miscellaneous costs)",
        "excel_bulk": "📂 Excel Batch Import",
        "excel_caption": "The system will try to detect the headers in the uploaded file and suggest mappings.",
        "download_template": "Download Template",
        "upload_excel": "Upload Excel (.xlsx)",
        "preview_fail": "Failed to read preview: {}",
        "raw_headers_detected": "Detected raw headers (for mapping; the system has already suggested a first-round mapping):",
        "mapping_suggested": "Suggested mappings have been generated for each column. You may apply them directly or adjust them before submitting.",
        "source_col": "Source Column: {}",
        "ignore": "Ignore",
        "apply_mapping_preview": "Apply Mapping and Preview",
        "mapping_saved": "Mapping has been saved. Please fill in the required global information and then import.",
        "mapping_restore_fail": "Failed to restore mapped data: {}",
        "mapped_preview": "Mapped Preview (first 10 rows):",
        "mapping_unavailable": "Mapped data cannot be previewed. Please remap it.",
        "open_global_form": "➡️ Fill / View Global Information and Import",
        "global_hint": "If you need to fill blank values in batch (currency/project/supplier/enquirer), please expand and complete the global information.",
        "global_info": "#### Global Information (fill blank values only)",
        "project_name": "Project Name",
        "supplier_name": "Supplier Name",
        "enquirer": "Enquirer",
        "inq_date": "Enquiry Date",
        "currency_fill": "Currency (used to fill blank values)",
        "apply_global_check": "Apply Global Info and Continue Validation",
        "global_required": "Required: Project Name, Supplier Name, Enquirer, and Enquiry Date",
        "global_currency_required": "Some source rows have empty currency values. Please select a currency to continue.",
        "global_applied": "Global information applied. Running overall required-field validation...",
        "mapping_lost": "Mapped data is missing and cannot continue import.",
        "imported_valid": "✅ Imported {} valid records.",
        "import_valid_fail": "Error while importing valid records: {}",
        "no_valid_records": "No records meeting the overall required conditions were found for import.",
        "invalid_rows_warn": "The following {} rows are missing required fields and were not imported. Please correct them and re-import:",
        "download_invalid": "📥 Download Invalid Rows (for correction)",
        "manual_device": "✏️ Manual Device Input",
        "material_name": "Device / Material Name",
        "brand_optional": "Brand (optional)",
        "qty_confirm": "Confirmed Quantity",
        "device_unit_price": "Device Unit Price",
        "labor_unit_price": "Labor Lump-Sum Unit Price",
        "currency": "Currency",
        "description": "Description",
        "manual_add_btn": "Add Record (Manual)",
        "manual_required": "Required fields cannot be empty: Project Name, Supplier Name, Enquirer, Device / Material Name",
        "manual_price_required": "Please enter at least one of Device Unit Price or Labor Lump-Sum Unit Price, and it must be greater than 0.",
        "manual_add_success": "✅ Manual record added",
        "manual_add_fail": "Failed to add record: {}",
        "manual_misc": "💰 Manual Miscellaneous Cost Input",
        "misc_category": "Miscellaneous Cost Category (e.g. transport / installation / tax)",
        "amount": "Amount",
        "remark_optional": "Remark (optional)",
        "occ_date": "Occurrence Date",
        "add_misc_btn": "Add Misc Cost Record",
        "misc_required": "Please fill in Project Name, Miscellaneous Cost Category, and Amount",
        "misc_add_success": "✅ Miscellaneous cost record added",
        "misc_add_fail": "Failed to add miscellaneous cost record: {}",
        "device_query_title": "Device Query",
        "device_query_sub": "Filter by keyword / project / supplier / brand / region, with Excel export support",
        "keyword_multi": "Keyword(s) (split by spaces)",
        "search_fields": "Search Fields (leave blank for default)",
        "filter_project": "Filter by Project Name",
        "filter_supplier": "Filter by Supplier Name",
        "filter_brand": "Filter by Brand",
        "all": "All",
        "filter_region_admin": "Filter by Region (Admin)",
        "only_region_data": "Only data from your region is shown: {}",
        "search_device_btn": "🔍 Search Devices",
        "query_fail": "Query failed: {}",
        "no_records": "No matching records found.",
        "download_result": "Download Results",
        "price_stats": "### Current Query — Price Statistics Overview (based on returned records)",
        "device_avg": "Device Unit Price — Average",
        "device_min": "Device Unit Price — Minimum",
        "labor_avg": "Labor Lump-Sum Unit Price — Average",
        "labor_min": "Labor Lump-Sum Unit Price — Minimum",
        "device_min_rows": "#### Device Unit Price — Records corresponding to the historical minimum price (ties possible)",
        "labor_min_rows": "#### Labor Lump-Sum Unit Price — Records corresponding to the historical minimum price (ties possible)",
        "group_by_name": "#### Grouped by Device Name — Average / Minimum",
        "stats_fail": "Exception occurred while calculating price statistics: {}",
        "search_alias_caption": "Supports Chinese/English keywords, brand aliases, and common abbreviations, e.g. 海康 / hikvision / hkvision",
        "admin_delete_title": "### ⚠️ Admin Delete (delete by id)",
        "admin_select_delete": "Select records to delete",
        "admin_confirm_delete": "I confirm deletion of the selected records (cannot be undone)",
        "admin_delete_btn": "Delete Selected Records (Admin)",
        "select_delete_first": "Please select records to delete first.",
        "confirm_delete_first": "Please tick the confirmation checkbox before deleting.",
        "parse_id_fail": "Failed to parse selected id(s): {}",
        "invalid_id_cancel": "No valid id found. Deletion cancelled.",
        "delete_archive_success": "✅ Selected records have been deleted and archived.",
        "delete_archive_fail": "Delete / archive failed: {}",
        "only_admin_delete": "Only admins can delete records.",
        "misc_query_title": "Miscellaneous Cost Query",
        "misc_query_sub": "Search miscellaneous cost records by project name, with Excel export support",
        "search_misc_btn": "🔍 Search Misc Costs",
        "download_misc": "Download Misc Results",
        "admin_panel": "Admin Panel",
        "admin_panel_sub": "User management: create / view / update region / delete accounts (protect current user and default admin)",
        "admin_user_mgmt": "👑 Admin Panel — User Management",
        "update_region_title": "🛠️ Update User Region",
        "select_user_update": "Select user to update",
        "new_region": "New Region",
        "confirm_update_region": "I confirm updating this user's region",
        "update_region_btn": "Update Region",
        "user_not_found": "User not found. Please refresh the page.",
        "default_admin_warn": "It is not recommended to modify the region of the default admin.",
        "confirm_update_first": "Please tick the confirmation checkbox before updating.",
        "update_region_success": "✅ Updated user {} region to: {}",
        "update_fail": "Update failed: {}",
        "delete_user_title": "🗑️ Delete User Account",
        "delete_user_caption": "Note: deleting an account will not automatically delete the quotation / miscellaneous cost data entered by that user. The data remains in the quotations / misc_costs tables.",
        "no_deletable_user": "There are currently no deletable users (current logged-in user and default admin are protected).",
        "select_delete_user": "Select user(s) to delete (multiple selection allowed)",
        "confirm_delete_user": "I confirm deleting the selected user(s) (cannot be undone)",
        "delete_user_btn": "Delete User(s)",
        "protected_user_error": "The selected users contain protected accounts (current logged-in user or default admin). Deletion rejected.",
        "delete_user_success": "✅ Deleted {} user account(s)",
        "db_missing": "Database connection is missing. Please set DB_URL in Streamlit Secrets or environment variables.",
        "admin_create_user_title": "➕ Create User Account",
        "admin_create_user_sub": "Normal user accounts are created by admin and assigned to a region",
        "admin_create_username": "Username",
        "admin_create_password": "Password",
        "admin_create_region": "Region",
        "admin_create_confirm": "I confirm creating this user account",
        "admin_create_btn": "Create User",
        "admin_create_success": "✅ User {} has been created with region: {}",
        "admin_create_fail": "Failed to create user: username already exists or database error",
        "admin_create_confirm_first": "Please tick the confirmation checkbox before creating the user",
        "empty_user_pass": "Username and password cannot be empty",
    }
}


if "lang" not in st.session_state:
    st.session_state["lang"] = "en"


def t(key: str) -> str:
    lang = st.session_state.get("lang", "en")
    return I18N.get(lang, I18N["en"]).get(key, key)


def set_language_widget(key_name: str):
    reverse_map = {v: k for k, v in LANG_OPTIONS.items()}
    current_display = reverse_map.get(st.session_state.get("lang", "en"), "English")
    selected = st.selectbox(
        t("lang_label"),
        options=list(LANG_OPTIONS.keys()),
        index=list(LANG_OPTIONS.keys()).index(current_display),
        key=key_name
    )
    st.session_state["lang"] = LANG_OPTIONS[selected]


def ui_card(title: str, subtitle: str = ""):
    st.markdown(
        f"""
        <div class="card">
          <div class="title">{title}</div>
          {"<div class='sub'>"+subtitle+"</div>" if subtitle else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


def ui_hr():
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)


def safe_rerun():
    try:
        st.rerun()
    except Exception:
        pass


# ==================== DB ====================
DB_URL = None
try:
    DB_URL = st.secrets.get("DB_URL", None)
except Exception:
    DB_URL = None
if not DB_URL:
    DB_URL = os.getenv("DB_URL")

if not DB_URL:
    st.error(t("db_missing"))
    st.stop()

engine = create_engine(DB_URL, pool_pre_ping=True, poolclass=NullPool)


def get_secret_or_env(name: str, default=None):
    value = None
    try:
        value = st.secrets.get(name, None)
    except Exception:
        value = None
    if value is None:
        value = os.getenv(name, default)
    return value


DS_OCR2_API_KEY = get_secret_or_env("DS_OCR2_API_KEY")
DS_OCR2_API_URL = get_secret_or_env("DS_OCR2_API_URL")
DS_OCR2_MODEL = get_secret_or_env("DS_OCR2_MODEL", "deepseek-ocr2")


# ==================== INIT DB ====================
with engine.begin() as conn:
    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT CHECK(role IN ('admin','user')),
        region TEXT
    )
    """))

    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS quotations (
        id SERIAL PRIMARY KEY,
        设备材料名称 TEXT NOT NULL,
        规格或型号 TEXT,
        品牌 TEXT,
        设备单价 DOUBLE PRECISION,
        人工包干单价 DOUBLE PRECISION,
        综合单价汇总 DOUBLE PRECISION,
        币种 TEXT,
        原厂品牌维保期限 TEXT,
        货期 TEXT,
        备注 TEXT,
        询价人 TEXT,
        项目名称 TEXT,
        供应商名称 TEXT,
        询价日期 TEXT,
        地区 TEXT
    )
    """))

    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS misc_costs (
        id SERIAL PRIMARY KEY,
        项目名称 TEXT,
        杂费类目 TEXT,
        金额 DOUBLE PRECISION,
        币种 TEXT,
        录入人 TEXT,
        地区 TEXT,
        发生日期 TEXT
    )
    """))

    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS deleted_quotations (
        id SERIAL PRIMARY KEY,
        original_id INTEGER,
        设备材料名称 TEXT,
        规格或型号 TEXT,
        品牌 TEXT,
        设备单价 DOUBLE PRECISION,
        人工包干单价 DOUBLE PRECISION,
        综合单价汇总 DOUBLE PRECISION,
        币种 TEXT,
        原厂品牌维保期限 TEXT,
        货期 TEXT,
        备注 TEXT,
        询价人 TEXT,
        项目名称 TEXT,
        供应商名称 TEXT,
        询价日期 TEXT,
        地区 TEXT,
        deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        deleted_by TEXT
    )
    """))

    conn.execute(text("""
    INSERT INTO users (username, password, role, region)
    VALUES ('admin', :pw, 'admin', 'All')
    ON CONFLICT (username) DO NOTHING
    """), {"pw": hashlib.sha256("admin".encode()).hexdigest()})


# ==================== HELPERS ====================
HEADER_SYNONYMS = {
    "序号": "序号", "no": "序号", "index": "序号",
    "设备材料名称": "设备材料名称", "设备名称": "设备材料名称", "material": "设备材料名称", "name": "设备材料名称",
    "规格或型号": "规格或型号", "规格": "规格或型号", "model": "规格或型号", "spec": "规格或型号",
    "描述": "描述", "description": "描述",
    "品牌": "品牌", "brand": "品牌",
    "单位": "单位", "unit": "单位",
    "数量确认": "数量确认", "数量": "数量确认", "qty": "数量确认", "quantity": "数量确认",
    "报价品牌": "报价品牌", "报价": "报价品牌",
    "型号": "型号",
    "设备单价": "设备单价", "单价": "设备单价", "price": "设备单价",
    "设备小计": "设备小计", "subtotal": "设备小计",
    "币种": "币种", "currency": "币种",
    "询价人": "询价人", "项目名称": "项目名称", "供应商名称": "供应商名称",
    "询价日期": "询价日期", "录入人": "录入人", "地区": "地区"
}

DB_COLUMNS = [
    "设备材料名称", "规格或型号", "品牌",
    "设备单价", "人工包干单价", "综合单价汇总", "币种",
    "原厂品牌维保期限", "货期", "备注",
    "询价人", "项目名称", "供应商名称", "询价日期", "地区"
]

NUMERIC_COLUMNS = ["设备单价", "人工包干单价", "综合单价汇总"]

REGION_OPTIONS = ["Singapore", "Malaysia", "Thailand", "Indonesia", "Vietnam", "Philippines", "Others"]
REGION_OPTIONS_ADMIN = ["Singapore", "Malaysia", "Thailand", "Indonesia", "Vietnam", "Philippines", "Others", "All"]
CURRENCY_OPTIONS = ["IDR", "USD", "RMB", "SGD", "MYR", "THB"]

OCR_MAPPING_COLUMNS = [
    "Ignore",
    "设备材料名称",
    "规格或型号",
    "品牌",
    "设备单价",
    "人工包干单价",
    "综合单价汇总",
    "原厂品牌维保期限",
    "货期",
    "备注",
]

OCR_EDITABLE_COLUMNS = [
    "设备材料名称",
    "规格或型号",
    "品牌",
    "设备单价",
    "人工包干单价",
    "综合单价汇总",
    "原厂品牌维保期限",
    "货期",
    "备注",
]

DS_OCR2_FIXED_PROMPT = """
请识别这张报价单页面中的报价明细表，并同时输出“原始表头 JSON”和“AI 自动匹配数据库字段 JSON”。

重要要求：
1. 只输出 JSON object，不要输出解释文字、Markdown 或代码块；
2. 保留报价单原始表头，不要擅自改名；
3. 保留每一行报价明细，不要合并不同行；
4. 看不清、模糊、无法确认、被遮挡、疑似错误的内容，统一输出字符串：请核查；
5. 不要猜测价格、型号、币种、小数点；
6. 不要把 subtotal、total、title、header、页脚、签字栏当成设备明细；
7. 如果某个原始列无法匹配数据库字段，请在 column_mapping 中标记为 Ignore；
8. 如果页面没有报价明细表，输出空数组，不要编造数据。

数据库字段只允许以下字段参与 AI 匹配：
[
  "设备材料名称",
  "规格或型号",
  "品牌",
  "设备单价",
  "人工包干单价",
  "综合单价汇总",
  "原厂品牌维保期限",
  "货期",
  "备注"
]

以下字段不要从 OCR 表格中匹配，后续由网页人工统一填写：
[
  "币种",
  "项目名称",
  "供应商名称",
  "询价日期",
  "询价人",
  "地区"
]

请严格输出以下 JSON 格式：
{
  "raw_tables": [
    {
      "table_name": "quotation_table",
      "columns": ["原始列名1", "原始列名2"],
      "rows": [
        {
          "原始列名1": "原始内容",
          "原始列名2": "原始内容"
        }
      ]
    }
  ],
  "column_mapping": {
    "原始列名1": "设备材料名称",
    "原始列名2": "规格或型号",
    "无法匹配的原始列名": "Ignore"
  },
  "mapped_tables": [
    {
      "table_name": "quotation_table_mapped",
      "columns": [
        "设备材料名称",
        "规格或型号",
        "品牌",
        "设备单价",
        "人工包干单价",
        "综合单价汇总",
        "原厂品牌维保期限",
        "货期",
        "备注"
      ],
      "rows": [
        {
          "设备材料名称": "",
          "规格或型号": "",
          "品牌": "",
          "设备单价": null,
          "人工包干单价": null,
          "综合单价汇总": null,
          "原厂品牌维保期限": "",
          "货期": "",
          "备注": ""
        }
      ]
    }
  ]
}
""".strip()


# ==================== SEARCH SYNONYMS ====================
SYNONYM_GROUPS = [
    ["海康威视", "海康", "hikvision", "hik vision", "hkvision", "hik-vision"],
    ["华为", "huawei"],
    ["中兴", "zte", "zte corporation"],
    ["新华三", "h3c"],
    ["思科", "cisco"],
    ["瞻博", "juniper"],
    ["锐捷", "ruijie"],
    ["戴尔", "dell", "dell emc"],
    ["惠普", "hp", "hewlett packard", "hpe"],
    ["联想", "lenovo"],
    ["浪潮", "inspur"],
    ["深信服", "sangfor"],
    ["飞塔", "fortinet"],
    ["帕洛阿尔托", "palo alto", "palo alto networks", "pan"],
    ["阿里云", "aliyun", "alibaba cloud"],
    ["腾讯云", "tencent cloud"],
    ["亚马逊云", "aws", "amazon web services"],
    ["微软云", "azure", "microsoft azure"],
    ["谷歌云", "gcp", "google cloud"],
]


def normalize_search_text(text: str) -> str:
    if text is None:
        return ""
    s = str(text).strip().lower()
    s = re.sub(r"[\s\-_]+", "", s)
    return s


SYNONYM_MAP = {}
for group in SYNONYM_GROUPS:
    normalized_group = []
    for item in group:
        s = normalize_search_text(item)
        if s:
            normalized_group.append(s)
    normalized_group = list(dict.fromkeys(normalized_group))
    for item in normalized_group:
        SYNONYM_MAP[item] = normalized_group


def expand_keywords(token: str):
    if token is None:
        return []
    t = normalize_search_text(token)
    if not t:
        return []
    if t in SYNONYM_MAP:
        return SYNONYM_MAP[t]
    return [t]


def split_query_tokens(text_value: str):
    if not text_value:
        return []
    return re.findall(r"\S+", str(text_value).strip())


def sql_normalize_expr(field_name: str) -> str:
    return f"REPLACE(REPLACE(REPLACE(LOWER(COALESCE({field_name}, '')), ' ', ''), '-', ''), '_', '')"


def build_search_blob_expr(fields):
    concat_sql = " || ' ' || ".join([f"COALESCE({f}, '')" for f in fields])
    return f"REPLACE(REPLACE(REPLACE(LOWER(({concat_sql})), ' ', ''), '-', ''), '_', '')"


def build_normalized_contains_conditions(field_sql: str, raw_text: str, prefix: str, params: dict):
    tokens = split_query_tokens(raw_text)
    if not tokens:
        return None

    all_token_ands = []

    for i, token in enumerate(tokens):
        synonyms = expand_keywords(token)
        token_ors = []
        for j, syn in enumerate(synonyms):
            pname = f"{prefix}_{i}_{j}"
            token_ors.append(f"{field_sql} LIKE :{pname}")
            params[pname] = f"%{syn}%"
        if token_ors:
            all_token_ands.append("(" + " OR ".join(token_ors) + ")")

    if not all_token_ands:
        return None

    return "(" + " AND ".join(all_token_ands) + ")"


def auto_map_header(orig_header: str):
    if orig_header is None:
        return None
    h = str(orig_header).strip().lower()
    for k, v in HEADER_SYNONYMS.items():
        if h == k.lower():
            return v
    h_norm = re.sub(r"[\s\-\_：:（）()]+", " ", h).strip()
    for k, v in HEADER_SYNONYMS.items():
        if h_norm == re.sub(r"[\s\-\_：:（）()]+", " ", k.lower()).strip():
            return v
    for k, v in HEADER_SYNONYMS.items():
        if k.lower() in h or h in k.lower():
            return v
    return None


def detect_header_from_preview(df_preview: pd.DataFrame, max_header_rows=2, max_search_rows=8):
    if df_preview is None or df_preview.shape[0] == 0:
        return None, None
    nrows, ncols = df_preview.shape
    search_rows = min(max_search_rows, nrows)
    best = {"score": -1}
    for start in range(search_rows):
        for rows_used in range(1, max_header_rows + 1):
            if start + rows_used > nrows:
                continue
            cand = []
            nonempty = 0
            mapped = 0
            for col in range(ncols):
                parts = []
                for r in range(start, start + rows_used):
                    cell = df_preview.iat[r, col]
                    if pd.isna(cell):
                        continue
                    s = str(cell).strip()
                    if s:
                        parts.append(s)
                header_text = " ".join(parts).strip()
                if header_text:
                    nonempty += 1
                cand.append(header_text)
                if header_text and auto_map_header(header_text):
                    mapped += 1
            score = mapped + 0.5 * nonempty
            if score > best["score"]:
                best = {
                    "score": score, "header": cand, "row": start,
                    "rows_used": rows_used, "mapped": mapped, "nonempty": nonempty
                }
    if best.get("header") is not None:
        if best["mapped"] >= 2 or (best["nonempty"] > 0 and (best["mapped"] / best["nonempty"]) >= 0.3):
            return best["header"], best["row"] + best["rows_used"] - 1
    return None, None


def normalize_for_display(df: pd.DataFrame) -> pd.DataFrame:
    if df is None:
        return df
    df_disp = df.copy()
    for col in df_disp.columns:
        try:
            ser = df_disp[col]
            if ser.dtype == "object":
                df_disp[col] = ser.where(ser.notna(), None).apply(lambda x: "" if x is None else str(x))
        except Exception:
            df_disp[col] = df_disp[col].where(df_disp[col].notna(), None).apply(lambda x: "" if x is None else str(x))
    return df_disp


def safe_st_dataframe(df: pd.DataFrame, height=None):
    df_disp = normalize_for_display(df)
    if height is None:
        st.dataframe(df_disp, use_container_width=True)
    else:
        st.dataframe(df_disp, height=height, use_container_width=True)


def normalize_cell(x):
    if pd.isna(x):
        return None
    s = str(x).strip()
    if s.lower() in ("", "nan", "none"):
        return None
    return s


def normalize_unclear_text(value):
    """将 OCR 模型常见的不确定表达统一显示为“请核查”。"""
    if value is None:
        return ""
    s = str(value).strip()
    if not s:
        return ""

    unclear_tokens = {
        "unclear", "[unclear]", "unknown", "[unknown]", "n/a", "na",
        "无法识别", "无法确认", "看不清", "模糊", "不清楚", "不可读", "未识别",
        "请核查", "请核对", "需核查", "需人工核查"
    }
    if s.lower() in unclear_tokens or s in unclear_tokens:
        return "请核查"
    return s


def pdf_bytes_to_page_png_bytes(pdf_bytes: bytes, dpi: int = 220, max_pages: int = 8):
    """将 PDF 每页转为 PNG bytes，供 DeepSeek-OCR2 图片接口识别。"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    for i in range(min(len(doc), max_pages)):
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        pages.append(pix.tobytes("png"))

    doc.close()
    return pages


def extract_json_from_text(text_value: str):
    """Extract JSON object from model response, including ```json fenced content."""
    if not text_value:
        raise ValueError("OCR 服务返回空内容。")

    s = str(text_value).strip()
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```$", "", s)

    try:
        return json.loads(s)
    except Exception:
        pass

    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        return json.loads(s[start:end + 1])

    raise ValueError("OCR result is not valid JSON.")


def normalize_json_values(obj):
    """递归清理 JSON 中的 OCR 不确定表达。"""
    if isinstance(obj, dict):
        return {str(k): normalize_json_values(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalize_json_values(v) for v in obj]
    if obj is None:
        return None
    if isinstance(obj, (int, float, bool)):
        return obj
    return normalize_unclear_text(obj)


def call_deepseek_ocr2_image_api(image_bytes: bytes, filename: str = "page.png") -> dict:
    """
    调用第三方已部署好的 DeepSeek-OCR2 / 多模态 OCR API。

    默认按 OpenAI-compatible Chat Completions 图片输入格式发送：
    - DS_OCR2_API_KEY：第三方平台提供的 API Key
    - DS_OCR2_API_URL：第三方平台提供的 chat/completions 接口地址
    - DS_OCR2_MODEL：第三方平台提供的模型名

    固定 Prompt 位于 DS_OCR2_FIXED_PROMPT，并随每一页图片一起发送。
    """
    if not DS_OCR2_API_KEY:
        raise ValueError("OCR 服务暂未配置，请联系管理员。")

    if not DS_OCR2_API_URL:
        raise ValueError("OCR 服务地址暂未配置，请联系管理员。")

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    image_data_url = f"data:image/png;base64,{image_b64}"

    payload = {
        "model": DS_OCR2_MODEL,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": DS_OCR2_FIXED_PROMPT,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data_url
                        },
                    },
                ],
            }
        ],
    }

    headers = {
        "Authorization": f"Bearer {DS_OCR2_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        DS_OCR2_API_URL,
        headers=headers,
        json=payload,
        timeout=300,
    )
    response.raise_for_status()
    data = response.json()

    # 兼容少数 OCR API 直接返回结构化 JSON 的情况。
    if isinstance(data.get("json"), dict):
        return normalize_json_values(data["json"])
    if isinstance(data.get("result"), dict):
        return normalize_json_values(data["result"])

    # OpenAI-compatible 标准返回：choices[0].message.content
    try:
        text_value = data["choices"][0]["message"]["content"]
    except Exception:
        text_value = data.get("text") or data.get("ocr_text") or data.get("content") or ""

    parsed = extract_json_from_text(text_value)
    return normalize_json_values(parsed)


def merge_ds_ocr2_page_json(page_json_list):
    """合并多页 DeepSeek-OCR2 输出。"""
    merged = {
        "raw_tables": [],
        "column_mapping": {},
        "mapped_tables": []
    }

    for page_idx, obj in enumerate(page_json_list, start=1):
        if not isinstance(obj, dict):
            continue

        for table in obj.get("raw_tables", []) or []:
            if isinstance(table, dict):
                table = table.copy()
                table["page"] = page_idx
                merged["raw_tables"].append(table)

        for raw_col, target_col in (obj.get("column_mapping", {}) or {}).items():
            if raw_col not in merged["column_mapping"]:
                merged["column_mapping"][raw_col] = target_col

        for table in obj.get("mapped_tables", []) or []:
            if isinstance(table, dict):
                table = table.copy()
                table["page"] = page_idx
                merged["mapped_tables"].append(table)

    return merged


def call_ds_ocr2_for_pdf(pdf_bytes: bytes, filename: str):
    """PDF -> 每页图片 -> DeepSeek-OCR2 -> 合并 raw_tables / column_mapping / mapped_tables。"""
    page_images = pdf_bytes_to_page_png_bytes(pdf_bytes, dpi=220, max_pages=8)
    if not page_images:
        raise ValueError("No pages found in PDF.")

    page_outputs = []
    for idx, img_bytes in enumerate(page_images, start=1):
        page_json = call_deepseek_ocr2_image_api(img_bytes, filename=f"{filename}_page_{idx}.png")
        page_outputs.append(page_json)

    return merge_ds_ocr2_page_json(page_outputs)


def raw_tables_to_dataframe(ocr_json: dict) -> pd.DataFrame:
    """将 raw_tables 合并为一个可供人工映射的 DataFrame。"""
    raw_tables = ocr_json.get("raw_tables", []) if isinstance(ocr_json, dict) else []
    dfs = []

    for t_idx, table in enumerate(raw_tables, start=1):
        if not isinstance(table, dict):
            continue
        columns = table.get("columns") or []
        rows = table.get("rows") or []
        if not isinstance(rows, list):
            continue

        clean_rows = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            clean_row = {}
            for col in columns:
                clean_row[str(col)] = normalize_unclear_text(row.get(col, ""))
            # 兼容模型漏写 columns 但 rows 里有键的情况
            for k, v in row.items():
                if str(k) not in clean_row:
                    clean_row[str(k)] = normalize_unclear_text(v)
            clean_rows.append(clean_row)

        if clean_rows:
            df = pd.DataFrame(clean_rows)
            df.insert(0, "来源页", table.get("page", ""))
            df.insert(1, "来源表", table.get("table_name", f"table_{t_idx}"))
            dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    return pd.concat(dfs, ignore_index=True, sort=False).fillna("")


def get_ai_column_mapping(ocr_json: dict) -> dict:
    mapping = ocr_json.get("column_mapping", {}) if isinstance(ocr_json, dict) else {}
    if not isinstance(mapping, dict):
        return {}

    cleaned = {}
    for raw_col, target_col in mapping.items():
        raw_col = str(raw_col)
        target_col = str(target_col).strip() if target_col is not None else "Ignore"
        if target_col not in OCR_MAPPING_COLUMNS:
            target_col = "Ignore"
        cleaned[raw_col] = target_col
    return cleaned


def apply_column_mapping_to_raw_df(raw_df: pd.DataFrame, mapped_choices: dict) -> pd.DataFrame:
    """根据用户确认后的 mapping，生成可人工编辑的数据库字段表。"""
    if raw_df is None or raw_df.empty:
        return pd.DataFrame(columns=OCR_EDITABLE_COLUMNS)

    result = pd.DataFrame()
    for raw_col, target_col in mapped_choices.items():
        if target_col == "Ignore":
            continue
        if raw_col not in raw_df.columns:
            continue
        if target_col not in OCR_EDITABLE_COLUMNS:
            continue

        # 如果多个 OCR 列映射到同一个目标字段，优先保留已有非空值，用空值补充。
        source_ser = raw_df[raw_col].map(normalize_unclear_text)
        if target_col not in result.columns:
            result[target_col] = source_ser
        else:
            mask = result[target_col].map(normalize_cell).isna()
            result.loc[mask, target_col] = source_ser.loc[mask]

    for col in OCR_EDITABLE_COLUMNS:
        if col not in result.columns:
            result[col] = ""

    result = result[OCR_EDITABLE_COLUMNS]
    for col in NUMERIC_COLUMNS:
        if col in result.columns:
            result[col] = result[col].astype(str).str.replace(",", "", regex=False).str.replace(" ", "", regex=False)

    return result


def validate_quotation_df(df: pd.DataFrame):
    if df is None or df.empty:
        return pd.DataFrame(columns=DB_COLUMNS), pd.DataFrame(columns=DB_COLUMNS)

    df2 = df.copy()
    for col in DB_COLUMNS:
        if col not in df2.columns:
            df2[col] = pd.NA
    df2 = df2[DB_COLUMNS]

    required_nonprice = ["项目名称", "供应商名称", "询价人", "币种", "询价日期", "设备材料名称"]
    missing_required = df2[required_nonprice].map(normalize_cell).isna().any(axis=1)

    def price_has_value(row):
        return normalize_cell(row.get("设备单价")) is not None or normalize_cell(row.get("人工包干单价")) is not None or normalize_cell(row.get("综合单价汇总")) is not None

    price_mask = df2.apply(price_has_value, axis=1)
    invalid_mask = missing_required | (~price_mask)

    df_valid = df2[~invalid_mask].copy()
    df_invalid = df2[invalid_mask].copy()
    return df_valid, df_invalid


# ==================== AUTH ====================
def login_form():
    ui_card(t("login_system"), t("login_sub"))
    ui_hr()

    with st.form("login_form"):
        u = st.text_input(t("username"))
        p = st.text_input(t("password"), type="password")
        submitted = st.form_submit_button(t("login_btn"))

    if submitted:
        if not u or not p:
            st.error(t("enter_user_pass"))
            return
        pw_hash = hashlib.sha256(p.encode()).hexdigest()
        with engine.begin() as conn:
            user_row = conn.execute(
                text("SELECT username, role, region FROM users WHERE username=:u AND password=:p"),
                {"u": u, "p": pw_hash}
            ).fetchone()
        if user_row:
            st.session_state["user"] = {"username": user_row.username, "role": user_row.role, "region": user_row.region}
            safe_rerun()
        else:
            st.error(t("wrong_user_pass"))


def logout():
    if "user" in st.session_state:
        del st.session_state["user"]
    safe_rerun()


# ==================== PAGE FLOW ====================
if "user" not in st.session_state:
    top_lang_l, top_lang_r = st.columns([6, 1.4])
    with top_lang_r:
        set_language_widget("lang_selector_guest_top")

    left, right = st.columns([1.35, 1])
    with left:
        st.markdown(f"## ✨ {t('app_title')}")
    with right:
        st.markdown(
            f"""
            <div class="card">
              <div class="title">{t("help_title")}</div>
              <div class="sub">
                {t("help_text")}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    ui_hr()
    login_form()
    st.stop()

user = st.session_state["user"]


# ==================== TOP BAR ====================
top_l, top_m, top_blank = st.columns([1.4, 2.3, 1.1])

with top_blank:
    set_language_widget("lang_selector_user_top")

with top_m:
    pages = [t("page_input"), t("page_device_query"), t("page_misc_query")]
    if user["role"] == "admin":
        pages.append(t("page_admin"))
    nav_tabs = st.tabs(pages)

with top_l:
    st.markdown(
        f"""
        <div class="card">
          <div class="title">{t("app_title")}</div>
          <div class="sub">{t("app_subtitle")}</div>
          <div class="hr" style="margin:0.75rem 0 0.8rem 0;"></div>
          <div class="title" style="font-size:0.98rem;">{t("current_user")}</div>
          <div class="sub">
            👤 {user["username"]}<br/>
            🏢 {user["region"]}<br/>
            🔑 {user["role"]}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button(t("logout"), key="logout_btn_top"):
        logout()

ui_hr()


# ==================== PAGE: HOME / INPUT ====================
with nav_tabs[0]:
    ui_card(t("input_center"), t("input_center_sub"))
    ui_hr()

    st.header("📄 PDF 报价单 OCR 录入")
    st.caption("上传 PDF 报价文件，系统会调用 DeepSeek-OCR2 服务识别为原始表格，并给出 AI 推荐字段映射。最终入库前必须人工确认。")

    uploaded_pdf = st.file_uploader("上传 PDF 报价文件", type=["pdf"], key="upload_pdf_ocr")

    if uploaded_pdf:
        st.info(f"已上传：{uploaded_pdf.name}")

        col_ocr_1, col_ocr_2 = st.columns([1, 4])
        run_ocr = col_ocr_1.button("开始 OCR 识别", key="run_pdf_ocr")
        col_ocr_2.caption("识别结果会先展示原始表格和 AI 推荐映射，不会直接入库。")

        if run_ocr:
            try:
                with st.spinner("正在调用 DeepSeek-OCR2 识别 PDF，请稍候..."):
                    ocr_json = call_ds_ocr2_for_pdf(uploaded_pdf.getvalue(), uploaded_pdf.name)
                    raw_df = raw_tables_to_dataframe(ocr_json)
                    ai_mapping = get_ai_column_mapping(ocr_json)

                    if raw_df.empty:
                        st.warning("OCR 未识别到可用报价表格，请检查 PDF 是否清晰。")
                    else:
                        st.session_state["ocr_json_raw"] = json.dumps(ocr_json, ensure_ascii=False, indent=2)
                        st.session_state["ocr_raw_df_csv"] = raw_df.to_csv(index=False)
                        st.session_state["ocr_ai_mapping_json"] = json.dumps(ai_mapping, ensure_ascii=False)
                        st.session_state.pop("ocr_mapped_csv", None)
                        st.session_state.pop("ocr_edited_csv", None)
                        st.session_state.pop("ocr_final_csv", None)
                        st.session_state["ocr_ready_for_global"] = False
                        st.success("OCR 识别完成，请先检查原始表格和 AI 推荐字段映射。")
            except Exception as e:
                st.error(f"OCR 识别失败：{e}")

    if st.session_state.get("ocr_json_raw"):
        with st.expander("查看 DeepSeek-OCR2 原始 JSON", expanded=False):
            st.code(st.session_state["ocr_json_raw"], language="json")

    if st.session_state.get("ocr_raw_df_csv"):
        try:
            raw_df = pd.read_csv(io.StringIO(st.session_state["ocr_raw_df_csv"]), dtype=object).fillna("")
        except Exception as e:
            st.error(f"恢复 OCR 原始表格失败：{e}")
            raw_df = pd.DataFrame()

        try:
            ai_mapping = json.loads(st.session_state.get("ocr_ai_mapping_json", "{}"))
        except Exception:
            ai_mapping = {}

        if not raw_df.empty:
            st.markdown("### 1. OCR 原始识别表格")
            st.caption("这里显示 DeepSeek-OCR2 识别出的原始表头和原始内容。看不清的内容会显示为：请核查。")
            safe_st_dataframe(raw_df, height=360)

            st.markdown("### 2. AI 推荐字段映射，可人工修改")
            st.caption("AI 会先自动猜测每个 OCR column 对应哪个数据库字段。如果不对，可以手动改。")

            mapped_choices = {}
            with st.form("ocr_ai_mapping_form", clear_on_submit=False):
                cols_left, cols_right = st.columns(2)
                for i, raw_col in enumerate(raw_df.columns):
                    # 来源页 / 来源表只用于追溯，不参与入库字段映射。
                    if raw_col in ["来源页", "来源表"]:
                        default = "Ignore"
                    else:
                        default = ai_mapping.get(raw_col, auto_map_header(raw_col) or "Ignore")
                        if default not in OCR_MAPPING_COLUMNS:
                            default = "Ignore"

                    container = cols_left if i % 2 == 0 else cols_right
                    selected = container.selectbox(
                        f"OCR列：{raw_col}",
                        OCR_MAPPING_COLUMNS,
                        index=OCR_MAPPING_COLUMNS.index(default),
                        key=f"ocr_ds_map_{i}_{raw_col}"
                    )
                    mapped_choices[raw_col] = selected

                submit_mapping = st.form_submit_button("应用映射并进入人工修改")

            if submit_mapping:
                df_mapped = apply_column_mapping_to_raw_df(raw_df, mapped_choices)
                st.session_state["ocr_mapped_csv"] = df_mapped.to_csv(index=False)
                st.session_state.pop("ocr_edited_csv", None)
                st.session_state.pop("ocr_final_csv", None)
                st.session_state["ocr_ready_for_global"] = False
                st.success("字段映射已应用。请在下方人工修改识别结果。")

    if st.session_state.get("ocr_mapped_csv"):
        try:
            df_for_edit = pd.read_csv(io.StringIO(st.session_state["ocr_mapped_csv"]), dtype=object).fillna("")
            for col in OCR_EDITABLE_COLUMNS:
                if col not in df_for_edit.columns:
                    df_for_edit[col] = ""
            df_for_edit = df_for_edit[OCR_EDITABLE_COLUMNS]
        except Exception as e:
            st.error(f"恢复映射后表格失败：{e}")
            df_for_edit = pd.DataFrame(columns=OCR_EDITABLE_COLUMNS)

        st.markdown("### 3. 人工修改识别结果")
        st.warning("请重点核对：设备材料名称、规格或型号、设备单价、人工包干单价、综合单价汇总、小数点、货期和维保期限。")

        edited_df = st.data_editor(
            df_for_edit,
            use_container_width=True,
            num_rows="dynamic",
            key="ocr_edit_table_after_mapping",
            height=420,
        )

        if st.button("保存人工修改，下一步填写全局信息", key="save_ocr_edits_next_global"):
            st.session_state["ocr_edited_csv"] = edited_df.to_csv(index=False)
            st.session_state["ocr_ready_for_global"] = True
            st.session_state.pop("ocr_final_csv", None)
            st.success("人工修改已保存。请继续填写全局信息。")

    if st.session_state.get("ocr_ready_for_global") and st.session_state.get("ocr_edited_csv"):
        try:
            df_edited_saved = pd.read_csv(io.StringIO(st.session_state["ocr_edited_csv"]), dtype=object).fillna("")
            for col in OCR_EDITABLE_COLUMNS:
                if col not in df_edited_saved.columns:
                    df_edited_saved[col] = ""
            df_edited_saved = df_edited_saved[OCR_EDITABLE_COLUMNS]
        except Exception as e:
            st.error(f"恢复人工修改表格失败：{e}")
            df_edited_saved = pd.DataFrame(columns=OCR_EDITABLE_COLUMNS)

        st.markdown("### 4. 填写全局信息")
        st.caption("以下 5 项由人工统一填写，并覆盖到每一条报价记录：币种、项目名称、供应商名称、询价日期、询价人。地区自动使用当前登录用户地区。")

        with st.form("ocr_global_info_form", clear_on_submit=False):
            g1, g2, g3, g4, g5 = st.columns(5)
            g_currency = g1.selectbox("币种", CURRENCY_OPTIONS, key="ocr_global_currency")
            g_project = g2.text_input("项目名称", key="ocr_global_project")
            g_supplier = g3.text_input("供应商名称", key="ocr_global_supplier")
            g_date = g4.date_input("询价日期", value=date.today(), key="ocr_global_date")
            g_enquirer = g5.text_input("询价人", key="ocr_global_enquirer")
            apply_global = st.form_submit_button("应用全局信息并校验")

        if apply_global:
            if not (g_currency and g_project and g_supplier and g_date and g_enquirer):
                st.error("请填写：币种、项目名称、供应商名称、询价日期、询价人。")
            else:
                df_final = df_edited_saved.copy()
                df_final["币种"] = str(g_currency)
                df_final["项目名称"] = str(g_project)
                df_final["供应商名称"] = str(g_supplier)
                df_final["询价日期"] = str(g_date)
                df_final["询价人"] = str(g_enquirer)
                df_final["地区"] = user["region"]

                for col in DB_COLUMNS:
                    if col not in df_final.columns:
                        df_final[col] = ""
                df_final = df_final[DB_COLUMNS]

                for col in NUMERIC_COLUMNS:
                    if col in df_final.columns:
                        df_final[col] = pd.to_numeric(
                            df_final[col].astype(str).str.replace(",", "", regex=False).str.replace(" ", "", regex=False),
                            errors="coerce"
                        )

                st.session_state["ocr_final_csv"] = df_final.to_csv(index=False)
                st.success("全局信息已应用，请检查校验结果后确认入库。")

    if st.session_state.get("ocr_final_csv"):
        try:
            df_final_preview = pd.read_csv(io.StringIO(st.session_state["ocr_final_csv"]), dtype=object)
            for col in DB_COLUMNS:
                if col not in df_final_preview.columns:
                    df_final_preview[col] = pd.NA
            df_final_preview = df_final_preview[DB_COLUMNS]
        except Exception as e:
            st.error(f"恢复最终表格失败：{e}")
            df_final_preview = pd.DataFrame(columns=DB_COLUMNS)

        st.markdown("### 5. 入库前最终确认")
        safe_st_dataframe(df_final_preview, height=360)

        c_valid, c_invalid = validate_quotation_df(df_final_preview)
        cc1, cc2, cc3 = st.columns(3)
        cc1.metric("可导入记录", len(c_valid))
        cc2.metric("需修正记录", len(c_invalid))
        cc3.metric("总记录", len(df_final_preview))

        if not c_invalid.empty:
            st.markdown("#### 以下记录缺少必填字段或价格字段，暂不能导入")
            safe_st_dataframe(c_invalid, height=260)

        confirm_import = st.checkbox("我已人工核对 OCR 结果，确认导入有效记录", key="confirm_ocr_import")

        if st.button("确认导入数据库", key="import_ocr_records"):
            if not confirm_import:
                st.warning("请先勾选确认框。")
            elif c_valid.empty:
                st.warning("没有可导入的有效记录。")
            else:
                try:
                    df_to_store = c_valid.copy()
                    for col in NUMERIC_COLUMNS:
                        if col in df_to_store.columns:
                            df_to_store[col] = pd.to_numeric(df_to_store[col], errors="coerce")
                    df_to_store = df_to_store.astype(object).where(pd.notnull(df_to_store), None)

                    with engine.begin() as conn:
                        df_to_store.to_sql("quotations", conn, if_exists="append", index=False, method="multi")

                    st.success(f"✅ 已导入 {len(df_to_store)} 条 OCR 报价记录。")
                    for k in [
                        "ocr_json_raw", "ocr_raw_df_csv", "ocr_ai_mapping_json",
                        "ocr_mapped_csv", "ocr_edited_csv", "ocr_final_csv",
                    ]:
                        st.session_state.pop(k, None)
                    st.session_state["ocr_ready_for_global"] = False
                    safe_rerun()
                except Exception as e:
                    st.error(f"导入 OCR 记录失败：{e}")

    ui_hr()
    st.header(t("manual_device"))
    with st.form("manual_add_form_original", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        pj = col1.text_input(t("project_name"))
        sup = col2.text_input(t("supplier_name"))
        inq = col3.text_input(t("enquirer"))

        col4, col5, col6 = st.columns(3)
        name = col4.text_input(t("material_name"))
        model_spec = col5.text_input("规格或型号")
        brand = col6.text_input(t("brand_optional"))

        col7, col8, col9, col10 = st.columns(4)
        price = col7.number_input(t("device_unit_price"), min_value=0.0)
        labor_price = col8.number_input(t("labor_unit_price"), min_value=0.0)
        total_price = col9.number_input("综合单价汇总", min_value=0.0)
        cur = col10.selectbox(t("currency"), CURRENCY_OPTIONS)

        col11, col12 = st.columns(2)
        warranty = col11.text_input("原厂品牌维保期限")
        lead_time = col12.text_input("货期")

        remark = st.text_area("备注")
        date_inq = st.date_input(t("inq_date"), value=date.today())
        submit_manual = st.form_submit_button(t("manual_add_btn"))

    if submit_manual:
        if not (pj and sup and inq and name):
            st.error(t("manual_required"))
        elif not (price > 0 or labor_price > 0 or total_price > 0):
            st.error("请至少填写设备单价、人工包干单价或综合单价汇总中的一项，且大于 0。")
        else:
            try:
                with engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO quotations
                        (项目名称,供应商名称,询价人,设备材料名称,规格或型号,品牌,
                         设备单价,人工包干单价,综合单价汇总,币种,
                         原厂品牌维保期限,货期,备注,地区,询价日期)
                        VALUES (:p,:s,:i,:n,:spec,:b,:pr,:lp,:tp,:c,:w,:lt,:rm,:reg,:dt)
                    """), {
                        "p": pj,
                        "s": sup,
                        "i": inq,
                        "n": name,
                        "spec": model_spec,
                        "b": brand if brand is not None else "",
                        "pr": float(price) if price > 0 else None,
                        "lp": float(labor_price) if labor_price > 0 else None,
                        "tp": float(total_price) if total_price > 0 else None,
                        "c": cur,
                        "w": warranty,
                        "lt": lead_time,
                        "rm": remark,
                        "reg": user["region"],
                        "dt": str(date_inq)
                    })
                st.success(t("manual_add_success"))
            except Exception as e:
                st.error(t("manual_add_fail").format(e))

    ui_hr()
    st.header(t("manual_misc"))
    with st.form("manual_misc_form", clear_on_submit=True):
        mcol1, mcol2, mcol3 = st.columns(3)
        misc_project = mcol1.text_input(t("project_name"))
        misc_category = mcol2.text_input(t("misc_category"))
        misc_amount = mcol3.number_input(t("amount"), min_value=0.0, format="%f")
        mc1, mc2 = st.columns(2)
        misc_currency = mc1.selectbox(t("currency"), CURRENCY_OPTIONS)
        misc_note = mc2.text_input(t("remark_optional"))
        misc_date = st.date_input(t("occ_date"), value=date.today())
        submit_misc = st.form_submit_button(t("add_misc_btn"))

    if submit_misc:
        if not (misc_project and misc_category) or misc_amount is None:
            st.error(t("misc_required"))
        else:
            try:
                with engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO misc_costs
                        (项目名称, 杂费类目, 金额, 币种, 录入人, 地区, 发生日期)
                        VALUES (:pj, :cat, :amt, :cur, :user, :region, :occ_date)
                    """), {
                        "pj": misc_project,
                        "cat": misc_category + (f" | {misc_note}" if misc_note else ""),
                        "amt": float(misc_amount),
                        "cur": misc_currency,
                        "user": user["username"],
                        "region": user["region"],
                        "occ_date": str(misc_date)
                    })
                st.success(t("misc_add_success"))
            except Exception as e:
                st.error(t("misc_add_fail").format(e))


# ==================== PAGE: SEARCH QUOTATIONS ====================
with nav_tabs[1]:
    ui_card(t("device_query_title"), t("device_query_sub"))
    ui_hr()

    st.header("📋 " + t("device_query_title"))

    kw = st.text_input(t("keyword_multi"), key="search_kw")
    st.caption(t("search_alias_caption"))

    search_fields = st.multiselect(
        t("search_fields"),
        ["设备材料名称", "规格或型号", "品牌", "项目名称", "供应商名称", "备注", "地区"],
        key="search_fields"
    )
    pj_filter = st.text_input(t("filter_project"), key="search_pj")
    sup_filter = st.text_input(t("filter_supplier"), key="search_sup")
    brand_filter = st.text_input(t("filter_brand"), key="search_brand")
    cur_filter = st.selectbox(t("currency"), [t("all")] + CURRENCY_OPTIONS, index=0, key="search_cur")

    regions_options = [t("all")] + REGION_OPTIONS_ADMIN
    if user["role"] == "admin":
        region_filter = st.selectbox(t("filter_region_admin"), regions_options, index=0, key="search_region")
    else:
        st.info(t("only_region_data").format(user["region"]))
        region_filter = user["region"]

    if st.button(t("search_device_btn"), key="search_button"):
        conds = []
        params = {}

        if user["role"] != "admin":
            conds.append("地区 = :r")
            params["r"] = user["region"]
        else:
            if region_filter and region_filter != t("all"):
                conds.append("地区 = :r")
                params["r"] = region_filter

        if pj_filter:
            project_expr = sql_normalize_expr("项目名称")
            pj_cond = build_normalized_contains_conditions(project_expr, pj_filter, "pj", params)
            if pj_cond:
                conds.append(pj_cond)

        if sup_filter:
            supplier_expr = sql_normalize_expr("供应商名称")
            sup_cond = build_normalized_contains_conditions(supplier_expr, sup_filter, "sup", params)
            if sup_cond:
                conds.append(sup_cond)

        if brand_filter:
            brand_expr = sql_normalize_expr("品牌")
            brand_cond = build_normalized_contains_conditions(brand_expr, brand_filter, "brand", params)
            if brand_cond:
                conds.append(brand_cond)

        if cur_filter != t("all"):
            conds.append("币种 = :cur")
            params["cur"] = cur_filter

        if kw:
            fields = search_fields if search_fields else [
                "设备材料名称", "规格或型号", "品牌", "项目名称", "供应商名称", "备注"
            ]
            search_blob_expr = build_search_blob_expr(fields)
            kw_cond = build_normalized_contains_conditions(search_blob_expr, kw, "kw", params)
            if kw_cond:
                conds.append(kw_cond)

        sql = "SELECT * FROM quotations"
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY id DESC"

        try:
            df = pd.read_sql(text(sql), engine, params=params)
        except Exception as e:
            st.error(t("query_fail").format(e))
            df = pd.DataFrame()

        if df.empty:
            st.info(t("no_records"))
        else:
            safe_st_dataframe(df, height=520)

            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df.to_excel(writer, index=False)
            buf.seek(0)
            st.download_button(t("download_result"), buf, "device_query_results.xlsx", key="download_search")

            try:
                df_prices = df.copy()
                device_price_col = "设备单价"
                labor_price_col = "人工包干单价"
                name_col = "设备材料名称"

                df_prices[device_price_col] = pd.to_numeric(df_prices.get(device_price_col), errors="coerce")
                df_prices[labor_price_col] = pd.to_numeric(df_prices.get(labor_price_col), errors="coerce")

                overall = {
                    "dev_mean": df_prices[device_price_col].mean(skipna=True),
                    "dev_min": df_prices[device_price_col].min(skipna=True),
                    "lab_mean": df_prices[labor_price_col].mean(skipna=True),
                    "lab_min": df_prices[labor_price_col].min(skipna=True),
                }

                def fmt(v):
                    return "-" if (v is None or (isinstance(v, float) and pd.isna(v))) else f"{v:,.2f}"

                ui_hr()
                st.markdown(t("price_stats"))
                c1, c2, c3, c4 = st.columns(4)
                c1.metric(t("device_avg"), fmt(overall["dev_mean"]))
                c2.metric(t("device_min"), fmt(overall["dev_min"]))
                c3.metric(t("labor_avg"), fmt(overall["lab_mean"]))
                c4.metric(t("labor_min"), fmt(overall["lab_min"]))

                if not pd.isna(overall["dev_min"]):
                    dev_min_rows = df_prices[df_prices[device_price_col] == overall["dev_min"]].copy()
                    st.markdown(t("device_min_rows"))
                    safe_st_dataframe(dev_min_rows.reset_index(drop=True), height=260)

                if not pd.isna(overall["lab_min"]):
                    lab_min_rows = df_prices[df_prices[labor_price_col] == overall["lab_min"]].copy()
                    st.markdown(t("labor_min_rows"))
                    safe_st_dataframe(lab_min_rows.reset_index(drop=True), height=260)

                if name_col in df_prices.columns:
                    agg = df_prices.groupby(name_col).agg(
                        设备单价_均价=(device_price_col, lambda s: s.mean(skipna=True)),
                        设备单价_最低=(device_price_col, lambda s: s.min(skipna=True)),
                        人工包干单价_均价=(labor_price_col, lambda s: s.mean(skipna=True)),
                        人工包干单价_最低=(labor_price_col, lambda s: s.min(skipna=True)),
                        样本数=(device_price_col, "count")
                    ).reset_index()
                    st.markdown(t("group_by_name"))
                    safe_st_dataframe(agg.sort_values(by="设备单价_均价", ascending=True).head(200), height=360)
            except Exception as e:
                st.warning(t("stats_fail").format(e))

            if user["role"] == "admin":
                ui_hr()
                st.markdown(t("admin_delete_title"))
                choices = []
                for _, row in df.iterrows():
                    rid = int(row["id"])
                    proj = str(row.get("项目名称", ""))[:40]
                    name = str(row.get("设备材料名称", ""))[:60]
                    brand = str(row.get("品牌", ""))[:30]
                    choices.append(f"{rid} | {proj} | {name} | {brand}")

                with st.form("admin_delete_form_pg", clear_on_submit=False):
                    selected = st.multiselect(t("admin_select_delete"), choices, key="admin_delete_selected_pg")
                    confirm = st.checkbox(t("admin_confirm_delete"), key="admin_delete_confirm_pg")
                    submit_del = st.form_submit_button(t("admin_delete_btn"), key="admin_delete_submit_pg")

                if submit_del:
                    if not selected:
                        st.warning(t("select_delete_first"))
                    elif not confirm:
                        st.warning(t("confirm_delete_first"))
                    else:
                        try:
                            selected_ids = [int(s.split("|", 1)[0].strip()) for s in selected]
                        except Exception as e:
                            st.error(t("parse_id_fail").format(e))
                            selected_ids = []

                        if not selected_ids:
                            st.warning(t("invalid_id_cancel"))
                        else:
                            placeholders = ",".join(str(int(i)) for i in selected_ids)
                            try:
                                with engine.begin() as conn:
                                    conn.execute(text(f"""
                                        INSERT INTO deleted_quotations (
                                            original_id, 设备材料名称, 规格或型号, 品牌,
                                            设备单价, 人工包干单价, 综合单价汇总,
                                            币种, 原厂品牌维保期限, 货期, 备注,
                                            询价人, 项目名称, 供应商名称, 询价日期, 地区,
                                            deleted_by
                                        )
                                        SELECT
                                            id, 设备材料名称, 规格或型号, 品牌,
                                            设备单价, 人工包干单价, 综合单价汇总,
                                            币种, 原厂品牌维保期限, 货期, 备注,
                                            询价人, 项目名称, 供应商名称, 询价日期, 地区,
                                            :user
                                        FROM quotations WHERE id IN ({placeholders})
                                    """), {"user": user["username"]})
                                    conn.execute(text(f"DELETE FROM quotations WHERE id IN ({placeholders})"))
                                st.success(t("delete_archive_success"))
                                safe_rerun()
                            except Exception as e:
                                st.error(t("delete_archive_fail").format(e))
            else:
                st.info(t("only_admin_delete"))


# ==================== PAGE: SEARCH MISC ====================
with nav_tabs[2]:
    ui_card(t("misc_query_title"), t("misc_query_sub"))
    ui_hr()

    st.header("💰 " + t("misc_query_title"))
    pj2 = st.text_input(t("filter_project"), key="misc_pj")

    if st.button(t("search_misc_btn"), key="misc_search"):
        params = {"pj": f"%{pj2.lower()}%"}
        sql = """
            SELECT id, 项目名称, 杂费类目, 金额, 币种, 录入人, 地区, 发生日期
            FROM misc_costs
            WHERE LOWER(项目名称) LIKE :pj
            ORDER BY id DESC
        """
        if user["role"] != "admin":
            sql = sql.replace("ORDER BY id DESC", "AND 地区 = :r ORDER BY id DESC")
            params["r"] = user["region"]

        try:
            df2 = pd.read_sql(text(sql), engine, params=params)
        except Exception as e:
            st.error(t("query_fail").format(e))
            df2 = pd.DataFrame()

        safe_st_dataframe(df2, height=520)
        if not df2.empty:
            buf2 = io.BytesIO()
            with pd.ExcelWriter(buf2, engine="openpyxl") as writer:
                df2.to_excel(writer, index=False)
            buf2.seek(0)
            st.download_button(t("download_misc"), buf2, "misc_costs.xlsx", key="download_misc")


# ==================== PAGE: ADMIN ====================
if user["role"] == "admin":
    with nav_tabs[3]:
        ui_card(t("admin_panel"), t("admin_panel_sub"))
        ui_hr()

        st.header(t("admin_user_mgmt"))
        users_df = pd.read_sql(text("SELECT id, username, role, region FROM users ORDER BY id"), engine)
        safe_st_dataframe(users_df, height=420)

        ui_hr()
        st.subheader(t("admin_create_user_title"))
        st.caption(t("admin_create_user_sub"))

        with st.form("admin_create_user_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            new_user = c1.text_input(t("admin_create_username"), key="admin_create_username_input")
            new_pass = c2.text_input(t("admin_create_password"), type="password", key="admin_create_password_input")
            new_region_create = c3.selectbox(t("admin_create_region"), REGION_OPTIONS, key="admin_create_region_select")
            confirm_create = st.checkbox(t("admin_create_confirm"), key="admin_create_confirm_check")
            submit_create = st.form_submit_button(t("admin_create_btn"))

        if submit_create:
            if not new_user or not new_pass:
                st.warning(t("empty_user_pass"))
            elif not confirm_create:
                st.warning(t("admin_create_confirm_first"))
            else:
                try:
                    pw_hash = hashlib.sha256(new_pass.encode()).hexdigest()
                    with engine.begin() as conn:
                        conn.execute(
                            text("INSERT INTO users (username,password,role,region) VALUES (:u,:p,'user',:r)"),
                            {"u": new_user, "p": pw_hash, "r": new_region_create}
                        )
                    st.success(t("admin_create_success").format(new_user, new_region_create))
                    safe_rerun()
                except Exception:
                    st.error(t("admin_create_fail"))

        ui_hr()
        st.subheader(t("update_region_title"))

        region_options = REGION_OPTIONS_ADMIN
        user_choices = [f"{row['id']} | {row['username']} | {row['role']} | {row['region']}" for _, row in users_df.iterrows()]

        with st.form("admin_update_user_region_form"):
            target = st.selectbox(t("select_user_update"), user_choices, key="admin_update_user_select")
            new_region = st.selectbox(t("new_region"), region_options, key="admin_update_user_region")
            confirm_update = st.checkbox(t("confirm_update_region"), key="admin_update_user_confirm")
            submit_update = st.form_submit_button(t("update_region_btn"))

        if submit_update:
            try:
                target_id = int(target.split("|", 1)[0].strip())
                target_row = users_df[users_df["id"] == target_id]
                if target_row.empty:
                    st.error(t("user_not_found"))
                else:
                    target_username = str(target_row.iloc[0]["username"])
                    target_role = str(target_row.iloc[0]["role"])

                    if target_role == "admin" and target_username == "admin":
                        st.warning(t("default_admin_warn"))
                    elif not confirm_update:
                        st.warning(t("confirm_update_first"))
                    else:
                        with engine.begin() as conn:
                            conn.execute(text("UPDATE users SET region=:r WHERE id=:id"), {"r": new_region, "id": target_id})
                        st.success(t("update_region_success").format(target_username, new_region))
                        safe_rerun()
            except Exception as e:
                st.error(t("update_fail").format(e))

        ui_hr()
        st.subheader(t("delete_user_title"))
        st.caption(t("delete_user_caption"))

        protected_usernames = {user["username"], "admin"}
        deletable_rows = users_df[~users_df["username"].isin(protected_usernames)].copy()

        if deletable_rows.empty:
            st.info(t("no_deletable_user"))
        else:
            del_choices = [f"{row['id']} | {row['username']} | {row['role']} | {row['region']}" for _, row in deletable_rows.iterrows()]

            with st.form("admin_delete_users_form"):
                selected = st.multiselect(t("select_delete_user"), del_choices, key="admin_delete_users_select")
                confirm_del = st.checkbox(t("confirm_delete_user"), key="admin_delete_users_confirm")
                submit_del = st.form_submit_button(t("delete_user_btn"))

            if submit_del:
                if not selected:
                    st.warning(t("select_delete_first"))
                elif not confirm_del:
                    st.warning(t("confirm_delete_first"))
                else:
                    try:
                        del_ids = [int(s.split("|", 1)[0].strip()) for s in selected]
                        check_df = users_df[users_df["id"].isin(del_ids)]
                        bad = check_df[check_df["username"].isin(protected_usernames)]
                        if not bad.empty:
                            st.error(t("protected_user_error"))
                        else:
                            placeholders = ",".join(str(i) for i in del_ids)
                            with engine.begin() as conn:
                                conn.execute(text(f"DELETE FROM users WHERE id IN ({placeholders})"))
                            st.success(t("delete_user_success").format(len(del_ids)))
                            safe_rerun()
                    except Exception as e:
                        st.error(t("delete_archive_fail").format(e))
