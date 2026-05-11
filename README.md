---
title: 英建工程 材料價格查詢系統
emoji: 🏗️
colorFrom: blue
colorTo: gray
sdk: docker
pinned: false
---
# 英建工程 材料價格查詢系統

## 功能特色

- **價格查詢**：支援按系統大類（電氣、消防、空調）和關鍵字搜尋材料價格
- **資料匯出**：將搜尋結果匯出為 CSV 格式檔案
- **Excel 匯入**：批次匯入 Excel/CSV 檔案到 TiDB 資料庫
- **批次刪除**：勾選多筆資料進行批次刪除操作
- **Hugging Face 整合**：自動將新匯入的資料同步到 Hugging Face 資料集

## 系統需求

- PHP 7.4+
- MySQL/MariaDB 或 TiDB
- SSL 憑證檔案 (isrgrootx1.pem)

## 快速部署 - Hugging Face Spaces

### 方式一：Streamlit 部署（✨ 推薦 - 最簡單）

1. 在 Hugging Face 建立新的 Space
   - 選擇「Streamlit」作為空間類型
   - 克隆此 Git 倉庫

2. 將 `streamlit_requirements.txt` 改名為 `requirements.txt`
   ```bash
   # 或在 HF 中直接編輯 requirements.txt
   ```

3. 在 Space 中設定 Secrets
   - `DB_PASS` = 您的 TiDB 密碼

4. 自動部署
   - Space 會自動運行 `streamlit_app.py`
   - 應用將在 `https://your-username-spacename.hf.space` 上運行

### 方式二：Docker 部署

1. 在 Hugging Face 建立新的 Space
   - 選擇「Docker」作為空間類型
   - 克隆此 Git 倉庫

2. 在 Space 中設定 Secrets
   - `DB_PASS` = 您的 TiDB 密碼
   - `HUGGINGFACE_TOKEN` (可選)

3. 自動部署
   - Space 將自動構建 Docker 映像
   - 應用將在 `https://your-username-spacename.hf.space` 上運行

### 方式三：本地部署

```bash
# 構建 Docker 映像
docker build -t price-query .

# 運行容器
docker run -e DB_PASS=your_password -p 7860:7860 price-query
```

## 安裝步驟

1. **下載專案**
   ```bash
   git clone <repository-url>
   cd price_query
   ```

2. **安裝依賴**
   ```bash
   # 如果有 Composer
   composer install

   # 或手動安裝 PhpSpreadsheet
   # 檔案已包含在 vendor/ 目錄中
   ```

3. **資料庫設定**
   - 確保 TiDB 或 MySQL 連線資訊正確
   - 複製 `.env.example` 為 `.env`
   - 設定以下環境變數：
     - `DB_HOST`：資料庫主機，預設 `127.0.0.1`
     - `DB_PORT`：資料庫連接埠，預設 `3306`
     - `DB_USER`：資料庫使用者，預設 `root`
     - `DB_PASS`：資料庫密碼（必要）
     - `DB_NAME`：資料庫名稱，預設 `price_query`
     - `HUGGINGFACE_TOKEN`：Hugging Face Token（可選）

4. **SSL 憑證**
   - 下載 ISRG Root X1 憑證到專案根目錄
   - 檔案名稱：`isrgrootx1.pem`

## 使用說明

### 基本查詢
1. 在首頁輸入關鍵字或選擇系統大類
2. 點擊「立即搜尋」按鈕
3. 系統會顯示符合條件的材料資料

### 匯出資料
1. 執行搜尋後，會出現「匯出 Excel (.csv)」按鈕
2. 點擊按鈕下載搜尋結果

### 匯入 Excel
1. 點擊「匯入 Excel」按鈕
2. 選擇要匯入的 Excel/CSV 檔案
3. 確保檔案格式正確（欄位順序：系統大類, 品名, 規格, 單位, 未稅單價, 更新時間）
4. 點擊「開始匯入」

### 批次刪除
1. 在搜尋結果中勾選要刪除的資料
2. 點擊「批次刪除」按鈕
3. 確認刪除操作

## 資料格式說明

### Excel/CSV 檔案格式
檔案應包含以下欄位（順序必須正確）：

| 欄位名稱 | 必填 | 說明 |
|---------|------|------|
| 系統大類 | 否 | 電氣/消防/空調 |
| 品名 | 是 | 材料名稱 |
| 規格 | 否 | 材料規格 |
| 單位 | 否 | 計量單位 |
| 未稅單價 | 是 | 數值型別 |
| 更新時間 | 否 | 日期格式 (YYYY-MM-DD) |

### 資料庫結構
```sql
CREATE TABLE materials (
    id INT AUTO_INCREMENT PRIMARY KEY,
    system VARCHAR(50),
    name VARCHAR(255) NOT NULL,
    spec VARCHAR(255),
    unit VARCHAR(50),
    unit_price DECIMAL(10,2) NOT NULL,
    quote_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Hugging Face 整合

系統支援自動將匯入的資料同步到 Hugging Face 資料集：

1. 設定環境變數 `HUGGINGFACE_TOKEN`
2. 修改 `import.php` 中的資料集 URL
3. 每次成功匯入資料後，系統會自動推送資料到 Hugging Face

## 安全注意事項

- 所有資料庫操作使用 PDO 預處理語句防止 SQL 注入
- 檔案上傳限制為 Excel/CSV 格式
- 敏感資訊使用環境變數管理
- SSL 連線確保資料傳輸安全

## 故障排除

### 常見問題

1. **資料庫連線失敗**
   - 檢查 TiDB 連線資訊
   - 確認 SSL 憑證檔案存在
   - 驗證環境變數設定

2. **Excel 匯入失敗**
   - 檢查檔案格式是否正確
   - 確認欄位順序和資料型別
   - 查看 PHP 錯誤日誌

3. **Hugging Face 同步失敗**
   - 檢查 API Token 是否正確
   - 確認資料集 URL 和權限
   - 查看網路連線狀態

## 技術支援

如有問題請聯絡技術支援團隊。