"""Support for Hailin Modbus sensors."""
import asyncio
import logging
from datetime import timedelta
import socket
import struct
import json

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.helpers.device_registry import DeviceInfo

_LOGGER = logging.getLogger(__name__)

DOMAIN = "hailin_modbus"
SCAN_INTERVAL = timedelta(seconds=30)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the Hailin Modbus sensor."""
    host = config_entry.data[CONF_HOST]
    port = config_entry.data[CONF_PORT]

    coordinator = HailinTCPCoordinator(hass, host, port)
    await coordinator.async_config_entry_first_refresh()

    # 设备信息，用于将所有传感器归类到同一个设备
    device_info = DeviceInfo(
        identifiers={(DOMAIN, f"{host}_{port}")},
        name=f"海林环境监测仪",
        manufacturer="hailin",
        model="Modbus 环境监测仪",
        sw_version="1.0",
        configuration_url=f"http://{host}:{port}",
    )

    sensors = [
        HailinModbusSensor(coordinator, "PM2.5", "µg/m³", "pm25", device_info, host, port),
        HailinModbusSensor(coordinator, "温度", UnitOfTemperature.CELSIUS, "temperature", device_info, host, port),
        HailinModbusSensor(coordinator, "湿度", PERCENTAGE, "humidity", device_info, host, port),
    ]

    async_add_entities(sensors, True)

class HailinTCPCoordinator(DataUpdateCoordinator):
    """Coordinator to manage Hailin TCP data."""

    def __init__(self, hass, host, port):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Hailin TCP",
            update_interval=SCAN_INTERVAL,
        )
        self.tcp_service = TCPService(host, port)
        self.parser = DataParser()

    async def _async_update_data(self):
        """Fetch data from TCP device."""
        try:
            data = await self.hass.async_add_executor_job(self.tcp_service.receive_data)
            if data:
                parsed_data = self.parser.parse_frame(data)
                if parsed_data:
                    return json.loads(parsed_data)
            return None
        except Exception as e:
            _LOGGER.error("Error updating Hailin TCP data: %s", e)
            return None

class HailinModbusSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Hailin Modbus sensor."""

    def __init__(self, coordinator, name, unit, key, device_info, host, port):
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
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get(self._key)
        return None

    @property
    def available(self):
        """Return if entity is available."""
        return self.coordinator.last_update_success

class TCPService:
    """TCP service to communicate with the device."""

    def __init__(self, host, port):
        """Initialize the TCP service."""
        self.host = host
        self.port = port
        self.socket = None

    def connect(self):
        """Connect to the TCP device."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            return True
        except Exception as e:
            _LOGGER.error("Failed to connect to TCP device: %s", e)
            self.socket = None
            return False

    def disconnect(self):
        """Disconnect from the TCP device."""
        if self.socket:
            self.socket.close()
            self.socket = None

    def receive_data(self):
        """Receive data from the TCP device."""
        if not self.socket and not self.connect():
            return None

        try:
            return self.socket.recv(1024)
        except Exception as e:
            _LOGGER.error("Error receiving data from TCP device: %s", e)
            self.disconnect()
            return None

class DataParser:
    """Parser for TCP data frames."""

    @staticmethod
    def parse_frame(frame):
        """Parse a TCP data frame."""
        try:
            _LOGGER.info(f"接收到的帧: {frame.hex()}")

            # 检查帧的最小长度
            if len(frame) < 8:  # Modbus RTU最小帧长度
                _LOGGER.error(f"帧长度不足: {len(frame)} 字节")
                return None

            slave_address, function_code = struct.unpack(">BB", frame[:2])
            _LOGGER.info(f"解析的数据: 从机地址={slave_address}, 功能码={function_code}")

            if function_code != 0x03:
                _LOGGER.error(f"不支持的功能码: {function_code}")
                return None

            data_length = frame[2]
            _LOGGER.info(f"数据长度: {data_length}")
            data = frame[3:3+data_length]

            if len(data) != data_length:
                _LOGGER.error(f"数据长度不匹配: 预期 {data_length}, 实际 {len(data)}")
                return None

            parsed_data = {}
            if data_length == 6:
                pm25, temp, humidity = struct.unpack(">HHH", data)
                parsed_data["pm25"] = pm25
                parsed_data["temperature"] = round(temp / 10.0, 1)
                parsed_data["humidity"] = humidity
                _LOGGER.info(f"解析的值: PM2.5={pm25}, 温度={parsed_data['temperature']}, 湿度={humidity}")
            else:
                _LOGGER.warning(f"未知的数据长度: {data_length}")
                return None

            if parsed_data:
                return json.dumps(parsed_data, ensure_ascii=False)
            else:
                _LOGGER.warning("未能解析任何数据")
                return None
        except Exception as e:
            _LOGGER.error(f"解析TCP帧时出错: {e}")
            _LOGGER.error(f"问题帧: {frame.hex()}")
            return None
