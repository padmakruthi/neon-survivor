# GoldenBatch AI — Frontend (HTML/CSS/JS)

**Team DeepThinkers · IARE · AVEVA National AI/ML Hackathon**

## How to Run

1. Unzip this folder
2. Open `index.html` directly in your browser
3. That's it — no installation needed!

## Login
- Use **any email + any password**
- Select your role: **Operator / Engineer / Manager**

## Pages & Features

| Page | Who Can See | What It Does |
|------|-------------|--------------|
| Overview | All | KPI cards, dissolution chart, recent predictions, recent messages |
| Batch Predictor | All | Enter 8 parameters → get predicted quality + pass/fail + recommendations |
| Golden Signature | All | Best historical batch (T056), top 5 Pareto archive |
| Carbon Tracker | Engineer + Manager | Energy estimates, CO₂ tracking, regulatory compliance |
| Messages | All | Send messages to team, quick alerts, full message history |

## Role Differences
- **Operator** — Can predict batches, send messages, accept/reject recommendations
- **Engineer** — Everything + can see Carbon Tracker, edit thresholds
- **Manager** — Everything + can set carbon limits, full access

## Tech
- Pure HTML + CSS + JavaScript
- No frameworks, no npm, no installation
- Google Fonts (Syne + DM Sans) loaded from CDN
- Charts drawn on HTML5 Canvas

## Prediction Model
The batch predictor uses linear regression coefficients derived from the 60-batch dataset. Key relationships:
- Moisture Content is the strongest predictor of Dissolution Rate (corr: -0.988)
- Compression Force directly drives Hardness and inversely affects Dissolution
- Energy is estimated from Compression Force × Machine Speed proxy
