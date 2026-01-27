# Evidence-Based Logistics Parameters

This document describes the sources and rationale for parameters used in OMEN's logistics impact translation rules. All constants are defined in `src/omen/domain/rules/translation/logistics/parameters.py` with `EvidenceRecord` entries (value, unit, source, source_date, notes). **Review and update quarterly.**

---

## Red Sea / Suez Canal

| Parameter | Value | Unit | Source | Notes |
|-----------|-------|------|--------|-------|
| `reroute_distance_increase_nm` | 3000 | nautical_miles | Clarksons Research, 2024 Red Sea Crisis Analysis | Asia–Europe via Cape vs Suez. Range: 2800–3400 nm by origin. |
| `reroute_transit_increase_days` | 10 | days | Drewry Maritime Research Q1 2024 | Average for container vessels. Range: 7–14 days by speed/port. |
| `fuel_consumption_increase_pct` | 30 | percent | Lloyd's List Intelligence, Jan 2024 | Bunker consumption for extended voyage, similar speed. |
| `freight_rate_increase_pct_base` | 15 | percent | Freightos Baltic Index historical analysis | Minimum observed. Spikes 200%+ in crisis. |
| `freight_rate_increase_pct_crisis` | 100 | percent | Freightos Baltic Index, Dec 2023–Jan 2024 | Peak during Houthi attacks; used when probability ≥ 0.7. |
| `insurance_premium_increase_pct` | 50 | percent | Lloyd's of London War Risk Premium updates | War risk for Red Sea transit; can reach 1% of hull value. |

---

## Port Closure

| Parameter | Value | Unit | Source | Notes |
|-----------|-------|------|--------|-------|
| `major_port_daily_capacity_teu` | 50 000 | TEU/day | UNCTAD Port Statistics 2023 | Top 20 global ports avg. Range: 20k–100k. |
| `congestion_buildup_rate` | 1.5 | days_delay per closure_day | Journal of Maritime Economics, 2022 | Empirical port-closure aftereffects. |
| `diversion_cost_increase_pct` | 25 | percent | Sea-Intelligence Sunday Spotlight | Cost increase to divert to alternative ports. |

---

## Strike / Labor Disruption

| Parameter | Value | Unit | Source | Notes |
|-----------|-------|------|--------|-------|
| `port_strike_productivity_loss_pct` | 60 | percent | ILWU historical data | Average productivity loss. Range: 30–100%. |
| `truck_strike_capacity_loss_pct` | 40 | percent | American Trucking Associations, 2022 | Capacity loss in major trucking strikes. |
| `strike_duration_avg_days` | 7 | days | BLS Work Stoppages data | Median duration in transportation. |

---

## Uncertainty and calibration

- **Transit time**: ±20% (0.8–1.3×) from historical variance.
- **Cost/freight**: ±30–50% (0.7–1.5×) from market volatility.
- **Calibration**: Use `HistoricalValidator` and `CalibrationReport` to compare predictions to outcomes and adjust bounds as needed.

Last structured update: 2025-01 (Phase 5). Next review: Q2 2025.
