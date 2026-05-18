"""BYD Energy Cloud API Client."""
import asyncio
import base64
from base64 import b64encode
import json
import logging
import time
import socket
from typing import Any, Dict, List, Optional
import aiohttp

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

from .const import BASE_URL, HARDCODED_IV

_LOGGER = logging.getLogger(__name__)

class BydEnergyApiClientError(Exception):
    """General BYD Energy API exception."""

class BydEnergyAuthError(BydEnergyApiClientError):
    """Authentication error."""

class BydEnergyApiClient:
    """Async API client for BYD Energy Cloud."""

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ) -> None:
        """Initialize API client."""
        self._username = username
        self._password = password
        self._session = session
        self.access_token = access_token
        self.refresh_token = refresh_token
        self._auth_lock = asyncio.Lock()

    def _is_token_expired(self, token: Optional[str]) -> bool:
        """Check if JWT access token is expired or near expiration (e.g. within 30 seconds)."""
        if not token:
            return True
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return True
            payload_b64 = parts[1]
            payload_b64 += '=' * (4 - len(payload_b64) % 4)
            payload_json = base64.b64decode(payload_b64).decode('utf-8')
            payload = json.loads(payload_json)
            exp = payload.get('exp')
            if exp is None:
                return True
            return time.time() >= (exp - 30)
        except Exception as ex:
            _LOGGER.warning("Failed to decode JWT expiration: %s", ex)
            return True

    def _encrypt_password(self, plain_password: str, key_str: str) -> str:
        """Encrypt password using AES-256-CBC with security key."""
        try:
            key_bytes = key_str.encode("utf-8")[:32]
            iv_bytes = HARDCODED_IV.encode("utf-8")[:16]
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
            padded_data = pad(plain_password.encode("utf-8"), AES.block_size)
            encrypted_bytes = cipher.encrypt(padded_data)
            return b64encode(encrypted_bytes).decode("utf-8")
        except Exception as ex:
            _LOGGER.error("Cryptographic encryption failure")
            raise BydEnergyApiClientError("Encryption failure") from ex

    async def _get_security_key(self) -> Dict[str, str]:
        """Request a one-time security key from the cloud."""
        url = f"{BASE_URL}/app/GetSecurityKey"
        headers = {"accept": "application/json, text/plain, */*"}
        try:
            async with self._session.post(url, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    raise BydEnergyApiClientError(f"Security key request failed with status {resp.status}")
                data = await resp.json()
                if not data or not data.get("Success") or not data.get("Data"):
                    raise BydEnergyApiClientError("Invalid security key response")
                return data["Data"]
        except (aiohttp.ClientError, socket.gaierror, asyncio.TimeoutError) as ex:
            raise BydEnergyApiClientError("Network error during security key handshake") from ex

    async def login(self) -> None:
        """Execute complete cryptographic authentication handshake."""
        async with self._auth_lock:
            _LOGGER.debug("Initiating full BYD Energy authentication flow")
            sec_data = await self._get_security_key()
            key_id = sec_data.get("keyId")
            raw_key = sec_data.get("key")
            if not key_id or not raw_key:
                raise BydEnergyAuthError("Missing key material from server")

            encrypted_pw = self._encrypt_password(self._password, raw_key)
            url = f"{BASE_URL}/api/app/account/app-login"
            payload = {
                "KeyId": key_id,
                "Name": self._username,
                "Password": encrypted_pw,
            }
            headers = {
                "accept": "application/json, text/plain, */*",
                "content-type": "application/json",
            }

            try:
                async with self._session.post(url, json=payload, headers=headers, timeout=15) as resp:
                    if resp.status != 200:
                        raise BydEnergyAuthError(f"Login rejected with HTTP {resp.status}")
                    data = await resp.json()
                    if not data or not data.get("Success"):
                        msg = data.get("Message", "Unknown login error")
                        raise BydEnergyAuthError(f"Authentication failed: {msg}")

                    auth_data = data.get("Data", {})
                    self.access_token = auth_data.get("Token")
                    self.refresh_token = auth_data.get("RefreshToken")
                    if not self.access_token or not self.refresh_token:
                        raise BydEnergyAuthError("Server returned invalid token payload")
                    _LOGGER.debug("Authentication successful, tokens acquired")
            except (aiohttp.ClientError, socket.gaierror, asyncio.TimeoutError) as ex:
                raise BydEnergyApiClientError("Network error during login") from ex

    async def _refresh_tokens(self) -> None:
        """Refresh expired access token."""
        if not self.access_token or not self.refresh_token:
            await self.login()
            return

        async with self._auth_lock:
            _LOGGER.debug("Attempting token refresh")
            url = f"{BASE_URL}/api/app/account/refresh-token"
            payload = {
                "AccessToken": self.access_token,
                "RefreshToken": self.refresh_token,
            }
            headers = {
                "accept": "application/json, text/plain, */*",
                "content-type": "application/json",
            }
            try:
                async with self._session.post(url, json=payload, headers=headers, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data and data.get("Success"):
                            token_data = data.get("Data", {})
                            self.access_token = token_data.get("AccessToken", self.access_token)
                            self.refresh_token = token_data.get("RefreshToken", self.refresh_token)
                            _LOGGER.debug("Token refresh successful")
                            return
            except (aiohttp.ClientError, socket.gaierror, asyncio.TimeoutError):
                _LOGGER.debug("Network issue during token refresh, falling back to full login")

        # If refresh failed or rejected, trigger full login
        await self.login()

    async def request(
        self, method: str, path: str, json: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Dispatch HTTP request with automatic token self-healing."""
        if not self.access_token or self._is_token_expired(self.access_token):
            await self._refresh_tokens()

        url = f"{BASE_URL}{path}"
        headers = {
            "accept": "application/json, text/plain, */*",
            "authorization": f"Bearer {self.access_token}",
        }
        if json is not None:
            headers["content-type"] = "application/json"

        attempts = 0
        while attempts < 2:
            attempts += 1
            try:
                async with self._session.request(method, url, json=json, params=params, headers=headers, timeout=15) as resp:
                    if resp.status == 401:
                        _LOGGER.debug("HTTP 401 received, triggering token self-healing")
                        await self._refresh_tokens()
                        headers["authorization"] = f"Bearer {self.access_token}"
                        continue

                    if resp.status != 200:
                        raise BydEnergyApiClientError(f"API request failed with HTTP {resp.status}")

                    data = await resp.json()
                    # Check for custom application-level auth rejection
                    if data and isinstance(data, dict):
                        if data.get("Code") == 401 or (data.get("Success") is False and "logged in" in str(data.get("Message", "")).lower()):
                            if attempts < 2:
                                _LOGGER.debug("App Code 401 received, triggering token self-healing")
                                await self._refresh_tokens()
                                headers["authorization"] = f"Bearer {self.access_token}"
                                continue
                            raise BydEnergyAuthError("Session expired and refresh failed")

                    return data
            except (aiohttp.ClientError, socket.gaierror, asyncio.TimeoutError) as ex:
                if attempts >= 2:
                    raise BydEnergyApiClientError("Network failure during API request") from ex

        raise BydEnergyApiClientError("API request failed after retries")

    async def get_paged_devices(self) -> List[Dict[str, Any]]:
        """Discover registered devices and their metadata."""
        payload = {
            "PageIndex": 1,
            "PageSize": 20,
            "Filter": {"ProductType": "", "PidAndNote": ""},
        }
        resp = await self.request("post", "/Product/app/getPagedPidByType", json=payload)
        if resp and resp.get("Success") and resp.get("Data"):
            return resp["Data"].get("Items", [])
        return []

    async def get_realtime_data_list(self, product_type: str, pid: str, display_type: str, child_no: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch realtime sensor metrics for a specific subsystem."""
        params = {
            "productType": product_type,
            "pid": pid,
            "clientType": "app",
            "realtimeDisplayType": display_type,
            "no": "1",
        }
        if child_no is not None:
            params["childNo"] = child_no

        resp = await self.request("post", "/RealtimeConfig/GetRealtimeDataList", params=params)
        if resp and resp.get("Success") and resp.get("Data"):
            return resp["Data"]
        return []

    async def get_pv_realtimes(self, product_type: str, pid: str) -> Dict[str, Any]:
        """Fetch instantaneous PV MPPT string parameters."""
        params = {"productType": product_type, "pid": pid}
        resp = await self.request("get", "/PV/GetPvRealtimes", params=params)
        if resp and resp.get("Success") and resp.get("Data") and isinstance(resp["Data"], list) and len(resp["Data"]) > 0:
            return resp["Data"][0]
        return {}

    async def get_today_ele_data(self, product_type: str, pid: str) -> Dict[str, Any]:
        """Fetch daily aggregated energy totals."""
        params = {"productType": product_type, "pid": pid}
        resp = await self.request("get", "/HistoryRealtime/GetTodayEleData", params=params)
        if resp and resp.get("Success") and resp.get("Data"):
            return resp["Data"]
        return {}

    async def get_total_ele_data_new(self, product_type: str, pid: str) -> Dict[str, Any]:
        """Fetch lifetime accumulated energy totals."""
        params = {"productType": product_type, "pid": pid}
        resp = await self.request("get", "/HistoryRealtime/GetTotalEleDataNew", params=params)
        if resp and resp.get("Success") and resp.get("Data"):
            return resp["Data"]
        return {}

    async def get_online_state(self, pid: str) -> Dict[str, Any]:
        """Fetch device connectivity status."""
        params = {"pid": pid}
        resp = await self.request("get", "/Product/GetProductOnlineState", params=params)
        if resp and resp.get("Success") and resp.get("Data"):
            return resp["Data"]
        return {}
    async def get_device_base_settings(self, product_type: str, pid: str) -> Dict[str, Any]:
        """Fetch device installation base settings ( qaTime )."""
        params = {"productType": product_type, "pid": pid}
        resp = await self.request("get", "/DeviceSetting/GetDeviceBaseSettings", params=params)
        if resp and resp.get("Success") and resp.get("Data"):
            return resp["Data"]
        return {}

    async def get_device_grid_settings(self, product_type: str, pid: str) -> Dict[str, Any]:
        """Fetch device grid regulatory standards settings."""
        params = {"productType": product_type, "pid": pid}
        resp = await self.request("get", "/DeviceSetting/GetDeviceSettings", params=params)
        if resp and resp.get("Success") and resp.get("Data"):
            return resp["Data"]
        return {}

    async def get_current_upgrade_version(self, device_type: str, pid: str) -> Optional[str]:
        """Fetch current firmware version for a target deviceType (bms or pcs)."""
        params = {"DeviceType": device_type, "pid": pid}
        resp = await self.request("get", "/Upgrade/GetCurrentUpgradeAreaVersion", params=params)
        if resp and resp.get("Success") and resp.get("Data"):
            return str(resp["Data"]).strip()
        return None

    async def get_latest_version(self, product_type: str, device_type: str) -> Optional[str]:
        """Check BYD cloud repository for latest available firmware version of a device type (bms, pcs, f527)."""
        params = {"ProductType": product_type, "deviceType": device_type, "appType": "IOS"}
        resp = await self.request("get", "/Upgrade/app/GetLatestVersion", params=params)
        if resp and resp.get("Success") and resp.get("Data"):
            return str(resp["Data"]).strip()
        return None

    async def get_bms_type(self, pid: str) -> Optional[str]:
        """Fetch BMS hardware series code."""
        params = {"pid": pid}
        resp = await self.request("get", "/Upgrade/GetBmsType", params=params)
        if resp and resp.get("Success") and resp.get("Data"):
            return str(resp["Data"])
        return None

    async def get_pv_max_power_output(self, pid: str) -> Dict[str, Any]:
        """Fetch maximum allowable PV generation rating per MPPT string."""
        params = {"pid": pid}
        resp = await self.request("get", "/Product/GetPvMaxPowerOutput", params=params)
        if resp and resp.get("Success") and resp.get("Data"):
            return resp["Data"]
        return {}

    async def get_device_eeprom_settings(self, product_type: str, pid: str) -> Dict[str, Any]:
        """Fetch internal hardware EEPROM parameter table."""
        params = {"productType": product_type, "pid": pid}
        resp = await self.request("get", "/RealtimeConfig/GetDeviceEepromSettings", params=params)
        if resp and resp.get("Success") and resp.get("Data") and isinstance(resp["Data"], list):
            return {item["jsonName"]: item.get("jsonValue") for item in resp["Data"] if isinstance(item, dict) and "jsonName" in item}
        return {}

    async def update_device_setting(self, pid: str, json_name: str, json_value: Any) -> bool:
        """Directly modify internal hardware EEPROM parameter register."""
        payload = {
            "Pid": pid,
            "ProductType": "lixia",
            "DeviceType": "pcs",
            "cmdOptions": [
                {
                    "JsonName": json_name,
                    "JsonValue": json_value,
                    "TableAttributeId": 0
                }
            ],
            "operType": "remote"
        }
        try:
            resp = await self.request("post", "/Upgrade/UpdateDeviceSetDirect", json=payload)
            if resp and resp.get("Success"):
                return True
        except Exception as err:
            _LOGGER.error("Failed to update setting %s: %s", json_name, err)
        return False

    async def update_pv_max_power(self, pid: str, string_id: int, power: int) -> bool:
        """Update configured peak power rating for PV MPPT string."""
        url = "/Product/SavePV1MaxPower" if string_id == 1 else "/Product/SavePV2MaxPower"
        payload = {"pid": pid, "pv1MaxPower" if string_id == 1 else "pv2MaxPower": power}
        try:
            resp = await self.request("post", url, json=payload)
            if resp and resp.get("Success"):
                return True
        except Exception as err:
            _LOGGER.error("Failed to update PV%d max power: %s", string_id, err)
        return False
