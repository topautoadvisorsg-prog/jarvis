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
    assert result["llm_ttft_p50_seconds"] == 1.5
    assert result["total_turn_p50_seconds"] == 5.0
    assert "private" not in serialized
    assert "transcript" not in serialized
    assert "response_text" not in serialized


def test_model_summary_reads_only_provider_and_model(tmp_path, server_mod):
    path = tmp_path / "config.yaml"
    path.write_text(
        "model:\n  provider: deepseek\n  default: deepseek-flash\nsecret: do-not-return\n",
        encoding="utf-8",
    )
    result = server_mod.read_hermes_model_config(path)
    assert result == {"provider": "deepseek", "model": "deepseek-flash"}
    assert "secret" not in json.dumps(result)
