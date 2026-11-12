---
name: power-balance-analysis
description: Analyze left/right power balance at given watts from TrainingPeaks workouts. Use when asked about L/R balance, leg imbalance, or pedaling symmetry at specific power levels, for one workout or across many.
---

# Left/right power balance analysis

Requires a dual-sided power meter (workouts without L/R balance data return no buckets).

## Steps

1. **Find workouts**: `tp_get_workouts` with a date range. Pick the cycling workouts (they need a device file).
2. **Analyze**: `tp_analyze_power_balance` with `workout_ids` (up to 20) and optional:
   - `bucket_size` (watts per bucket, default 50; use 10-25 for fine detail around a target wattage)
   - `sample_seconds` (seconds per data point, typically 1; adds durations)
   The tool fetches each workout's device FIT file from TrainingPeaks and analyses it in memory;
   workouts without a device file are listed under `skipped_workouts`.
3. **Report**: use the `buckets` rows (`left_pct`, `right_pct`, `datapoints`, `duration`) or the ready-made `text` table.

Passing several workout IDs in one call combines them into a single bucketed result (cross-workout analysis).

## Interpreting results

- Balance is the share of total power from each leg per bucket; 50/50 is symmetric, within about 48-52% is typical.
- Ignore buckets with few `datapoints`; they are noisy.
- Compare buckets (e.g. 150-200 W vs 300-350 W) to see whether imbalance grows with effort.
- For a specific wattage, set `bucket_size` so it falls inside one bucket, e.g. 250 W with size 25 gives the 250-275 bucket.

## Reusable code

Offline helpers live in `src/tp_mcp/fit/`:

- `parser.py`: `load_workout_bytes` (FIT bytes, plain or gzipped — never local paths), `flatten_workouts`, `WorkoutDataPoint`, `decode_left_right_balance`
- `power_balance.py`: `bucket_left_right_power`, `summarize_power_buckets`, `format_power_buckets`

Add new FIT analyses (cadence, HR by power, etc.) as new modules there on top of `WorkoutDataPoint`, with a thin tool in `src/tp_mcp/tools/`.
