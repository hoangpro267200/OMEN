# OMEN Demo UI

Presentation-grade dashboard for showing how OMEN processes prediction market signals into risk intelligence. Supports **Demo mode** (mock data) and **Live mode** (real backend).

## Run locally

```bash
npm install
npm run dev
```

Open http://localhost:5174 (or the port Vite prints) and use **Data** / **Live** in the header to switch data source.

## Live mode — dashboard nhận data thật

Để dashboard hiển thị số liệu thật (Signals Today, Hot Path OK, Activity):

1. **Chạy backend OMEN** (cùng repo, từ thư mục gốc):
   ```bash
   # Từ thư mục gốc OMEN
   make up
   # hoặc chạy trực tiếp:
   python -m uvicorn omen.main:app --host 0.0.0.0 --port 8000
   ```
2. **Cấu hình frontend trỏ tới backend** — tạo file `omen-demo/.env` (copy từ `.env.example`):
   ```env
   VITE_OMEN_API_URL=http://localhost:8000/api/v1
   VITE_API_BASE=http://localhost:8000
   ```
   Nếu không set `VITE_API_BASE`, frontend sẽ gọi API lên chính origin (localhost:5174) và nhận HTML → lỗi "Live API chưa sẵn sàng".
3. **Bật Live** trong header (nhãn Data → Live). Dashboard gọi `GET /api/ui/overview`; nếu backend chưa chạy pipeline lần nào thì số liệu vẫn 0 cho đến khi có request xử lý (ví dụ từ màn Realtime signals hoặc Ingest Demo).

## Stack

- React 19 + TypeScript (Vite)
- Tailwind CSS (v4)
- Framer Motion (animations)
- Lucide React (icons)

## Layout

1. **Header** — OMEN logo + status (Demo / Processing / Signal ready)
2. **Data flow** — Input → Processing (Layers 1–4) → Output with animated particle
3. **Live signal** — Title, probability bar, confidence/severity/actionable badges, impact metrics with uncertainty
4. **Explanation chain** — Timeline of validation/translation steps (rule, status, reasoning)
5. **Affected routes** — Blocked vs alternative shipping corridors

## Build

```bash
npm run build
npm run preview
```
