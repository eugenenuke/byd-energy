# Service lifecycle regressions

Use Python 3.14 in an isolated environment:

```sh
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements-test.txt
.venv/bin/python -m pytest
```

Alternatively, `uv venv --python 3.14 .venv` and
`uv pip install --python .venv/bin/python -r requirements-test.txt` supply
the same pinned direct dependencies. The complete tested dependency snapshot
is retained with the private evidence packet.

Tests use actual Home Assistant config-entry setup, six platforms, service
registration/calls, coordinator update semantics, options reload and unload.
API read responses are synthetic. Notification publication is suppressed as
an unrelated boundary. Internet sockets are blocked; local Unix sockets are
permitted for asyncio. No account credentials, devices or cloud calls are
needed. This suite does not start the HA frontend or prove device behavior.

On the original integration, the 12 cases produce seven behavioral failures
and five passing controls. The proposed service implementation passes all 12.
The cases include in-flight reads finishing after unload; the service skips
entries unloaded before their turn but does not cancel reads already running.
