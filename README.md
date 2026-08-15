# hass_485_hailin

Home Assistant 自定义集成：经 485↔TCP 网关（现网 USR-N580）读取海林环境传感器。

> 仓库名 `hass_485_hailin`；HA 里 domain 仍是 **`hailin_modbus`**（v0.1.8）。  
> 现网 N580 海林口常见 `:35`（串口 5）。

## 安装

将本仓库文件放到 Home Assistant 的 `custom_components/hailin_modbus/`，重启后在「集成」里添加 **Hailin Environmental Monitor**。

## 配置要点

| 项 | 说明 |
|----|------|
| 主机 / 端口 | 串口服务器 IP 与 TCP 口（海林现网常见 `:35`） |
| 通信 | Modbus，经 485↔TCP 透传 |
