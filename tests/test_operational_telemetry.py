import json


def test_performance_summary_is_aggregate_only(tmp_path, server_mod):
    path = tmp_path / "latency.jsonl"
    rows = [
        {
            "transcript": "private customer request",
            "response_text": "private answer",
            "llm_provider": "hermes",
            "llm_model": "hermes-agent",
            "llm_time_to_first_token_seconds": 1.0,
            "total_turn_seconds": 3.0,
            "interrupted": False,
            "errors": [],
        },
        {
            "transcript": "stop",
            "response_text": "",
            "llm_provider": "hermes",
            "llm_model": "hermes-agent",
            "llm_time_to_first_token_seconds": 2.0,
            "total_turn_seconds": 5.0,
            "interrupted": False,
            "errors": ["typed turn cancelled (barge-in or stop)"],
        },
        {
            "transcript": "another private request",
            "response_text": "",
            "llm_provider": "hermes",
            "llm_model": "hermes-agent",
            "total_turn_seconds": 7.0,
            "interrupted": False,
            "errors": ["backend failed"],
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\ninvalid\n")

    result = server_mod.read_performance(path, max_records=20)
    serialized = json.dumps(result)
    assert result["sample_count"] == 3
    assert result["successful_turns"] == 1
    assert result["interrupted_turns"] == 1
    assert result["failed_turns"] == 1
    assert result["reliability_sample_count"] == 2
    assert result["completion_success_rate_pct"] == 50.0
    assert result["llm_ttft_p50_seconds"] == 1.5
    assert result["total_turn_p50_seconds"] == 5.0
    assert "private" not in serialized
    assert "transcript" not in serialized
    assert "response_text" not in serialized


def test_performance_health_waits_for_enough_samples(server_mod):
    performance = {
        "reliability_sample_count": 2,
        "completion_success_rate_pct": 50.0,
        "llm_ttft_sample_count": 2,
        "llm_ttft_p95_seconds": 30.0,
        "total_turn_sample_count": 2,
        "total_turn_p95_seconds": 90.0,
    }
    result = server_mod.evaluate_performance_health(performance, {"min_samples": 5})
    assert result["status"] == "insufficient_data"
    assert not result["regressions"]
    assert {check["status"] for check in result["checks"]} == {"unknown"}


def test_performance_health_reports_actionable_regressions(server_mod):
    performance = {
        "reliability_sample_count": 10,
        "completion_success_rate_pct": 70.0,
        "llm_ttft_sample_count": 10,
        "llm_ttft_p95_seconds": 4.0,
        "total_turn_sample_count": 10,
        "total_turn_p95_seconds": 75.0,
    }
    result = server_mod.evaluate_performance_health(performance)
    assert result["status"] == "degraded"
    assert [item["metric"] for item in result["regressions"]] == [
        "completion_success_rate_pct",
        "total_turn_p95_seconds",
    ]


def test_performance_health_accepts_configured_healthy_window(server_mod):
    performance = {
        "reliability_sample_count": 5,
        "completion_success_rate_pct": 90.0,
        "llm_ttft_sample_count": 5,
        "llm_ttft_p95_seconds": 12.0,
        "total_turn_sample_count": 5,
        "total_turn_p95_seconds": 42.0,
    }
    result = server_mod.evaluate_performance_health(
        performance,
        {
            "min_samples": 5,
            "min_success_rate_pct": 85,
            "max_llm_ttft_p95_seconds": 13,
            "max_total_turn_p95_seconds": 45,
        },
    )
    assert result["status"] == "healthy"
    assert all(check["status"] == "pass" for check in result["checks"])


def test_model_summary_reads_only_provider_and_model(tmp_path, server_mod):
    path = tmp_path / "config.yaml"
    path.write_text(
        "model:\n  provider: deepseek\n  default: deepseek-flash\nsecret: do-not-return\n",
        encoding="utf-8",
    )
    result = server_mod.read_hermes_model_config(path)
    assert result == {"provider": "deepseek", "model": "deepseek-flash"}
    assert "secret" not in json.dumps(result)
