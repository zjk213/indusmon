# IndusMon — 工业设备数采与监控平台

轻量级工业数据采集与监控（SCADA-lite）示例项目：**Modbus TCP 接入 + 周期采集 + SQLite 时序存储 + 阈值告警 + 实时看板**。  
单进程、零 Docker、Windows/Linux 一键启动，适合自动化 / 工业物联网方向的作品集与本地演示。

网申填表 Skill 是独立 GitHub 仓库：[zjk213/job-app-filler](https://github.com/zjk213/job-app-filler)（不隶属本仓库）。

## 特性

- 内置 **Modbus TCP 模拟从站**（锅炉 + 产线两台虚拟设备），无需真实 PLC
- 多线程 **周期采集引擎**（按设备独立 interval，通信失败计数，SQLite WAL）
- **阈值告警**（hi / hihi / lo，2% 回差去抖，hihi 优先，可 ACK）
- REST API + **SSE** 实时推送 + 历史曲线降采样查询
- 深色工业风 Web 看板（设备卡片 / 曲线 / 告警面板 / 一键尖峰演示）
- SQLite 单文件存储，pytest 覆盖核心路径

## 架构

```
┌─────────────────────────────────────────────────────────┐
│                     indusmon 进程                        │
│  ┌──────────────┐   poll    ┌────────────────────────┐  │
│  │ Modbus 模拟从站 │◄─────────│  Collector（周期采集）   │  │
│  │  (TCP :5020)  │           │  interval 可配 / 设备级 │  │
│  └──────────────┘           └───────────┬────────────┘  │
│                                          │ write         │
│                                          ▼               │
│  ┌──────────────┐  evaluate ┌────────────────────────┐  │
│  │ Alert Engine │◄──────────│   SQLite (readings,     │  │
│  └──────┬───────┘           │   alerts, devices)      │  │
│         │                   └───────────┬────────────┘  │
│         ▼                               │ query         │
│  ┌──────────────┐   SSE/REST            ▼               │
│  │  FastAPI     │◄────────────────►  Web Dashboard      │
│  │  /api/v1/*   │                   (static + Chart.js) │
│  └──────────────┘                                      │
└─────────────────────────────────────────────────────────┘
```

## 快速开始

```bash
# 建议 Python 3.11+
pip install -e ".[dev]"

# 一键启动（模拟从站 + 采集 + API + 看板）
python -m indusmon
```

浏览器打开：

- 看板：<http://127.0.0.1:8080/>
- OpenAPI：<http://127.0.0.1:8080/docs>

### 截图

![IndusMon 看板](docs/assets/dashboard.png)

> 占位：启动后对 `http://127.0.0.1:8080/` 截图保存为 `docs/assets/dashboard.png`。

### 演示告警

1. 看板左侧选中 `boiler-01 / steam_temp`
2. 点右上 **「制造尖峰」**，输入例如 `200`
3. 数秒内告警面板出现 HI/HIHI；恢复后自动 cleared，可 ACK

### 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `INDUSMON_DB` | `./data/indusmon.db` | SQLite 路径 |
| `INDUSMON_HOST` | `127.0.0.1` | HTTP 监听 |
| `INDUSMON_PORT` | `8080` | HTTP 端口 |
| `INDUSMON_SIM_PORT` | `5020` | 模拟从站端口 |
| `INDUSMON_POLL_MS` | `1000` | 默认采集周期 |
| `INDUSMON_SEED_DEMO` | `1` | 启动时种子演示设备 |

## API 摘要

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/v1/health` | 健康检查 |
| GET/POST | `/api/v1/devices` | 设备列表 / 注册 |
| PATCH | `/api/v1/devices/{id}` | 更新 enabled / interval |
| GET | `/api/v1/readings` | 历史查询 |
| GET | `/api/v1/readings/latest` | 最新值 |
| GET | `/api/v1/series?device_id&tag&from&to` | 曲线序列（降采样） |
| GET | `/api/v1/alerts` | 告警列表 |
| POST | `/api/v1/alerts/{id}/ack` | 确认告警 |
| POST | `/api/v1/sim/spike` | 人为制造尖峰 |
| GET | `/api/v1/metrics` | 采集统计 |
| GET | `/api/v1/stream` | SSE 实时读数 |

## 演示设备点表

| 设备 | unit | tag | 含义 | 工程量 |
|------|------|-----|------|--------|
| boiler-01 | 1 | steam_temp | 蒸汽温度 | °C |
| boiler-01 | 1 | pressure | 压力 | MPa |
| boiler-01 | 1 | level | 液位 | % |
| boiler-01 | 1 | burner | 燃烧器 | 0/1 |
| line-02 | 2 | motor_current | 电机电流 | A |
| line-02 | 2 | rpm | 转速 | rpm |
| line-02 | 2 | vibration | 振动 | mm/s |
| line-02 | 2 | parts_count | 计数 | pcs |

模拟从站将模拟量存为 `round(raw*100)` 的 16-bit 寄存器，点表 `scale=0.01` 还原工程量。

## 测试

```bash
pytest -q
```

## 工程结构

```
src/indusmon/
  __main__.py      # python -m indusmon
  app.py           # FastAPI 工厂 + 种子数据
  config.py
  db.py
  collector.py     # 周期采集
  alerts.py        # 阈值与回差
  simulator.py     # Modbus TCP 从站模拟
  api/routes.py
  web/static/      # 看板
tests/
docs/compose/spec/ # 设计文档
```

## 路线图（非 MVP）

- JWT 鉴权与设备权限
- MQTT / OPC-UA 接入
- 规则引擎与通知（邮件/钉钉）
- 工艺流程图组态
- InfluxDB/Timescale 时序后端

## License

MIT
