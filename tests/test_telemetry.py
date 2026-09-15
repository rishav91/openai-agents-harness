from equity_harness.telemetry import _traces_endpoint, setup_telemetry, shutdown_telemetry


def test_traces_endpoint_appends_path():
    assert _traces_endpoint("http://127.0.0.1:4318") == "http://127.0.0.1:4318/v1/traces"
    assert (
        _traces_endpoint("http://127.0.0.1:4318/v1/traces")
        == "http://127.0.0.1:4318/v1/traces"
    )


def test_setup_without_endpoint_does_not_raise(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    tracer = setup_telemetry("equity-harness-test")
    with tracer.start_as_current_span("harness.run"):
        pass
    shutdown_telemetry()
