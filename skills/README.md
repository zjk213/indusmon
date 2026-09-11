# Skills

本仓库存放可安装的 Agent Skill（MiMo Desktop / Claude Code 兼容的 `SKILL.md` 文件夹）。

## job-app-filler

网申表智能填表助手：读本地简历档案，用 Playwright/CDP 填写北森类网申；验证码与最终提交必须人工。

### 安装到本机

**方式 A — 拷贝到全局 skills 根（MiMo Desktop / Claude Code）**

```powershell
# Windows 示例
$dest = "$env:USERPROFILE\.claude\skills\job-app-filler"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Recurse -Force .\skills\job-app-filler\* $dest
```

**方式 B — 仅当前项目**

```powershell
Copy-Item -Recurse -Force .\skills\job-app-filler .\.claude\skills\job-app-filler
```

新对话中会自动扫描；也可在 MiMo Desktop「插件」页看到显示名「网申填表助手」。

### 使用

1. 复制 `skills/job-app-filler/assets/profile.example.yaml` 改成你的档案（**不要提交真实身份证号**）
2. 对 Agent 说：`帮我填这个网申 <岗位URL>，档案在 <路径>`
3. 按提示完成登录、验证码、上传与提交

### 目录

| 路径 | 作用 |
|------|------|
| `SKILL.md` | 主流程与触发说明 |
| `references/` | 表单映射、档案字段、安全清单 |
| `assets/profile.example.yaml` | 脱敏模板 |
| `locales/` | MiMo 插件页显示名 |
