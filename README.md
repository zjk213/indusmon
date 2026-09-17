# IndusMon — 工业设备数采与监控平台

轻量级工业数据采集与监控（SCADA-lite）示例项目：**Modbus TCP 接入 + 周期采集 + SQLite 时序存储 + 阈值告警 + 实时看板**。  
单进程、零 Docker、Windows/Linux 一键启动，适合自动化 / 工业物联网方向的作品集与本地演示。

## 快速开始

```powershell
cd indusmon
pip install -e ".[dev]"
python -m indusmon
```

- 看板：<http://127.0.0.1:8080/>
- OpenAPI：<http://127.0.0.1:8080/docs>

完整说明见 [`indusmon/README.md`](indusmon/README.md)。

## 仓库结构

```
indusmon/
  src/          # 应用源码
  tests/        # pytest
  scripts/      # 冒烟与种子脚本
  docs/         # 设计文档
  pyproject.toml
```

## License

MIT
