# 个人档案字段说明（profile-schema）

档案是填表的唯一数据来源。推荐 YAML；若用户只有 `简历.md`，可先抽字段再填表。

## 必填

```yaml
person:
  name: 周某某
  gender: 男
  nation: 汉族
  birth: "2005-02-13"          # YYYY-MM-DD
  id_number: "****************"  # 18 位，仅填表用
  phone: "186********"
  email: "you@example.com"
  political: 中共党员            # 或 共青团员 / 群众
  origin: 某省某市               # 籍贯
  residence: 某省某市某区         # 现居住地

education:
  school: 某某大学
  college: 某某学院
  major: 自动化
  degree: 学士
  edu_level: 本科               # 统招本科等
  edu_start: "2023-09"
  edu_end: "2027-06"
  student_id: "2300******"      # 可选
  gpa: 3.51                     # 可选
  rank_text: "班级综合测评第1名，专业前3%"  # 可选
```

## 列表字段

```yaml
certs:
  - name: 大学英语四级 CET-4
    date: "2024-06"
  - name: 低压电工证
    date: "2026-03"

awards:
  - name: 某省某竞赛银奖
    date: "2025-07"
    level: 省级                 # 国家级 | 省级 | 校级 | 其他
  - name: 某校优秀学生干部
    date: "2025-11"
    level: 校级

projects:
  - name: 某某系统研发
    role: 核心成员
    period: "2025.04-2025.07"
    summary: 一句话说明做了什么、结果如何
```

## 可选

```yaml
intent:
  city: 贵阳
  role: 电气/自动化工程师
  salary_expect: ""             # 用户确认后再填

summary: |
  两到四句自我评价；生成草稿后必须让用户改过再粘贴。

relatives_in_target: false      # 目标集团是否有近亲属，以用户为准
fresh_grad_policy: "2027届"     # 政策题以用户确认为准
```

## 校验规则

- 缺 `person.name` / `id_number` / `phone` / `email` / `education.school` → 不能开始填表  
- `awards[].level` 必须是枚举之一，便于排序  
- `date` 能解析为年月；写不出就问用户，不要猜  
- **示例与文档中永远不要出现真实完整身份证号**

## 与简历.md 的关系

若用户只提供简历 Markdown：

1. 抽取姓名、教育、奖项、项目  
2. 身份证/手机等简历通常没有 → 只在真正填到该框时请用户口头提供或临时粘贴  
3. 不要把证件号写回仓库文件  
