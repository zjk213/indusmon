---
feature: job-app-filler
status: delivered
updated: 2026-09-11
branch: feature/job-app-filler
commits: 66fdabf..0e00c30
---

# job-app-filler — 网申表智能填表 Skill

> 交付物：MiMo/Claude 可安装的 skill 文件夹，放在本仓库 `skills/job-app-filler/`，可拷贝到 `~/.claude/skills/` 或独立上传 GitHub。
> 工作区：主 checkout 分支 `feature/job-app-filler`（沿用本仓库此前 worktree 策略覆盖：会话禁止 `git worktree add`）。

## Report

**What was built** — 可安装 Agent Skill `job-app-filler`：SKILL.md 规定触发词、档案校验、CDP/Playwright 打开北森类网申、分栏填写、获奖批量循环，以及验证码/签名/上传/**最终提交** 人工关口；`references/` 提供表单映射、档案 schema、安全清单；`assets/profile.example.yaml` 为脱敏模板；`locales/` 供 MiMo 插件页显示；`skills/README.md` 说明拷贝到 `~/.claude/skills/` 的安装步骤。

**Verification** — `python scripts/validate_job_app_skill.py` → PASS（结构、frontmatter、locales 键、无简历真实证件号、skill 目录无 README）。独立 review：T1–T4 合格，安全门完整，无 critical；随后修正 profile 校验列表与 validator 死代码。

**Journey log** — 1) 流程从用户已验证的网申任务指令抽象而来，而非臆造站点 API；2) 把「永不自动提交」写进 Important/人工关口/Out of scope 三处，防模型自作主张；3) 示例证件号必须明显假号且校验器拉黑简历真实号；4) skill 目录禁止 README，安装说明放仓库 `skills/README.md`。

## [S1] Problem

校招/社招网申表字段多、获奖条目多，手动填极慢。用户已有 Playwright + 北森（zhiye.com 等）验证经验，但每次新会话都要重新交代路径、字段映射、安全边界与操作顺序，易漏填、误提交、泄露敏感信息。

需要一个可复用 skill：在用户给出岗位 URL 后，按统一流程读档案 → 打开表单 → 分栏填写 → 汇报，且**永不自动提交**。

## [S2] Design

### S2.1 身份与安装

| 项 | 值 |
|----|-----|
| 目录 ID / name | `job-app-filler` |
| 位置（本仓库） | `skills/job-app-filler/` |
| 本机生效 | 拷贝或链接到 `~/.claude/skills/job-app-filler/` |
| 显示元数据 | `locales/zh-CN.json` + `locales/en-US.json` |

### S2.2 目录结构

```
skills/job-app-filler/
  SKILL.md
  locales/zh-CN.json
  locales/en-US.json
  references/
    profile-schema.md      # 个人档案 YAML 字段说明与示例（脱敏）
    form-mapping.md        # 北森类网申表栏目 → 档案字段映射
    safety-checklist.md    # 提交前检查与禁止事项
  assets/
    profile.example.yaml   # 可复制的档案模板（无真实证件号）
```

禁止：skill 目录内 `README.md`（规范要求）；真实身份证/手机号写入示例。

### S2.3 Frontmatter 契约

```yaml
name: job-app-filler
description: 自动填写招聘网站网申表（北森 zhiye.com 等）：读取本地简历档案，用 Playwright/CDP 填写个人信息、教育经历、获奖情况、项目实践等；验证码/滑块/签名/最终提交必须人工。当用户说「网申」「填报名表」「帮我填北森」「获奖情况太多不想手填」「打开岗位链接帮我填」时使用。
```

- description 同时含 WHAT + WHEN + 负向触发（最终提交人工）
- 触发词：网申、填表、北森、zhiye、报名表、获奖情况批量填

### S2.4 运行时流程（SKILL.md 正文）

1. **收集输入**：目标 URL、是否已登录、档案路径（默认询问；缺档则先引导填 `profile.example.yaml` 副本）
2. **加载档案**：读 YAML/MD；校验必填：姓名、证件号、手机、邮箱、学校、学历、毕业时间、获奖列表
3. **安全前置**：不把证件号写入日志/多余文件；截图避免整页含完整证件号（必要时打码或局部截图）
4. **打开页面**：优先用户已开浏览器 CDP（`--remote-debugging-port=9222`），否则 Playwright `msedge` channel；失败则指导手动打开
5. **Snapshot 识别**：按 `references/form-mapping.md` 栏目顺序填写
6. **获奖批量**：循环「添加获奖」——级别（国家/省/校）优先降序，时间 YYYY-MM
7. **人工关口**：验证码、短信、滑块、手写签名、附件上传选文件、**预览并提交** — 一律停下请用户操作
8. **汇报**：已填栏目、跳过项、待用户确认项；不点提交

### S2.5 表单映射（form-mapping.md 摘要）

| 表单栏目 | 档案字段 |
|----------|----------|
| 个人信息 | name, gender, nation, birth, id_number, phone, email, origin, residence, political |
| 教育经历 | school, college, major, degree, edu_start, edu_end, gpa, rank, student_id |
| 证书 | certs[] |
| 获奖情况 | awards[] {name, date, level} |
| 项目/实践 | projects[] {name, role, period, summary} |
| 求职意向 | intent.city, intent.role, intent.salary（缺省询问） |
| 自我评价 | summary（可生成后请用户改） |

未知/简历未覆盖字段：**询问用户，禁止编造**。

### S2.6 安全与合规（safety-checklist.md）

- 资料必须真实；禁止生成虚假奖项
- 敏感字段仅填表用，不复制到无关文件
- 默认不自动点「提交」
- 亲属声明、是否应届等按用户确认
- 操作失败不无限重试；连续失败 2 次停下汇报

### S2.7 安装说明（仓库级，不在 skill 内）

仓库 `skills/README.md`：如何拷贝到 `~/.claude/skills/`、MiMo Desktop 插件页加载方式、与 `~/.claude/skills` 约定一致。

### S2.8 验收方式

- [ ] SKILL.md frontmatter name/description 合法且含触发短语
- [ ] locales 两语言仅 displayName/brief
- [ ] 示例 profile 无真实身份证
- [ ] 流程覆盖：档案→打开→分栏填→获奖循环→人工关口→汇报
- [ ] 文档写明 CDP/Edge 与 Playwright 路径（与用户已验证结论一致）

## [S3] Out of Scope

- 真正执行一次网申的 E2E 自动化测试（需真实账号/岗位）
- 图形验证码识别、滑块破解
- 多站点（智联/BOSS）适配（仅写扩展点）
- 把 skill 强制安装进 `~/.claude/skills`（用户自行拷贝）
- 简历重写/求职信生成（可另做 skill）

## Tasks

- [x] T1: 创建 `skills/job-app-filler/` 骨架与 locales — acceptance: 目录与两 json 存在且 JSON 合法 (covers: S2.1, S2.2)
- [x] T2: 编写 SKILL.md 主流程 — acceptance: 含触发、步骤、人工关口、引用 references 路径 (covers: S2.3, S2.4)
- [x] T3: 编写 references + 脱敏 profile 模板 — acceptance: 三份 reference + example yaml，无真实证件号 (covers: S2.5, S2.6)
- [x] T4: 仓库 skills/README.md 安装说明 + 提交 — acceptance: 安装步骤可跟做；feature 分支 commit 完成 (covers: S2.7; depends: T1–T3)
