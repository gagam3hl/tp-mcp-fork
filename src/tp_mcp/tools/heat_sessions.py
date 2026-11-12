"""Heat-training sessions over a date range (rt5).

For heat-adaptation questions across weeks ("does my heart rate at the same
core temperature drop?", "how many Zone 3 minutes did I get?") one compact row
per session with CORE sensor data. Each workout is analysed in light mode
(downsampled charts, no laps, no file): two requests per workout.
"""

from typing import Any

from pydantic import ValidationError

from tp_mcp.tools._validation import DateRangeInput, format_validation_error
from tp_mcp.tools.analyze import tp_analyze_workout
from tp_mcp.tools.workouts import tp_get_workouts

MAX_WORKOUTS = 40
MIN_DURATION_H = 0.25
ZONE3_TARGET_MIN = 45


def _error(code: str, message: str) -> dict[str, Any]:
    return {"isError": True, "error_code": code, "message": message}


def _total(analysis: dict[str, Any], name: str) -> float | None:
    value = ((analysis.get("totals") or {}).get(name) or {}).get("value")
    return round(float(value), 1) if isinstance(value, (int, float)) else None


def _session_row(workout: dict[str, Any], analysis: dict[str, Any], heat: dict[str, Any]) -> dict[str, Any]:
    core, hsi = heat["core_temp_c"], heat.get("heat_strain_index") or {}
    row = {
        "date": workout.get("date"),
        "workout_id": workout.get("id"),
        "sport": workout.get("sport"),
        "title": (workout.get("title") or "")[:60],
        "duration_min": round((workout.get("duration_actual") or 0) * 60),
        "tss": workout.get("tss_actual"),
        "ambient_avg_c": (heat.get("ambient_temp_c") or {}).get("avg"),
        "core_start_c": core["start"], "core_avg_c": core["avg"], "core_max_c": core["max"],
        "core_rise_c": core["rise"], "core_min_at_or_above_38_5": core["minutes_at_or_above"]["38.5"],
        "hsi_avg": hsi.get("avg"), "hsi_max": hsi.get("max"),
        "zone_minutes": hsi.get("minutes_in_zone"), "minutes_to_zone3": hsi.get("minutes_to_zone3"),
        "skin_avg_c": (heat.get("skin_temp_c") or {}).get("avg"),
        "core_skin_gradient_c": (heat.get("skin_temp_c") or {}).get("core_skin_gradient_avg"),
        "hr_avg": _total(analysis, "Avg heart rate"), "np_w": _total(analysis, "NP"),
    }
    return {k: v for k, v in row.items() if v is not None}


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    zone3 = [((r.get("zone_minutes") or {}).get("zone3") or 0.0) for r in rows]
    return {
        "sessions_with_core_data": len(rows),
        "zone3_minutes_total": round(sum(zone3), 1),
        f"sessions_with_zone3_at_least_{ZONE3_TARGET_MIN}_min": sum(1 for z in zone3 if z >= ZONE3_TARGET_MIN),
        "zone4_minutes_total": round(sum(((r.get("zone_minutes") or {}).get("zone4") or 0.0) for r in rows), 1),
    }


async def tp_get_heat_sessions(start_date: str, end_date: str) -> dict[str, Any]:
    """Compact heat metrics for every completed workout with CORE sensor data in a date range.

    Args:
        start_date: Start date (YYYY-MM-DD).
        end_date: End date (YYYY-MM-DD), at most 90 days after start_date.

    Returns:
        Dict with one row per heat session, totals, and truncation/skip info.
    """
    try:
        DateRangeInput(start_date=start_date, end_date=end_date)  # type: ignore[arg-type]
    except (ValidationError, ValueError) as e:
        msg = format_validation_error(e) if isinstance(e, ValidationError) else str(e)
        return _error("VALIDATION_ERROR", msg)
    listing = await tp_get_workouts(start_date, end_date, workout_filter="completed")
    if listing.get("isError"):
        return listing
    candidates = sorted(
        (w for w in listing.get("workouts", []) if (w.get("duration_actual") or 0) >= MIN_DURATION_H),
        key=lambda w: (w.get("date") or "", str(w.get("id"))),
    )
    return await _collect(candidates, start_date, end_date)


async def _collect(candidates: list[dict[str, Any]], start_date: str, end_date: str) -> dict[str, Any]:
    batch, rest = candidates[:MAX_WORKOUTS], candidates[MAX_WORKOUTS:]
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    without_core = 0
    for workout in batch:
        analysis = await tp_analyze_workout(str(workout.get("id")), light=True)
        if analysis.get("isError"):
            errors.append({"workout_id": str(workout.get("id")), "error": str(analysis.get("error_code"))})
            continue
        heat = analysis.get("heat")
        if heat is None:
            without_core += 1
            continue
        rows.append(_session_row(workout, analysis, heat))
    result: dict[str, Any] = {
        "date_range": {"start": start_date, "end": end_date},
        "sessions": rows, "summary": _summary(rows),
        "workouts_checked": len(batch), "workouts_without_core_data": without_core,
        "note": "Values from downsampled time series; use tp_analyze_workout for one session in full detail.",
    }
    if errors:
        result["errors"] = errors
    if rest:
        result["truncated"] = True
        result["next_start_date"] = rest[0].get("date")
        result["message"] = f"Only the first {MAX_WORKOUTS} workouts were checked; call again from next_start_date."
    return result
