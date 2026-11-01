"""Exercise the service through Home Assistant config-entry lifecycle."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.fixture
def api_reads(enable_custom_integrations):
    """Synthetic read responses; use the real coordinator and HA lifecycle."""
    from pathlib import Path

    import custom_components

    custom_components.__path__.append(
        str(Path(__file__).parents[1] / "custom_components")
    )
    from custom_components.byd_energy.api import BydEnergyApiClient

    methods = {
        "get_realtime_data_list": [],
        "get_pv_realtimes": {},
        "get_online_state": {},
        "get_today_ele_data": {},
        "get_total_ele_data_new": {},
        "get_pv_max_power_output": {},
        "get_device_eeprom_settings": {},
        "get_bms_type": "4",
        "get_device_base_settings": {},
        "get_device_grid_settings": {},
        "get_all_latest_versions": {"DeviceVersionList": []},
    }
    from contextlib import ExitStack

    with ExitStack() as stack:
        for name, result in methods.items():
            stack.enter_context(
                patch.object(BydEnergyApiClient, name, AsyncMock(return_value=result))
            )
        # Notification publication is unrelated to refresh service ownership.
        stack.enter_context(
            patch(
                "custom_components.byd_energy.BydEnergyDataUpdateCoordinator._async_check_firmware_notifications"
            )
        )
        yield


async def setup_entry(hass, pid):
    entry = MockConfigEntry(
        domain="byd_energy",
        title=pid,
        unique_id=pid,
        data={"username": "synthetic", "password": "synthetic", "pid": pid},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    return entry


@pytest.mark.asyncio
@pytest.mark.parametrize("order", [("first", "second"), ("second", "first")])
async def test_two_loaded_entries_refresh_and_partial_unload(hass, api_reads, order):
    first = await setup_entry(hass, order[0])
    second = await setup_entry(hass, order[1])
    coordinators = hass.data["byd_energy"]
    calls = {}
    for entry in (first, second):
        coordinator = coordinators[entry.entry_id]
        calls[entry.entry_id] = AsyncMock(wraps=coordinator.async_force_full_refresh)
        coordinator.async_force_full_refresh = calls[entry.entry_id]

    await hass.services.async_call("byd_energy", "force_refresh", {}, blocking=True)
    assert [calls[e.entry_id].await_count for e in (first, second)] == [1, 1]
    assert await hass.config_entries.async_unload(first.entry_id)
    await hass.async_block_till_done()
    assert first.state is ConfigEntryState.NOT_LOADED
    assert second.state is ConfigEntryState.LOADED
    assert hass.services.has_service("byd_energy", "force_refresh")
    await hass.services.async_call("byd_energy", "force_refresh", {}, blocking=True)
    assert calls[second.entry_id].await_count == 2
    assert await hass.config_entries.async_unload(second.entry_id)
    assert not hass.services.has_service("byd_energy", "force_refresh")


@pytest.mark.asyncio
async def test_single_entry_preserves_full_loop_refresh(hass, api_reads):
    entry = await setup_entry(hass, "single")
    coordinator = hass.data["byd_energy"][entry.entry_id]
    coordinator._last_medium_fetch = 10**15
    coordinator._last_slow_fetch = 10**15
    with (
        patch.object(
            coordinator.client, "get_device_eeprom_settings", AsyncMock(return_value={})
        ) as medium,
        patch.object(
            coordinator.client, "get_device_base_settings", AsyncMock(return_value={})
        ) as slow,
    ):
        await hass.services.async_call("byd_energy", "force_refresh", {}, blocking=True)
        medium.assert_awaited_once()
        slow.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_unload_preserves_service(hass, api_reads):
    entry = await setup_entry(hass, "first")
    with patch.object(
        hass.config_entries, "async_unload_platforms", AsyncMock(return_value=False)
    ):
        assert not await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.FAILED_UNLOAD
    assert entry.entry_id in hass.data["byd_energy"]
    assert hass.services.has_service("byd_energy", "force_refresh")
    coordinator = hass.data["byd_energy"][entry.entry_id]
    with patch.object(coordinator, "async_force_full_refresh", AsyncMock()) as refresh:
        await hass.services.async_call("byd_energy", "force_refresh", {}, blocking=True)
        refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_options_reload_preserves_other_entry(hass, api_reads):
    first = await setup_entry(hass, "first")
    second = await setup_entry(hass, "second")
    hass.config_entries.async_update_entry(first, options={"polling_interval": 42})
    await hass.async_block_till_done()
    assert first.state is ConfigEntryState.LOADED
    assert second.state is ConfigEntryState.LOADED
    assert hass.data["byd_energy"][first.entry_id].update_interval.total_seconds() == 42
    with patch.object(
        hass.data["byd_energy"][second.entry_id],
        "async_force_full_refresh",
        AsyncMock(),
    ) as refresh:
        await hass.services.async_call("byd_energy", "force_refresh", {}, blocking=True)
        refresh.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["raised", "coordinator_status"])
async def test_failure_still_attempts_other_entry(hass, api_reads, failure):
    first = await setup_entry(hass, "first")
    second = await setup_entry(hass, "second")
    a = hass.data["byd_energy"][first.entry_id]
    b = hass.data["byd_energy"][second.entry_id]
    if failure == "raised":
        failing = patch.object(
            a,
            "async_force_full_refresh",
            AsyncMock(side_effect=RuntimeError("synthetic failure")),
        )
    else:
        failing = patch.object(
            a,
            "_async_update_data",
            AsyncMock(side_effect=UpdateFailed("synthetic failure")),
        )
    with (
        failing,
        patch.object(
            b, "async_force_full_refresh", AsyncMock(wraps=b.async_force_full_refresh)
        ) as refresh,
    ):
        with pytest.raises(HomeAssistantError, match=first.entry_id):
            await hass.services.async_call(
                "byd_energy", "force_refresh", {}, blocking=True
            )
        refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_forward_failure_rolls_back_coordinator(hass, api_reads):
    entry = MockConfigEntry(
        domain="byd_energy",
        data={"username": "synthetic", "password": "synthetic", "pid": "failed"},
    )
    entry.add_to_hass(hass)
    with patch.object(
        hass.config_entries,
        "async_forward_entry_setups",
        AsyncMock(side_effect=RuntimeError("synthetic forwarding failure")),
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert entry.entry_id not in hass.data["byd_energy"]
    assert not hass.services.has_service("byd_energy", "force_refresh")


@pytest.mark.asyncio
async def test_skip_entry_unloaded_before_its_turn(hass, api_reads):
    first = await setup_entry(hass, "first")
    second = await setup_entry(hass, "second")
    a = hass.data["byd_energy"][first.entry_id]
    b = hass.data["byd_energy"][second.entry_id]

    async def unload_other():
        assert await hass.config_entries.async_unload(second.entry_id)

    with (
        patch.object(
            a, "async_force_full_refresh", AsyncMock(side_effect=unload_other)
        ),
        patch.object(b, "async_force_full_refresh", AsyncMock()) as refresh,
    ):
        await hass.services.async_call("byd_energy", "force_refresh", {}, blocking=True)
        refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancellation_propagates(hass, api_reads):
    import asyncio

    entry = await setup_entry(hass, "first")
    coordinator = hass.data["byd_energy"][entry.entry_id]
    with (
        patch.object(
            coordinator,
            "async_force_full_refresh",
            AsyncMock(side_effect=asyncio.CancelledError),
        ),
        pytest.raises(asyncio.CancelledError),
    ):
        await hass.services.async_call("byd_energy", "force_refresh", {}, blocking=True)


@pytest.mark.asyncio
async def test_initial_refresh_failure_preserves_existing_service(hass, api_reads):
    from custom_components.byd_energy import BydEnergyDataUpdateCoordinator

    loaded = await setup_entry(hass, "loaded")
    failed = MockConfigEntry(
        domain="byd_energy",
        data={"username": "synthetic", "password": "synthetic", "pid": "failed"},
    )
    failed.add_to_hass(hass)
    with patch.object(
        BydEnergyDataUpdateCoordinator,
        "_async_update_data",
        AsyncMock(side_effect=UpdateFailed("synthetic initial failure")),
    ):
        assert not await hass.config_entries.async_setup(failed.entry_id)
    assert failed.state is ConfigEntryState.SETUP_RETRY
    assert failed.entry_id not in hass.data["byd_energy"]
    assert loaded.entry_id in hass.data["byd_energy"]
    assert hass.services.has_service("byd_energy", "force_refresh")


@pytest.mark.asyncio
async def test_inflight_read_can_finish_after_unload(hass, api_reads):
    import asyncio

    entry = await setup_entry(hass, "first")
    coordinator = hass.data["byd_energy"][entry.entry_id]
    started = asyncio.Event()
    finish = asyncio.Event()
    original_update = coordinator._async_update_data

    async def delayed_update():
        started.set()
        await finish.wait()
        return await original_update()

    with patch.object(coordinator, "_async_update_data", delayed_update):
        call = hass.async_create_task(
            hass.services.async_call("byd_energy", "force_refresh", {}, blocking=True)
        )
        await started.wait()
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert not hass.services.has_service("byd_energy", "force_refresh")
        finish.set()
        await call
    assert entry.entry_id not in hass.data["byd_energy"]
