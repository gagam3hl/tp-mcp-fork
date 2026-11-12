"""Tests for left/right power balance analysis (rt5: device files by workout ID, in memory)."""

import gzip
from unittest.mock import AsyncMock, patch

import pytest

from tp_mcp.client.http import APIResponse, RawResponse
from tp_mcp.fit import (
    FitDataError,
    WorkoutDataPoint,
    bucket_left_right_power,
    decode_left_right_balance,
    format_power_buckets,
)
from tp_mcp.fit import parser as fit_parser
from tp_mcp.tools import power_balance
from tp_mcp.tools.power_balance import tp_analyze_power_balance


def _pt(power, balance):
    return WorkoutDataPoint(power=power, left_right_balance=balance)


def test_decode_balance_left_and_right_flag():
    assert decode_left_right_balance(48, 200) == {
        "left_pct": 48, "right_pct": 52, "left_watts": 96.0, "right_watts": 104.0,
    }
    assert decode_left_right_balance(0x80 | 48)["right_pct"] == 48


def test_bucketing_skips_unusable_and_groups():
    pts = [_pt(210, 50), _pt(240, 50), _pt(None, 50), _pt(100, None), _pt(60, 50)]
    buckets = bucket_left_right_power(pts, 50)
    assert buckets[(200, 250)]["datapoints"] == 2
    assert buckets[(50, 100)]["datapoints"] == 1
    assert buckets[(0, 50)]["datapoints"] == 0
    assert "Left 50.00% / Right 50.00%" in format_power_buckets(buckets, 1)


def test_bucket_size_validation():
    with pytest.raises(ValueError):
        bucket_left_right_power([], 0)


def test_fit_bytes_plain_gzip_and_limits(monkeypatch):
    assert fit_parser._fit_bytes(b"plain") == b"plain"
    assert fit_parser._fit_bytes(gzip.compress(b"inner")) == b"inner"
    with pytest.raises(FitDataError):
        fit_parser._fit_bytes(b"\x1f\x8bnot really gzip")
    monkeypatch.setattr(fit_parser, "MAX_FIT_BYTES", 10)
    with pytest.raises(FitDataError):
        fit_parser._fit_bytes(b"x" * 11)  # raw too large
    with pytest.raises(FitDataError):
        fit_parser._fit_bytes(gzip.compress(b"y" * 1000))  # decompresses beyond the cap


def test_not_a_fit_file_raises_fit_data_error():
    with pytest.raises(FitDataError):
        fit_parser.load_workout_bytes(gzip.compress(b"not a fit file"))


def test_schema_takes_workout_ids_not_paths():
    from tp_mcp.server import TOOLS

    tool = next(t for t in TOOLS if t.name == "tp_analyze_power_balance")
    props = set(tool.input_schema["properties"])
    assert "workout_ids" in props and not props & {"file_paths", "file_path", "output_path"}
    assert tool.input_schema["required"] == ["workout_ids"]


@pytest.mark.parametrize("ids, kwargs", [([], {}), (["x"], {}), (["1"], {"bucket_size": 0}),
                                         (["1"], {"sample_seconds": -1}), ([str(i) for i in range(21)], {})])
async def test_tool_validation(ids, kwargs):
    with patch("tp_mcp.tools.power_balance.TPClient") as mock_client:
        result = await tp_analyze_power_balance(ids, **kwargs)
    assert result["isError"] and result["error_code"] == "VALIDATION_ERROR"
    mock_client.assert_not_called()


def _client(details, raw):
    inst = AsyncMock()
    inst.ensure_athlete_id = AsyncMock(return_value=123)
    inst.get = AsyncMock(return_value=details)
    inst.get_raw = AsyncMock(return_value=raw)
    return inst


async def test_fetches_device_file_by_workout_id_and_analyzes(monkeypatch):
    details = APIResponse(success=True, data={"workoutDeviceFileInfos": [{"fileId": 77}]})
    raw = RawResponse(success=True, content=b"FITBYTES")
    seen = []
    monkeypatch.setattr(power_balance, "load_workout_bytes", lambda data: seen.append(data) or [_pt(210, 48)])
    with patch("tp_mcp.tools.power_balance.TPClient") as mock_client:
        inst = _client(details, raw)
        mock_client.return_value.__aenter__.return_value = inst
        result = await tp_analyze_power_balance(["555"])
    assert seen == [b"FITBYTES"]
    inst.get.assert_awaited_with("/fitness/v6/athletes/123/workouts/555/details")
    inst.get_raw.assert_awaited_with("/fitness/v6/athletes/123/workouts/555/rawfiledata/77")
    assert result["workouts_analyzed"] == 1 and result["buckets"][-1]["left_pct"] == 48.0


async def test_workout_without_device_file_is_skipped():
    details = APIResponse(success=True, data={"workoutDeviceFileInfos": []})
    with patch("tp_mcp.tools.power_balance.TPClient") as mock_client:
        inst = _client(details, None)
        mock_client.return_value.__aenter__.return_value = inst
        result = await tp_analyze_power_balance(["555"])
    assert result["isError"] and "no device file" in result["message"]
    inst.get_raw.assert_not_called()
