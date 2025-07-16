"""Support for Hailin Modbus sensors."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .tcp_client import DataParser, TCPService

_LOGGER = logging.getLogger(__name__)

CONF_ENABLE_POLLING = "enable_polling"
DOMAIN = "hailin_modbus"
SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Hailin Modbus sensor."""
    host = config_entry.data[CONF_HOST]
    port = int(config_entry.data[CONF_PORT])  # Ensure port number is integer type.
    enable_polling = config_entry.data.get(CONF_ENABLE_POLLING, False)

    coordinator = HailinTCPCoordinator(hass, host, port, enable_polling)
    await coordinator.async_config_entry_first_refresh()

    # Device information for grouping all sensors under the same device.
    device_info = DeviceInfo(
        identifiers={(DOMAIN, f"{host}_{port}")},
        name="海林环境监测仪",
        manufacturer="hailin",
        model="Modbus 环境监测仪",
        sw_version="1.0",
        configuration_url=f"http://{host}:{port}",
        serial_number=f"hailin_{host}_{port}",
        hw_version="1.0",
        suggested_area="客厅",
    )

    sensors = [
        HailinModbusSensor(coordinator, "PM2.5", "µg/m³", "pm25", device_info, host, port),
        HailinModbusSensor(coordinator, "湿度", PERCENTAGE, "humidity", device_info, host, port),
        HailinModbusSensor(coordinator, "温度", UnitOfTemperature.CELSIUS, "temperature", device_info, host, port),
    ]

    async_add_entities(sensors, True)


class HailinTCPCoordinator(DataUpdateCoordinator):
    """Coordinator to manage Hailin TCP data."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, enable_polling: bool = False) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Hailin TCP",
            update_interval=SCAN_INTERVAL,
        )
        self.tcp_service = TCPService(host, port)
        self.parser = DataParser()
        self.enable_polling = enable_polling

    async def _async_update_data(self) -> dict[str, Any] | None:
        """Fetch data from TCP device."""
        try:
            if self.enable_polling:
                # Active polling mode.
                data = await self.hass.async_add_executor_job(
                    self.tcp_service.send_modbus_query, 1, 0, 3
                )
            else:
                # Passive receiving mode.
                data = await self.hass.async_add_executor_job(self.tcp_service.receive_data)
            
            if data:
                parsed_data = self.parser.parse_frame(data)
                if parsed_data:
                    result = json.loads(parsed_data)
                    _LOGGER.info("成功获取数据: %s", result)
                    return result
                else:
                    _LOGGER.warning("数据解析失败")
            else:
                _LOGGER.warning("未接收到数据")
            return None
        except Exception as e:
            _LOGGER.error("Error updating Hailin TCP data: %s", e)
            return None


class HailinModbusSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Hailin Modbus sensor."""

    def __init__(
        self, 
        coordinator: HailinTCPCoordinator, 
        name: str, 
        unit: str, 
        key: str, 
        device_info: DeviceInfo, 
        host: str, 
        port: int
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._key = key
        self._attr_unique_id = f"hailin_modbus_{host}_{port}_{key}"
        self._attr_device_info = device_info
        self._attr_has_entity_name = True

        if key == "pm25":
            self._attr_device_class = SensorDeviceClass.PM25
            self._attr_icon = "mdi:air-filter"
            self._attr_state_class = "measurement"
        elif key == "temperature":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_icon = "mdi:thermometer"
            self._attr_state_class = "measurement"
        elif key == "humidity":
            self._attr_device_class = SensorDeviceClass.HUMIDITY
            self._attr_icon = "mdi:water-percent"
            self._attr_state_class = "measurement"

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get(self._key)
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
