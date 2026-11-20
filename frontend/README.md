# ServiceYield AI — Frontend Dashboard (Decision Replay)

Decision Replay and Workshop Control Tower interface for **ServiceYield AI**, an advisory decision-intelligence platform for automotive dealership fixed operations.

## Technology Stack

- **Framework:** React 18 + TypeScript
- **Build Tool:** Vite 5
- **Styling:** Tailwind CSS + PostCSS + Autoprefixer
- **Icons:** Lucide React

## Getting Started

### Installation

```bash
cd frontend
npm install
```

### Development Server

```bash
npm run dev
```

Runs the development server at `http://localhost:3000`.

### Production Build

```bash
npm run build
```

Performs TypeScript type-checking and creates an optimized production bundle in `dist/`.

## Architecture & Scope

- **Stage 1 (Active):** Workshop Control Tower — displays simulated 1:15 PM fixed ops telemetry, active bay occupancies, technician statuses, and RO parts readiness classifications.
- **Stages 2–7 (Upcoming):** Navigation placeholders for subsequent Decision Replay steps (Sourcing Search, Dynamic Schedule, Replay Execution, etc.).
- **Synthetic Data Disclaimer:** Operates solely on synthetic benchmark data (S-MATH-01). No live Tekion API integration or real dealership customer records.
