import os
import ssl
from datetime import datetime

import pandas as pd
import pymysql
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# 頁面配置
st.set_page_config(page_title="英建工程 材料價格查詢", layout="wide")

st.markdown("""
<style>
html, body, [class*="css"] { font-size: 20px !important; }
.stDataFrame, .stDataEditor { font-size: 20px !important; }
div[data-testid="stDataFrame"] * { font-size: 20px !important; }
.block-container { padding-top: 1rem !important; }
/* 取消 rerun 時的變暗效果 */
[data-stale="true"] { opacity: 1 !important; }
</style>
""", unsafe_allow_html=True)

# 登入設定
APP_USER = os.getenv("APP_USER", "")
APP_PASS = os.getenv("APP_PASS", "")


def show_login():
    st.title("🏗️ 英建工程 材料價格查詢系統")
    st.subheader("🔐 請登入")
    _, col, _ = st.columns([1, 2, 1])
    with col:
        username = st.text_input("帳號", key="login_user")
        password = st.text_input("密碼", type="password", key="login_pass")
        if st.button("登入", use_container_width=True, type="primary"):
            if APP_USER and APP_PASS and username == APP_USER and password == APP_PASS:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("帳號或密碼錯誤")


if not st.session_state.get("authenticated"):
    show_login()
    st.stop()

# 標題
st.title("🏗️ 英建工程 材料價格查詢系統")

# 資料庫設定
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "price_query")
DB_USE_SSL = os.getenv("DB_USE_SSL", os.getenv("DB_SSL", "false")).lower() in ("1", "true", "yes", "on")
DB_SSL_CA = os.getenv("DB_SSL_CA", "")
DB_SSL_CA_CONTENT = os.getenv("DB_SSL_CA_CONTENT", "")

TABLE_SQL = """
CREATE TABLE IF NOT EXISTS materials (
    id INT AUTO_INCREMENT PRIMARY KEY,
    system VARCHAR(50),
    sub_system VARCHAR(50),
    vendor VARCHAR(100),
    vendor_full VARCHAR(255),
    quote_no VARCHAR(100),
    alias TEXT,
    name VARCHAR(255) NOT NULL,
    spec VARCHAR(255),
    unit VARCHAR(50),
    unit_price DECIMAL(20,4) NOT NULL,
    quote_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
"""

COLUMN_MAPPING = {
    "系統大類": "system",
    "系統": "system",
    "system": "system",

    "系統子類": "sub_system",
    "sub_system": "sub_system",

    "廠商簡稱": "vendor",
    "vendor": "vendor",

    "廠商全名": "vendor_full",
    "vendor_full": "vendor_full",

    "報價編號": "quote_no",
    "quote_no": "quote_no",

    "別稱": "alias",
    "alias": "alias",

    "品名": "name",
    "名稱": "name",
    "name": "name",
    "規格": "spec",
    "說明": "spec",
    "spec": "spec",
    "單位": "unit",
    "unit": "unit",
    "未稅單價": "unit_price",
    "單價": "unit_price",
    "unit_price": "unit_price",
    "price": "unit_price",
    "更新時間": "quote_date",
    "日期": "quote_date",
    "date": "quote_date",
}


def get_connection(db_name=None):
    if not DB_PASS:
        raise ValueError("請先設定 DB_PASS 環境變數。")

    conn_args = {
        "host": DB_HOST,
        "user": DB_USER,
        "password": DB_PASS,
        "port": DB_PORT,
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": True,
    }

    if DB_USE_SSL:
        if DB_SSL_CA_CONTENT:
            import tempfile

            tmp_ca = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
            tmp_ca.write(DB_SSL_CA_CONTENT.encode("utf-8"))
            tmp_ca.flush()
            tmp_ca.close()
            ssl_ctx = ssl.create_default_context(cafile=tmp_ca.name)
        elif DB_SSL_CA:
            ssl_ctx = ssl.create_default_context(cafile=DB_SSL_CA)
        else:
            ssl_ctx = ssl.create_default_context()
        conn_args["ssl"] = ssl_ctx

    if db_name:
        conn_args["database"] = db_name

    return pymysql.connect(**conn_args)


def ensure_database_and_table():
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        with get_connection(DB_NAME) as conn:
            with conn.cursor() as cursor:
                cursor.execute(TABLE_SQL)

                columns_to_check = {
                    "sub_system": "ALTER TABLE materials ADD COLUMN sub_system VARCHAR(50) AFTER system",
                    "vendor": "ALTER TABLE materials ADD COLUMN vendor VARCHAR(100) AFTER sub_system",
                    "vendor_full": "ALTER TABLE materials ADD COLUMN vendor_full VARCHAR(255) AFTER vendor",
                    "quote_no": "ALTER TABLE materials ADD COLUMN quote_no VARCHAR(100) AFTER vendor_full",
                    "alias": "ALTER TABLE materials ADD COLUMN alias TEXT AFTER quote_no",
                }

                for column_name, alter_sql in columns_to_check.items():
                    cursor.execute(f"SHOW COLUMNS FROM materials LIKE '{column_name}'")
                    if not cursor.fetchone():
                        cursor.execute(alter_sql)

                cursor.execute("SHOW COLUMNS FROM materials LIKE 'unit_price'")
                col_info = cursor.fetchone()
                col_type = col_info.get("Type", "").lower().replace(" ", "") if col_info else ""
                if col_info and "decimal(20,4)" not in col_type:
                    try:
                        cursor.execute("ALTER TABLE materials MODIFY COLUMN unit_price DECIMAL(20,4) NOT NULL")
                    except Exception:
                        pass
    except Exception as exc:
        raise RuntimeError(f"資料庫初始化失敗：{exc}")



def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    normalized = {}
    for col in df.columns:
        key = str(col).strip()
        normalized[key] = COLUMN_MAPPING.get(key, None)

    df = df.rename(columns={old: new for old, new in normalized.items() if new})
    required_columns = ["name", "unit_price"]
    if not all(col in df.columns for col in required_columns):
        raise ValueError("匯入檔案缺少必要欄位，請包含 '品名' 和 '未稅單價' 欄位。")

    defaults = {
        "system": "",
        "sub_system": "",
        "vendor": "",
        "vendor_full": "",
        "quote_no": "",
        "alias": "",
        "spec": "",
        "unit": "",
    }
    for key, value in defaults.items():
        if key not in df.columns:
            df[key] = value

    if "quote_date" not in df.columns:
        df["quote_date"] = pd.to_datetime(datetime.today().date())

    df = df[[
        "system",
        "sub_system",
        "vendor",
        "vendor_full",
        "quote_no",
        "alias",
        "name",
        "spec",
        "unit",
        "unit_price",
        "quote_date",
    ]]
    df = df.dropna(subset=["name", "unit_price"])
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["unit_price"] = df["unit_price"].replace([float("inf"), float("-inf")], pd.NA)
    df = df.dropna(subset=["unit_price"])
    df["unit_price"] = df["unit_price"].clip(lower=0, upper=9_999_999_999_999.99)
    df["quote_date"] = pd.to_datetime(df["quote_date"], errors="coerce").dt.date
    df["quote_date"] = df["quote_date"].fillna(datetime.today().date())

    return df


def import_dataframe(df: pd.DataFrame) -> tuple[int, list[str]]:
    ensure_database_and_table()
    df = normalize_dataframe(df)
    df["unit_price"] = df["unit_price"].astype(float)

    insert_sql = """
    INSERT INTO materials (
        system,
        sub_system,
        vendor,
        vendor_full,
        quote_no,
        alias,
        name,
        spec,
        unit,
        unit_price,
        quote_date
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    rows = [tuple(
        None if (isinstance(v, float) and pd.isna(v)) else v
        for v in row
    ) for row in df.itertuples(index=False, name=None)]

    inserted = 0
    skipped: list[str] = []
    with get_connection(DB_NAME) as conn:
        with conn.cursor() as cursor:
            for i, row in enumerate(rows):
                try:
                    cursor.execute(insert_sql, row)
                    inserted += 1
                except Exception as e:
                    skipped.append(f"第 {i+1} 筆（{row[6]}，單價={row[9]}）：{e}")
    return inserted, skipped


def build_search_query(keyword: str, system_filter: str, sub_system_filter: str):
    conditions = []
    params = []

    if keyword:
        pattern = f"%{keyword.strip().upper()}%"
        conditions.append("(UPPER(name) LIKE %s OR UPPER(spec) LIKE %s OR UPPER(vendor) LIKE %s OR UPPER(vendor_full) LIKE %s OR UPPER(sub_system) LIKE %s OR UPPER(quote_no) LIKE %s OR UPPER(alias) LIKE %s)")
        params.extend([pattern] * 7)

    if system_filter and system_filter != "全部":
        conditions.append("system = %s")
        params.append(system_filter)

    if sub_system_filter and sub_system_filter != "全部":
        conditions.append("sub_system = %s")
        params.append(sub_system_filter)

    where_clause = " AND ".join(conditions) if conditions else "1"
    sql = f"""
    SELECT id, system, sub_system, vendor, name, spec, unit, unit_price, quote_date
    FROM materials
    WHERE {where_clause}
    ORDER BY id DESC
    LIMIT 100000
    """
    return sql, params


def query_materials(keyword: str, system_filter: str, sub_system_filter: str) -> pd.DataFrame:
    ensure_database_and_table()
    sql, params = build_search_query(keyword.strip(), system_filter, sub_system_filter)
    with get_connection(DB_NAME) as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
    return pd.DataFrame(rows)


def delete_materials(ids: list[int]) -> int:
    if not ids:
        return 0
    ensure_database_and_table()
    placeholders = ",".join(["%s"] * len(ids))
    sql = f"DELETE FROM materials WHERE id IN ({placeholders})"
    with get_connection(DB_NAME) as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, ids)
            deleted = cursor.rowcount
    return deleted


def truncate_materials():
    ensure_database_and_table()
    with get_connection(DB_NAME) as conn:
        with conn.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE materials")


def reset_search_filters():
    for key in ("filter_keyword", "filter_sys_major", "filter_sys_sub"):
        st.session_state.pop(key, None)
    st.session_state.pop("search_results", None)
    st.session_state.pop("search_keyword", None)


@st.cache_data(ttl=300)
def load_system_options() -> list[str]:
    ensure_database_and_table()
    with get_connection(DB_NAME) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT DISTINCT system FROM materials WHERE system IS NOT NULL AND system != '' ORDER BY system")
            rows = cursor.fetchall()
    return ["全部"] + [r["system"] for r in rows]


@st.cache_data(ttl=300)
def load_sub_system_options(system: str) -> list[str]:
    ensure_database_and_table()
    with get_connection(DB_NAME) as conn:
        with conn.cursor() as cursor:
            if system and system != "全部":
                cursor.execute(
                    "SELECT DISTINCT sub_system FROM materials WHERE sub_system IS NOT NULL AND sub_system != '' AND system = %s ORDER BY sub_system",
                    (system,),
                )
            else:
                cursor.execute("SELECT DISTINCT sub_system FROM materials WHERE sub_system IS NOT NULL AND sub_system != '' ORDER BY sub_system")
            rows = cursor.fetchall()
    return ["全部"] + [r["sub_system"] for r in rows]


def load_all_materials() -> pd.DataFrame:
    ensure_database_and_table()
    with get_connection(DB_NAME) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, system, sub_system, vendor, name, spec, unit, unit_price, quote_date FROM materials ORDER BY id DESC LIMIT 100000")
            rows = cursor.fetchall()
    return pd.DataFrame(rows)


# 側邊欄
with st.sidebar:
    st.header("⚙️ 設定")
    search_type = st.radio("選擇功能", ["查詢", "匯入", "刪除"])
    st.markdown("---")
    if st.button("登出", use_container_width=True):
        st.session_state.clear()
        st.rerun()

try:
    ensure_database_and_table()
except Exception as exc:
    st.sidebar.error(str(exc))

RESULT_COLUMNS = {
    "id": st.column_config.NumberColumn("ID", width="small", format="%d"),
    "system": st.column_config.TextColumn("系統大類"),
    "sub_system": st.column_config.TextColumn("系統子類"),
    "vendor": st.column_config.TextColumn("廠商簡稱"),
    "name": st.column_config.TextColumn("品名"),
    "spec": st.column_config.TextColumn("規格"),
    "unit": st.column_config.TextColumn("單位"),
    "unit_price": st.column_config.NumberColumn("單價", format="%.2f"),
    "quote_date": st.column_config.DateColumn("日期"),
}

if search_type == "查詢":
    st.subheader("🔍 搜尋材料")

    for _k, _v in [("filter_keyword", ""), ("filter_sys_major", "全部"), ("filter_sys_sub", "全部")]:
        if _k not in st.session_state:
            st.session_state[_k] = _v

    if st.session_state.pop("reset_search_filters_requested", False):
        reset_search_filters()

    col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 1])
    with col1:
        keyword = st.text_input("輸入關鍵字（品名/規格/廠商/系統子類）", key="filter_keyword")
    with col2:
        try:
            system_options = load_system_options()
        except Exception:
            system_options = ["全部"]
        sys_major = st.selectbox("系統大類", system_options, key="filter_sys_major")
    with col3:
        try:
            sub_system_options = load_sub_system_options(sys_major)
        except Exception:
            sub_system_options = ["全部"]
        sys_sub = st.selectbox("系統子類", sub_system_options, key="filter_sys_sub")
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        search_clicked = st.button("搜尋", use_container_width=True)
    with col5:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("清除篩選", use_container_width=True):
            st.session_state["reset_search_filters_requested"] = True
            st.rerun()

    if search_clicked:
        try:
            st.session_state["search_results"] = query_materials(keyword, sys_major, sys_sub)
        except Exception as exc:
            st.error(f"查詢失敗：{exc}")
            st.session_state.pop("search_results", None)
            st.session_state.pop("search_keyword", None)

    if "search_results" in st.session_state:
        results = st.session_state["search_results"]
        if results.empty:
            st.warning("找不到符合條件的資料。")
        else:
            st.success(f"查詢完成，共 {len(results)} 筆資料。")
            st.dataframe(results, use_container_width=True, hide_index=True, column_config=RESULT_COLUMNS)
            csv = results.to_csv(index=False, encoding="utf-8-sig")
            st.download_button("下載 CSV", csv, file_name="search_results.csv", mime="text/csv")

elif search_type == "匯入":
    st.subheader("📤 匯入 Excel 或 CSV 檔案")
    uploaded_file = st.file_uploader("上傳 Excel 或 CSV 檔案", type=["xlsx", "xls", "csv"])

    if uploaded_file:
        st.success(f"✅ 已選擇檔案: {uploaded_file.name}")
        if st.button("開始匯入"):
            try:
                if uploaded_file.name.lower().endswith(".csv"):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                inserted, skipped = import_dataframe(df)
                st.success(f"匯入完成，共 {inserted} 筆成功。")
                if skipped:
                    st.warning(f"跳過 {len(skipped)} 筆有問題的資料：")
                    for msg in skipped[:20]:
                        st.text(msg)
            except Exception as exc:
                st.error(f"匯入失敗：{exc}")

elif search_type == "刪除":
    st.subheader("🗑️ 批次刪除")
    st.warning("⚠️ 此操作無法復原，請謹慎使用。")

    try:
        all_data = load_all_materials()
        if all_data.empty:
            st.info("目前沒有可刪除的資料。")
        else:
            select_all = st.checkbox("全選", key="delete_select_all")
            all_data.insert(0, "勾選", select_all)
            edited = st.data_editor(
                all_data,
                column_config={
                    "勾選": st.column_config.CheckboxColumn("勾選", help="勾選要刪除的項目", width="small"),
                    **RESULT_COLUMNS,
                },
                disabled=["id", "system", "sub_system", "vendor", "name", "spec", "unit", "unit_price", "quote_date"],
                hide_index=True,
                use_container_width=True,
            )

            selected_rows = edited[edited["勾選"] == True]
            selected_count = len(selected_rows)

            col_info, col_btn = st.columns([3, 1])
            with col_info:
                if selected_count > 0:
                    st.info(f"已選擇 {selected_count} 筆，按右側按鈕確認刪除。")
            with col_btn:
                if st.button("確認刪除", disabled=(selected_count == 0), type="primary", use_container_width=True):
                    deleted = delete_materials(selected_rows["id"].tolist())
                    st.success(f"已刪除 {deleted} 筆資料。")
                    st.session_state.pop("search_results", None)
                    st.rerun()
    except Exception as exc:
        st.error(f"刪除失敗：{exc}")

    st.markdown("---")
    st.markdown("#### 危險操作")
    st.error("⚠️ 清空全部資料並將 ID 重置為 1，此操作**無法復原**。")
    confirm = st.checkbox("我確認要清空所有資料並重置 ID", key="confirm_truncate")
    if st.button("清空並重置 ID", disabled=not confirm, type="primary"):
        try:
            truncate_materials()
            st.success("已清空所有資料，ID 已重置為 1，請重新匯入。")
            st.session_state.pop("search_results", None)
            st.rerun()
        except Exception as exc:
            st.error(f"操作失敗：{exc}")

# 頁尾
st.markdown("---")
st.markdown("""
### 📋 功能說明
- **查詢**：搜尋材料價格資訊
- **匯入**：批次匯入 Excel/CSV 檔案
- **刪除**：批次刪除選定項目

### 🔐 安全
- 所有資料使用 SSL 加密傳輸
- 支援環境變數管理敏感資訊
""")
