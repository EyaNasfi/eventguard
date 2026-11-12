"""S2-05: agent run records from n8n execution data (no network)."""

from agent.export_runs import run_record

EXECUTION = {
    "id": 9,
    "status": "success",
    "startedAt": "2026-11-13T00:00:00.000Z",
    "stoppedAt": "2026-11-13T00:00:02.500Z",
    "data": {
        "resultData": {
            "runData": {
                "When chat message received": [
                    {"data": {"main": [[{"json": {"sessionId": "smoke-1", "chatInput": "hi"}}]]}}
                ],
                "Google Gemini Chat Model": [
                    {
                        "data": {
                            "ai_languageModel": [
                                [
                                    {
                                        "json": {
                                            "tokenUsage": {
                                                "promptTokens": 100,
                                                "completionTokens": 10,
                                                "totalTokens": 110,
                                            }
                                        }
                                    }
                                ]
                            ]
                        }
                    },
                    {
                        "data": {
                            "ai_languageModel": [
                                [
                                    {
                                        "json": {
                                            "tokenUsage": {
                                                "promptTokens": 200,
                                                "completionTokens": 20,
                                                "totalTokens": 220,
                                            }
                                        }
                                    }
                                ]
                            ]
                        }
                    },
                ],
                "EventGuard gateway": [{"data": {}}, {"data": {}}],
            }
        }
    },
}


def test_run_record_sums_tokens_and_finds_the_session() -> None:
    record = run_record(EXECUTION, "editor")
    assert record["session_id"] == "smoke-1"
    assert record["model_calls"] == 2
    assert (record["prompt_tokens"], record["completion_tokens"], record["total_tokens"]) == (
        300,
        30,
        330,
    )
    assert record["latency_ms"] == 2500 and record["tool_node_runs"] == 2
    assert record["status"] == "success" and record["error"] is None


def test_run_record_keeps_the_error_message() -> None:
    failed = {
        "id": 10,
        "status": "error",
        "data": {"resultData": {"runData": {}, "error": {"message": "429"}}},
    }
    record = run_record(failed, "reader")
    assert record["error"] == "429" and record["latency_ms"] is None and record["model_calls"] == 0


def test_model_comes_from_the_workflow_that_ran() -> None:
    execution = {
        **EXECUTION,
        "workflowData": {
            "nodes": [
                {
                    "type": "@n8n/n8n-nodes-langchain.lmChatGoogleGemini",
                    "parameters": {"modelName": "models/gemini-x"},
                }
            ]
        },
    }
    assert run_record(execution, "editor")["model"] == "gemini-x"
    assert run_record(EXECUTION, "editor")["model"] is None
