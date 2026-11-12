"""Left/right power balance analysis over the device files of workouts.

rt5: takes workout IDs instead of local file paths (#185 took `file_paths`).
The device file of each workout is fetched from TrainingPeaks and parsed in
memory — the server never reads files from its own disk on a caller's behalf,
which on a shared server could expose other users' credentials (see #194).
"""

from typing import Any

from tp_mcp.client import TPClient
from tp_mcp.fit import (
    FitDataError,
    bucket_left_right_power,
    flatten_workouts,
    format_power_buckets,
    load_workout_bytes,
    summarize_power_buckets,
)

MAX_WORKOUTS = 20


def _error(code: str, message: str) -> dict[str, Any]:
    return {"isError": True, "error_code": code, "message": message}


def _validate(workout_ids: list[str], bucket_size: int, sample_seconds: int | None) -> dict[str, Any] | None:
    if not workout_ids or not isinstance(workout_ids, list):
        return _error("VALIDATION_ERROR", "workout_ids must contain at least one workout ID.")
    if len(workout_ids) > MAX_WORKOUTS:
        return _error("VALIDATION_ERROR", f"At most {MAX_WORKOUTS} workouts per call.")
    if not all(str(w).isdigit() for w in workout_ids):
        return _error("VALIDATION_ERROR", "workout_ids must be numeric workout IDs.")
    if not isinstance(bucket_size, int) or bucket_size <= 0:
        return _error("VALIDATION_ERROR", "bucket_size must be a positive integer.")
    if sample_seconds is not None and (not isinstance(sample_seconds, int) or sample_seconds <= 0):
        return _error("VALIDATION_ERROR", "sample_seconds must be a positive integer.")
    return None


async def _device_file_bytes(client: TPClient, athlete_id: int, workout_id: str) -> bytes:
    """Fetch the first device file of a workout from TrainingPeaks."""
    details = await client.get(f"/fitness/v6/athletes/{athlete_id}/workouts/{workout_id}/details")
    infos = details.data.get("workoutDeviceFileInfos") if isinstance(details.data, dict) else None
    if details.is_error or not infos:
        raise FitDataError("workout has no device file")
    file_id = infos[0].get("fileId") if isinstance(infos[0], dict) else None
    if file_id is None:
        raise FitDataError("workout has no device file")
    raw = await client.get_raw(f"/fitness/v6/athletes/{athlete_id}/workouts/{workout_id}/rawfiledata/{file_id}")
    if raw.is_error:
        raise FitDataError("device file could not be downloaded")
    return raw.content


async def tp_analyze_power_balance(
    workout_ids: list[str],
    bucket_size: int = 50,
    sample_seconds: int | None = None,
) -> dict[str, Any]:
    """Analyze left/right power balance by power bucket from the workouts' device files.

    Args:
        workout_ids: Workout IDs (from tp_get_workouts); their device files are combined.
        bucket_size: Width of each total-power bucket in watts.
        sample_seconds: Seconds per data point, used to report durations.

    Returns:
        Dict with per-bucket balance rows, a text table, and any skipped workouts.
    """
    invalid = _validate(workout_ids, bucket_size, sample_seconds)
    if invalid:
        return invalid
    workouts = []
    failed: list[dict[str, str]] = []
    async with TPClient() as client:
        athlete_id = await client.ensure_athlete_id()
        if not athlete_id:
            return _error("AUTH_INVALID", "Could not get athlete ID. Re-authenticate.")
        for workout_id in (str(w) for w in workout_ids):
            try:
                workouts.append(load_workout_bytes(await _device_file_bytes(client, athlete_id, workout_id)))
            except ImportError:
                return _error("DEPENDENCY_MISSING", "The 'fitparse' package is required to analyze FIT files.")
            except FitDataError as e:
                failed.append({"workout_id": workout_id, "error": str(e)})
    if not workouts:
        return _error("VALIDATION_ERROR", f"No device files could be analyzed: {failed}")
    return _result(workouts, failed, bucket_size, sample_seconds)


def _result(
    workouts: list, failed: list[dict[str, str]], bucket_size: int, sample_seconds: int | None
) -> dict[str, Any]:
    points = flatten_workouts(workouts)
    buckets = bucket_left_right_power(points, bucket_size)
    result = summarize_power_buckets(buckets, sample_seconds)
    result.update({
        "workouts_analyzed": len(workouts),
        "records_total": len(points),
        "bucket_size": bucket_size,
        "text": format_power_buckets(buckets, sample_seconds),
    })
    if failed:
        result["skipped_workouts"] = failed
    if not buckets:
        result["message"] = "No records contained both power and left/right balance (needs a dual-sided power meter)."
    return result
