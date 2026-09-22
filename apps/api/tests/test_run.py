from api import run


def test_main_uses_render_port(monkeypatch):
    calls = []
    monkeypatch.setenv("PORT", "4312")
    monkeypatch.setattr(run.uvicorn, "run", lambda *args, **kwargs: calls.append((args, kwargs)))

    run.main()

    assert calls == [
        (
            ("api.main:app",),
            {"host": "0.0.0.0", "port": 4312},
        )
    ]


def test_main_uses_local_default_port(monkeypatch):
    calls = []
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.setattr(run.uvicorn, "run", lambda *args, **kwargs: calls.append((args, kwargs)))

    run.main()

    assert calls[0][1]["port"] == 10000
