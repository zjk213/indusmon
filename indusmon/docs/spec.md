---
feature: indusmon-mvp
status: delivered
updated: 2026-09-11
branch: feature/indusmon-mvp
commits: 7b95098..6ab0a87
---

# IndusMon — 工业设备数采与监控平台（MVP）

> 定位：面向自动化/工业物联网岗位的作品集项目。展示工业协议接入、周期采集、时序存储、阈值告警与实时监控的完整闭环。
> 工作区覆盖说明：会话策略阻止 `git worktree add`，本 feature 在主 checkout 的 `feature/indusmon-mvp` 分支上实现（非 worktree）。

## Report

**What was built** — 单进程 Python monorepo `indusmon`：内置 Modbus TCP 模拟从站（锅炉 unit=1 / 产线 unit=2），多线程周期采集引擎写入 SQLite（WAL + 线程本地连接），阈值告警（hi/hihi/lo，2% 回差，hihi 优先，可 ACK），FastAPI REST + SSE + 深色工业风看板（Chart.js 曲线、尖峰演示）。启动：`pip install -e ".[dev]" && python -m indusmon`，看板 `http://127.0.0.1:8080/`。

**Verification** — `pytest -q` → PASS（17 passed：告警回差/scale/API/404/端口占用/协议回环）；`python scripts/smoke_e2e.py` → PASS（1.5s 写入 56 点，steam_temp≈167，尖峰后 hihi active）。独立 review 修复 4 项 critical（EventSource、端口占用启动失败、未知设备 404、线程安全 DB），二次 re-review 全 PASS。

**Journey log** — 1) 模拟从站 datastore 曾把 unit_id 写死为 0，读到全 0；2) rpm 用 gain=100 会超出 int16，改为 per-point `gain`；3) SQLite 列名 `limit` 为保留字，需双引号；4) pymodbus 3.7 用 `slave=` 而非 `device_id=`；5) 前端 SSE API 是 `EventSource` 不是 `EventStream`。

## [S1] Problem

自动化/工业软件岗位需要可运行、可讲解的「数采 + 监控」作品：

1. 真实产线设备昂贵且不可在个人环境复现，需要**协议级模拟**才能完整演示。
2. 常见学生项目只有算法或单片机裸机代码，缺少**服务化架构**（采集引擎、存储、API、告警、前端）。
3. 简历/面试需要能一键启动、有 API 文档、有测试、有架构说明的开源仓库。

用户诉求：轻量 Python 全栈、零 Docker 依赖、Windows 可跑、GitHub 可展示的 **采集 + 监控 + 告警 MVP**。

## [S2] Design

### S2.1 项目身份

| 项 | 值 |
|----|-----|
| 仓库名 / 包名 | `indusmon` |
| 中文名 | 工业设备数采与监控平台 |
| 运行时 | Python 3.11+（本机验证 3.12） |
| 许可证 | MIT |

### S2.2 技术栈

| 层 | 选型 | 理由 |
|----|------|------|
| API | FastAPI + uvicorn | 异步、自动 OpenAPI、作品集友好 |
| 存储 | SQLite（`aiosqlite` 或 `sqlite3` + 线程） | 零部署，单文件可拷走 |
| 协议 | `pymodbus`（TCP Client + Server） | 工业标准 Modbus TCP，模拟从站 + 主站采集 |
| 调度 | `asyncio` 周期任务 | 单进程内跑采集循环 |
| 前端 | 原生 HTML/CSS/JS + Chart.js（本地 vendored） | 无 Node 构建链，双击可看 |
| 测试 | `pytest` + `httpx` ASGI | 协议与 API 可测 |

**明确不用**：Docker、InfluxDB、Grafana、React、Postgres、MQTT（后续可选，不进 MVP）。

### S2.3 架构

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

单进程、单仓库、`python -m indusmon` 一键拉起模拟器 + 采集器 + API + 静态页。

### S2.4 数据模型

**devices**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | 设备 ID，如 `boiler-01` |
| name | TEXT | 显示名 |
| host | TEXT | Modbus TCP 主机 |
| port | INTEGER | 端口（模拟器默认 5020） |
| unit_id | INTEGER | 从站地址 |
| poll_interval_ms | INTEGER | 采集周期，默认 1000 |
| enabled | INTEGER | 0/1 |
| created_at | TEXT ISO8601 | |

**tags**（每设备的测点）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| device_id | TEXT FK | |
| name | TEXT | 如 `temp_out` |
| register | INTEGER | 保持寄存器地址 |
| data_type | TEXT | `uint16` \| `int16` \| `float32`（两寄存器） |
| scale | REAL | 工程量换算系数，默认 1 |
| offset | REAL | 默认 0 |
| unit | TEXT | 如 `°C` |
| limit_hi | REAL NULL | 高报阈值 |
| limit_hihi | REAL NULL | 高高报阈值 |
| limit_lo | REAL NULL | 低报阈值（可选） |

**readings**

| 字段 | 类型 | 说明 |
|------|------|------|
| ts | INTEGER | epoch ms |
| device_id | TEXT | |
| tag | TEXT | tag name |
| value | REAL | 工程量 |
| quality | INTEGER | 0=good, 1=uncertain, 2=bad |

索引：`(device_id, tag, ts)`。

**alerts**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| ts | INTEGER | 触发时间 |
| device_id | TEXT | |
| tag | TEXT | |
| level | TEXT | `hi` \| `hihi` \| `lo` |
| value | REAL | 触发值 |
| limit | REAL | 阈值 |
| state | TEXT | `active` \| `cleared` |
| cleared_ts | INTEGER NULL | |

告警去重：同一 `(device_id, tag, level)` 仅允许一条 `active`；恢复到阈值回差内后置 `cleared`。

### S2.5 模拟从站（Simulator）

- 内置进程内 Modbus TCP Server，监听 `127.0.0.1:5020`（可配）。
- 预置 **2 台虚拟设备**（不同 unit_id）：
  1. `boiler-01` 锅炉：蒸汽温度、压力、液位、燃烧器状态
  2. `line-02` 产线：电机电流、转速、振动、计数
- 波形：正弦 + 漂移 + 高斯噪声 + 偶发尖峰（便于演示告警）。
- 提供 `scripts/spike_demo.py` 或 API `POST /api/v1/sim/spike` 人为制造超限，便于演示告警闭环。

### S2.6 采集引擎（Collector）

- 按设备 `poll_interval_ms` 并发读取该设备全部 tags。
- 连接失败：`quality=2` 不写坏值（或写入 bad 点，二选一：**MVP 选择不写坏值，仅计数器/日志**），连续失败 N 次后可产生 `comm_lost` 日志（不进 alerts 表）。
- 批量写入 SQLite（每轮一次事务）。
- 可通过 API 动态 enable/disable 设备。

### S2.7 告警引擎

- 每次成功入库后对 value 评估阈值。
- 优先级：`hihi` > `hi` > `lo`。
- 回差：清除条件为 value 回到 `limit * 0.98`（高报）或 `limit * 1.02`（低报）内，避免抖动刷屏。
- 提供 `GET /api/v1/alerts` 过滤查询与 `POST /api/v1/alerts/{id}/ack`（MVP 仅标记，不删）。

### S2.8 HTTP API（`/api/v1`）

| Method | Path | 说明 |
|--------|------|------|
| GET | `/health` | 存活 |
| GET | `/devices` | 设备列表（含 tags） |
| POST | `/devices` | 注册设备 |
| PATCH | `/devices/{id}` | 更新 enabled/interval 等 |
| GET | `/readings?device_id&tag&from&to&limit` | 历史查询 |
| GET | `/readings/latest` | 全部 tag 最新值 |
| GET | `/series?device_id&tag&from&to` | 曲线用序列（自动降采样） |
| GET | `/alerts?state&device_id` | 告警列表 |
| POST | `/alerts/{id}/ack` | 确认告警 |
| POST | `/sim/spike` | 模拟尖峰（演示） |
| GET | `/metrics` | 采集轮次、点数、错误计数（简单 JSON） |
| GET | `/` | 监控看板 HTML |
| GET | `/stream` | SSE 实时推送最新读数 |

SSE 消息：`{"ts":..., "readings": [{device_id, tag, value, unit}, ...]}`，默认约 1s 推送。

### S2.9 前端看板（单页）

- 设备卡片：最新值 + 质量色点 + 单位。
- 实时曲线：选 tag 后 SSE 滚动曲线（Chart.js line）。
- 历史区间查询：时间范围 → 调用 `/series`。
- 告警面板：active 列表 + 红/橙色标识 + ack 按钮。
- 深浅色：默认深色工业风（深灰底、青绿/琥珀强调色）。

### S2.10 配置

环境变量 / `.env`（可选）：

| 变量 | 默认 |
|------|------|
| `INDUSMON_DB` | `./data/indusmon.db` |
| `INDUSMON_HOST` | `127.0.0.1` |
| `INDUSMON_PORT` | `8080` |
| `INDUSMON_SIM_PORT` | `5020` |
| `INDUSMON_POLL_MS` | `1000` |
| `INDUSMON_SEED_DEMO` | `1`（启动时确保演示设备存在） |

### S2.11 启动与工程结构

```
indusmon/
  pyproject.toml
  README.md
  LICENSE
  src/indusmon/
    __init__.py
    __main__.py          # python -m indusmon
    app.py               # FastAPI factory
    config.py
    db.py
    models.py
    simulator.py
    collector.py
    alerts.py
    api/
      __init__.py
      routes.py
    web/
      static/
        index.html
        app.js
        style.css
        vendor/chart.umd.min.js
  scripts/
    seed_demo.py
  tests/
    test_alerts.py
    test_collector_scale.py
    test_api.py
    test_sim_roundtrip.py
```

一键启动：

```bash
pip install -e ".[dev]"
python -m indusmon
# 打开 http://127.0.0.1:8080
```

### S2.12 测试边界

| 测试 | 验收 |
|------|------|
| `test_alerts` | 超 hi/hihi 产生 active；回差清除；同 tag 不重复 active |
| `test_collector_scale` | raw register → scale/offset → 工程量正确 |
| `test_api` | devices/readings/alerts/health 契约；未注册设备 404 |
| `test_sim_roundtrip` | pymodbus client 读模拟从站，值域合理 |

不做：真实硬件、并发压测、鉴权、多用户。

### S2.13 错误与边界行为

- 未知 device/tag 查询 → 404
- 时间范围倒置 → 400
- 模拟器端口占用 → 启动失败并提示改 `INDUSMON_SIM_PORT`
- DB 目录不存在 → 自动创建
- SSE 客户端断开 → 服务端取消任务，不影响采集

### S2.14 简历/README 叙事要点

- 工业标准 Modbus TCP 接入 + 内置从站模拟
- 多线程周期采集引擎与质量位
- SQLite（WAL + 线程本地连接）时序写入与降采样查询
- 阈值告警（回差去抖）与 SSE 实时看板
- 单命令本地演示、pytest 覆盖核心路径

## [S3] Out of Scope

- 用户登录 / JWT / RBAC / 审计
- MQTT、OPC-UA、Kafka 上云
- InfluxDB / Timescale / Grafana
- React/Vue 构建链
- 真实 PLC/传感器联调
- 工艺流程图 SCADA 组态
- 多节点部署、K8s、容器
- 移动端 App

## Tasks

- [x] T1: 项目骨架与依赖（pyproject、包结构、config、db schema 初始化）— acceptance: `pip install -e ".[dev]"` 成功；`python -c "import indusmon"` 成功；空库可创建表 (covers: S2.2, S2.4, S2.10, S2.11)
- [x] T2: Modbus 模拟从站与演示设备种子 — acceptance: 客户端可读两台虚拟设备寄存器；波形随时间变化 (covers: S2.5)
- [x] T3: 采集引擎入库 — acceptance: 启动后 readings 表持续增长；scale/offset 正确；失败不写坏值 (covers: S2.6; depends: T1, T2)
- [x] T4: 告警引擎与 API — acceptance: 尖峰可产生 hi/hihi active；回差后 cleared；ack 可用 (covers: S2.7, S2.8; depends: T3)
- [x] T5: REST + SSE + 静态看板 — acceptance: `/` 可看设备/曲线/告警；SSE 实时刷新；历史查询可用 (covers: S2.8, S2.9; depends: T3, T4)
- [x] T6: 测试与 README — acceptance: `pytest` 全绿；README 含架构图、启动步骤、API 摘要、截图位 (covers: S2.12, S2.14; depends: T1–T5)
