# 人物誌設計師 V2

Streamlit 的 BYOK 人物誌設計工具；入口為 `app.py`。未填金鑰時只顯示啟動與金鑰設定頁；進入人物誌編輯及 AI 生成需要自行提供 Google Gemini API Key。

## 模型與資料流

- 預設穩定版 `gemini-3.8-flash`；支援 `gemini-3.5-flash-lite`，並保留 `gemini-2.5-flash` 給具存取權限的既有帳號。清單依帳號模型 metadata 篩選。
- 不再選用已停用的 Gemini 1.5 / 2.0。備援只使用帳號清單內的支援模型，僅模型 404 觸發備援；認證、配額或其他錯誤會停止。
- 金鑰檢查只讀模型清單，不以 PING 產生內容。清單可讀不代表實際生成或配額已通過。
- Key 會經 Streamlit 伺服器向 Google API 認證；生成會傳送輸入內容，可能依帳號計費。勿輸入敏感資料。
- 使用 `google-genai`；依賴見 `requirements.txt`，本次不升版或新增 Gemini SDK。

2026-10-09 核對官方來源：Gemini 1.5 系列於 2025-09-29 停用、Gemini 2.0 Flash 於 2026-06-01 停用；3.8 Flash 穩定版發布於 2026-09-02、3.5 Flash Lite 於 2026-07-21。帳號可用性仍須個別驗證。

- https://ai.google.dev/gemini-api/docs/changelog
- https://ai.google.dev/gemini-api/docs/deprecations
- https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash
- https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite

## 無付費回歸

```bash
python -m pytest -q test_app.py tests/test_model_routing.py
```

測試禁止外部網路，使用模型 metadata 與生成 client 替身；包括新舊 session 首頁、金鑰驗證不生成內容、只對 404 備援及 JSON 清理。真實 BYOK、圖片生成流程、匯出及正式部署版本尚未驗證。
