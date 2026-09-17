# mimo — 作品集 monorepo

| 子项目 | 说明 |
|--------|------|
| [`indusmon/`](indusmon/README.md) | 工业设备数采与监控平台（Modbus + FastAPI + SQLite + 看板） |
| [`job-app-filler/`](job-app-filler/README.md) | 网申表智能填表 Agent Skill（可拷到 Claude Code / MiMo / Cursor） |

两个子项目相互独立，可分别安装、运行、发布。

## 快速入口

**IndusMon 本地演示**

```powershell
cd indusmon
pip install -e ".[dev]"
python -m indusmon
# http://127.0.0.1:8080/
```

**安装网申 Skill（Claude Code / MiMo）**

```powershell
$dest = "$env:USERPROFILE\.claude\skills\job-app-filler"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Recurse -Force ".\job-app-filler\skill\*" $dest
```

详见各子目录 README。
