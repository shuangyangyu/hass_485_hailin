"""TCP client for Hailin Modbus communication."""
from __future__ import annotations

import json
import logging
import socket
import struct
from typing import Any

_LOGGER = logging.getLogger(__name__)


class TCPService:
    """TCP service to communicate with the device."""

    def __init__(self, host: str, port: int | str) -> None:
        """Initialize the TCP service."""
        self.host = host
        self.port = int(port)  # Ensure port number is integer type.
        self.socket: socket.socket | None = None

    def connect(self) -> bool:
        """Connect to the TCP device."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)  # Set timeout.
            self.socket.connect((self.host, self.port))
            return True
        except Exception as e:
            _LOGGER.error("Failed to connect to TCP device: %s", e)
            self.socket = None
            return False

    def disconnect(self) -> None:
        """Disconnect from the TCP device."""
        if self.socket:
            self.socket.close()
            self.socket = None

    def _calculate_crc(self, data: bytes) -> bytes:
        """Calculate CRC16 for Modbus RTU."""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return struct.pack('<H', crc)  # Little-endian.

    def send_modbus_query(self, slave_address: int = 1, start_address: int = 0, quantity: int = 3) -> bytes | None:
        """Send Modbus RTU query to read holding registers."""
        try:
            if not self.socket and not self.connect():
                return None
            
            # Build Modbus RTU query frame.
            # Format: [slave_address][function_code][start_address_h][start_address_l][quantity_h][quantity_l][crc_h][crc_l]
            query = struct.pack('>BBHH', slave_address, 0x03, start_address, quantity)
            crc = self._calculate_crc(query)
            query_frame = query + crc
            
            self.socket.send(query_frame)
            
            # Receive response.
            response = self.socket.recv(1024)
            return response
            
        except Exception as e:
            _LOGGER.error("Error sending Modbus query: %s", e)
            self.disconnect()
            return None

    def receive_data(self) -> bytes | None:
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
    def parse_frame(frame: bytes) -> str | None:
        """Parse a TCP data frame."""
        try:
            # Check minimum frame length.
            if len(frame) < 8:  # Modbus RTU minimum frame length.
                _LOGGER.error("帧长度不足: %s 字节", len(frame))
                return None

            slave_address, function_code = struct.unpack(">BB", frame[:2])

            if function_code != 0x03:
                _LOGGER.error("不支持的功能码: %s", function_code)
                return None

            data_length = frame[2]
            data = frame[3:3+data_length]

            if len(data) != data_length:
                _LOGGER.error("数据长度不匹配: 预期 %s, 实际 %s", data_length, len(data))
                return None

            parsed_data: dict[str, Any] = {}
            if data_length == 6:
                pm25, temp, humidity = struct.unpack(">HHH", data)
                parsed_data["pm25"] = pm25
                parsed_data["temperature"] = round(temp / 10.0, 1)
                parsed_data["humidity"] = humidity
            else:
                _LOGGER.warning("未知的数据长度: %s", data_length)
                return None

            if parsed_data:
                return json.dumps(parsed_data, ensure_ascii=False)
            else:
                _LOGGER.warning("未能解析任何数据")
                return None
        except Exception as e:
            _LOGGER.error("解析TCP帧时出错: %s", e)
            return None 