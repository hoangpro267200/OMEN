# OMEN Demo UI

Presentation-grade dashboard for showing how OMEN processes prediction market signals into risk intelligence. **Demo only** — uses mock data, no live API.

## Run locally

```bash
npm install
npm run dev
```

Open http://localhost:5173 and click **Run OMEN demo** to step through the pipeline and see the signal, explanation chain, and affected routes.

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
