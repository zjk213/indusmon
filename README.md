# mimo — 本地工作区（两个独立项目）

| 目录 | GitHub | 说明 |
|------|--------|------|
| [`indusmon/`](indusmon/README.md) | [zjk213/indusmon](https://github.com/zjk213/indusmon) | 工业数采监控平台 |
| [`job-app-filler/`](job-app-filler/README.md) | [zjk213/job-app-filler](https://github.com/zjk213/job-app-filler) | 网申填表 Agent Skill |

本地放在一起方便管理；**GitHub 上是两个独立仓库**，互不隶属。  
`job-app-filler/` 在父仓库中已被忽略（`.gitignore`），其自身是独立 git 仓库。

## 快速入口

**IndusMon**

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
