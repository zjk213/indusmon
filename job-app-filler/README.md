# job-app-filler — 网申表智能填表 Skill

读本地简历档案，用浏览器（Playwright / CDP）填写北森类网申表；**验证码、滑块、短信、签名、上传、最终提交必须人工**。

本目录是独立的 skill 工程，与仓库里 IndusMon 平台代码分开。

## 目录

```
job-app-filler/
  skill/          # 真正要安装的 SKILL.md 包（拷贝这个）
  docs/spec.md    # 设计说明
  scripts/        # 结构校验
  README.md
```

## 准备档案

1. 复制 `skill/assets/profile.example.yaml`
2. 改成你的真实信息（姓名、教育、获奖、项目）
3. **不要把含真实身份证号的文件提交到 Git**

## 在其它 AI 编程工具里安装

核心只有一件事：让 Agent 的 **skills 扫描目录** 里出现 `job-app-filler/SKILL.md`。

### Claude Code（Anthropic）

全局：

```powershell
$dest = "$env:USERPROFILE\.claude\skills\job-app-filler"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Recurse -Force ".\skill\*" $dest
```

仅当前项目：

```powershell
Copy-Item -Recurse -Force ".\skill" ".\.claude\skills\job-app-filler"
```

新开会话后，描述里含「网申 / 填北森 / 帮我填报名表」时会自动加载；也可直接说「使用 job-app-filler 技能」。

### MiMo Desktop

1. 按上面拷到 `~/.claude/skills/job-app-filler/`（Windows：`%USERPROFILE%\.claude\skills\job-app-filler`）
2. 新对话；插件页可见显示名「网申填表助手」
3. 或在对话里点/搜索该 skill

### Cursor

Cursor 不完全兼容 `SKILL.md` 自动发现，两种做法：

**A. 项目 Rules（推荐）**  
把 `skill/SKILL.md` 正文（去掉 YAML 头）放到：

```
.cursor/rules/job-app-filler.mdc
```

frontmatter 用 Cursor 格式，例如：

```markdown
---
description: 网申填表：读档案后用浏览器填北森类表单，禁止自动提交
globs:
alwaysApply: false
---
（粘贴 SKILL.md 的正文）
```

**B. 对话粘贴**  
需要时把 `skill/SKILL.md` + 档案路径丢进聊天，并说明「按此 skill 执行，禁止自动提交」。

### OpenCode / 其它支持 skills 目录的 CLI

常见全局根（以该工具文档为准）：

```text
~/.config/opencode/skills/job-app-filler/
~/.agents/skills/job-app-filler/
```

Windows 上对应 `%USERPROFILE%\.config\opencode\skills\...`。把 `skill/` 内容拷进去即可。

### GitHub Copilot / 纯 IDE 补全

没有 skills 运行时的话：

1. 在仓库放 `docs/job-app-filler-prompt.md`（可从 SKILL.md 导出）
2. 每次填表时手动 `@` 引用该文件 + 提供档案路径 + 岗位 URL

## 怎么对 Agent 说（触发示例）

- 「帮我填这个网申 `https://…`，档案在 `D:/…/my-profile.yaml`」
- 「打开北森报名表，把获奖情况都填上」
- 「网申填表，只填教育和项目，提交前停一下」

Agent 应：

1. 读档案并校验必填字段  
2. 连接浏览器 / 用 Playwright 打开 URL  
3. 按 `skill/references/form-mapping.md` 分栏填写  
4. 获奖批量循环  
5. 验证码 / 提交前停下，让你操作  

## 校验 skill 结构

```powershell
python .\scripts\validate_skill.py
```

在本目录（`job-app-filler/`）下执行；期望输出 `PASS`。

## 安全底线

- 永不自动点「提交」  
- 禁止编造奖项、成绩、证书  
- 身份证号只进表单控件，不进仓库/日志  
- 验证码与滑块不做破解  
