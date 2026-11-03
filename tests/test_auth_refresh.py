"""Exercise concurrent authentication through the real API request method."""

import asyncio
import base64
import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def api_module(enable_custom_integrations):
    import custom_components

    custom_components.__path__.append(
        str(Path(__file__).parents[1] / "custom_components")
    )
    from custom_components.byd_energy import api

    return api


def token(expiry, generation=0):
    """Make a synthetic JWT-shaped value; no real credentials are used."""
    payload = (
        base64.b64encode(json.dumps({"exp": expiry, "generation": generation}).encode())
        .decode()
        .rstrip("=")
    )
    return f"synthetic.{payload}.signature"


class Response:
    def __init__(self, status, data, *, wait=None, entered=None):
        self.status = status
        self.data = data
        self.wait = wait
        self.entered = entered

    async def __aenter__(self):
        await asyncio.sleep(0)
        if self.entered is not None:
            self.entered.set()
        if self.wait is not None:
            await self.wait.wait()
        return self

    async def __aexit__(self, *args):
        return False

    async def json(self):
        await asyncio.sleep(0)
        return self.data


class Session:
    """An in-memory HTTP boundary with observable request and auth counts."""

    def __init__(self, *, rejection="http", refresh_fails=False, login_fails=False):
        self.rejection = rejection
        self.refresh_fails = refresh_fails
        self.login_fails = login_fails
        self.invalid_login_refresh = False
        self.reject_all = False
        self.rejected_tokens = set()
        self.refreshes = 0
        self.logins = 0
        self.handshakes = 0
        self.requests = []
        self.latest_token = None
        self.auth_wait = None
        self.auth_entered = None
        self.late_wait = None

    def post(self, url, **kwargs):
        if url.endswith("/refresh-token"):
            self.refreshes += 1
            if self.refresh_fails:
                return Response(200, {"Success": False})
            self.latest_token = token(4102444800, self.refreshes + self.logins)
            return Response(
                200,
                {
                    "Success": True,
                    "Data": {
                        "AccessToken": self.latest_token,
                        "RefreshToken": "synthetic-refresh",
                    },
                },
                wait=self.auth_wait,
                entered=self.auth_entered,
            )
        if url.endswith("/app/GetSecurityKey"):
            self.handshakes += 1
            return Response(
                200,
                {
                    "Success": True,
                    "Data": {
                        "keyId": "synthetic-key-id",
                        "key": "0" * 32,
                    },
                },
            )
        assert url.endswith("/app-login")
        self.logins += 1
        if self.login_fails:
            return Response(401, {})
        self.latest_token = token(4102444800, self.refreshes + self.logins)
        if self.invalid_login_refresh is not False:
            payload = {"Token": self.latest_token}
            if self.invalid_login_refresh is not None:
                payload["RefreshToken"] = self.invalid_login_refresh
            return Response(200, {"Success": True, "Data": payload})
        return Response(
            200,
            {
                "Success": True,
                "Data": {
                    "Token": self.latest_token,
                    "RefreshToken": "synthetic-refresh",
                },
            },
        )

    def request(self, method, url, *, headers, **kwargs):
        access_token = headers["authorization"].removeprefix("Bearer ")
        self.requests.append((method, url, access_token))
        if self.reject_all or access_token in self.rejected_tokens:
            wait = self.late_wait if url.endswith("/late") else None
            if self.rejection == "http":
                return Response(401, {}, wait=wait)
            if self.rejection == "application_message":
                return Response(
                    200, {"Success": False, "Message": "Not logged in"}, wait=wait
                )
            return Response(200, {"Code": 401}, wait=wait)
        return Response(200, {"ok": True})


@pytest.mark.parametrize("initial", ["expired", "absent", "no_refresh", "fallback"])
async def test_concurrent_expired_requests_share_authentication(api_module, initial):
    session = Session(refresh_fails=initial == "fallback")
    client = api_module.BydEnergyApiClient(
        "synthetic",
        "synthetic",
        session,
        None if initial == "absent" else token(0),
        None if initial in {"absent", "no_refresh"} else "synthetic-refresh",
    )
    results = await asyncio.gather(
        *(client.request("get", f"/poll/{index}") for index in range(8))
    )
    assert results == [{"ok": True}] * 8
    assert session.refreshes == (1 if initial in {"expired", "fallback"} else 0)
    assert session.logins == (0 if initial == "expired" else 1)
    assert session.handshakes == session.logins
    assert len(session.requests) == 8
    assert {request[2] for request in session.requests} == {client.access_token}


@pytest.mark.parametrize("rejection", ["http", "application", "application_message"])
async def test_concurrent_rejections_refresh_once_and_retry(api_module, rejection):
    session = Session(rejection=rejection)
    initial = token(4102444800)
    session.rejected_tokens.add(initial)
    client = api_module.BydEnergyApiClient(
        "synthetic", "synthetic", session, initial, "synthetic-refresh"
    )
    results = await asyncio.gather(
        *(client.request("get", f"/poll/{index}") for index in range(8))
    )
    assert results == [{"ok": True}] * 8
    assert session.refreshes == 1
    assert session.logins == 0
    assert len(session.requests) == 16
    assert sum(request[2] == initial for request in session.requests) == 8
    assert sum(request[2] == client.access_token for request in session.requests) == 8


@pytest.mark.parametrize("rejection", ["http", "application", "application_message"])
async def test_late_rejection_does_not_refresh_an_already_replaced_token(
    api_module, rejection
):
    session = Session(rejection=rejection)
    session.late_wait = asyncio.Event()
    initial = token(4102444800)
    session.rejected_tokens.add(initial)
    client = api_module.BydEnergyApiClient(
        "synthetic", "synthetic", session, initial, "synthetic-refresh"
    )
    late = asyncio.create_task(client.request("get", "/late"))
    try:
        assert await client.request("get", "/fast") == {"ok": True}
    finally:
        session.late_wait.set()
    assert await late == {"ok": True}
    assert session.refreshes == 1


async def test_valid_tokens_need_no_authentication(api_module):
    session = Session()
    initial = token(4102444800)
    client = api_module.BydEnergyApiClient(
        "synthetic", "synthetic", session, initial, "synthetic-refresh"
    )
    results = await asyncio.gather(
        *(client.request("get", f"/poll/{index}") for index in range(8))
    )
    assert results == [{"ok": True}] * 8
    assert session.refreshes == session.logins == 0
    assert all(request[2] == initial for request in session.requests)


async def test_a_separately_rejected_replacement_still_refreshes(api_module):
    session = Session()
    initial = token(4102444800)
    session.rejected_tokens.add(initial)
    client = api_module.BydEnergyApiClient(
        "synthetic", "synthetic", session, initial, "synthetic-refresh"
    )
    assert await client.request("get", "/first") == {"ok": True}
    session.rejected_tokens.add(client.access_token)
    assert await client.request("get", "/second") == {"ok": True}
    assert session.refreshes == 2


async def test_cancelled_refresh_releases_waiters(api_module):
    session = Session()
    session.auth_wait = asyncio.Event()
    session.auth_entered = asyncio.Event()
    client = api_module.BydEnergyApiClient(
        "synthetic", "synthetic", session, token(0), "synthetic-refresh"
    )
    leader = asyncio.create_task(client.request("get", "/cancelled"))
    await session.auth_entered.wait()
    waiter = asyncio.create_task(client.request("get", "/waiter"))
    leader.cancel()
    with pytest.raises(asyncio.CancelledError):
        await leader
    session.auth_wait.set()
    assert await asyncio.wait_for(waiter, timeout=1) == {"ok": True}
    assert session.refreshes == 2


async def test_failed_login_releases_queued_requests_and_allows_recovery(api_module):
    session = Session(login_fails=True)
    client = api_module.BydEnergyApiClient("synthetic", "synthetic", session)
    results = await asyncio.wait_for(
        asyncio.gather(
            *(client.request("get", f"/poll/{index}") for index in range(3)),
            return_exceptions=True,
        ),
        timeout=1,
    )
    assert all(isinstance(result, api_module.BydEnergyAuthError) for result in results)
    assert session.logins == 3
    assert session.requests == []
    session.login_fails = False
    assert await client.request("get", "/recovered") == {"ok": True}
    assert session.logins == 4


@pytest.mark.parametrize("refresh_value", [None, ""])
async def test_incomplete_login_is_not_reused_as_a_successful_renewal(
    api_module, refresh_value
):
    session = Session()
    session.invalid_login_refresh = refresh_value
    client = api_module.BydEnergyApiClient("synthetic", "synthetic", session)
    results = await asyncio.wait_for(
        asyncio.gather(
            *(client.request("get", f"/poll/{index}") for index in range(8)),
            return_exceptions=True,
        ),
        timeout=1,
    )
    assert all(isinstance(result, api_module.BydEnergyAuthError) for result in results)
    assert session.logins == 8
    assert session.requests == []


@pytest.mark.parametrize("rejection", ["http", "application", "application_message"])
async def test_repeated_rejections_keep_the_existing_two_attempt_limit(
    api_module, rejection
):
    session = Session(rejection=rejection)
    session.reject_all = True
    client = api_module.BydEnergyApiClient(
        "synthetic", "synthetic", session, token(4102444800), "synthetic-refresh"
    )
    with pytest.raises(api_module.BydEnergyApiClientError):
        await client.request("get", "/always-rejected")
    assert len(session.requests) == 2


@pytest.mark.parametrize(("band", "expected_reads"), [("fast", 3), ("all", 14)])
async def test_actual_coordinator_poll_shares_one_token_renewal(
    hass, api_module, band, expected_reads
):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.byd_energy import BydEnergyDataUpdateCoordinator

    initial = token(0)
    entry = MockConfigEntry(
        domain="byd_energy",
        data={"access_token": initial, "refresh_token": "synthetic-refresh"},
    )
    entry.add_to_hass(hass)
    session = Session()
    client = api_module.BydEnergyApiClient(
        "synthetic", "synthetic", session, initial, "synthetic-refresh"
    )
    coordinator = BydEnergyDataUpdateCoordinator(
        hass, client, "synthetic", "lixia", 15, 300, 43200, entry
    )
    coordinator.data = {"sensors": {}}
    coordinator._bms_type = "4"
    if band == "fast":
        coordinator._last_medium_fetch = time.time()
        coordinator._last_slow_fetch = time.time()
    with patch.object(coordinator, "_async_check_firmware_notifications"):
        result = await coordinator._async_update_data()
    assert isinstance(result, dict)
    assert len(session.requests) == expected_reads
    assert session.refreshes == 1
    assert session.logins == 0
    assert all(request[2] == client.access_token for request in session.requests)
    assert entry.data["access_token"] == client.access_token
