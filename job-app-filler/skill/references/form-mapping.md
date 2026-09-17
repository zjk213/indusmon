# 北森类网申表栏目映射（form-mapping）

启发式对照表。**以页面 snapshot 为准**，不要写死 CSS 选择器。

## 栏目 → 档案字段

| 表单栏目（常见文案） | 档案路径 | 备注 |
|----------------------|----------|------|
| 姓名 | `person.name` | |
| 性别 | `person.gender` | 单选 |
| 民族 | `person.nation` | 下拉可搜「汉」 |
| 出生日期 | `person.birth` | 日期控件；能从身份证带出则确认 |
| 身份证号 | `person.id_number` | 敏感；勿截图全页 |
| 手机 / 联系电话 | `person.phone` | |
| 邮箱 | `person.email` | |
| 政治面貌 | `person.political` | |
| 籍贯 | `person.origin` | |
| 现居住地 | `person.residence` | |
| 最高学历 / 学位 | `education.edu_level` / `degree` | |
| 毕业院校 | `education.school` | |
| 学院 | `education.college` | |
| 专业 | `education.major` | |
| 入学 / 毕业时间 | `education.edu_start` / `edu_end` | |
| 学号 | `education.student_id` | 可选 |
| GPA / 绩点 | `education.gpa` | |
| 排名 / 综测 | `education.rank_text` | 有的表要「专业排名%」 |
| 获奖情况 | `awards[]` | 见下节 |
| 证书 / 资格证书 | `certs[]` | |
| 项目经历 / 实践经历 | `projects[]` | |
| 校内职务 | 用户补充或 projects | |
| 自我评价 | `summary` | 先草稿后确认 |
| 期望工作地点 | `intent.city` | |
| 期望岗位 | `intent.role` | |
| 期望年薪/月薪 | `intent.salary_expect` | 用户定 |
| 是否接受调剂 | 问用户 | |
| 是否 2026 届择业期未就业 | 问用户 | 2027 届一般选否 |
| 有无近亲属 | `relatives_in_target` + 用户确认 | |
| 渠道来源 / 内推码 | 问用户 | |

## 获奖子表字段

| 表单字段 | 档案 |
|----------|------|
| 获奖名称 | `awards[].name` |
| 获奖时间 | `awards[].date` |
| 获奖级别 | `awards[].level`（国家级/省级/校级） |
| 颁奖单位 | 档案可选；没有则留空 |

排序：国家级 → 省级 → 校级 → 其他；同级按时间倒序。

## 项目/实践子表

| 表单字段 | 档案 |
|----------|------|
| 名称 | `projects[].name` |
| 角色/职务 | `projects[].role` |
| 起止时间 | `projects[].period` |
| 描述 | `projects[].summary` |

## 填写手法

1. `snapshot` 拿 ref → `fill` / `select` / `click`  
2. 下拉：搜索框输入「贵州省」→ 点「贵州省」  
3. 多段「添加」按钮循环，每段填完再 snapshot 一次（DOM 会变）  
4. 标签文案变体：「新增获奖」「添加获奖情况」「+ 添加」都当同一类控件  
5. 必填红星（`*`）优先填；非必填没有数据就跳过  

## 站点差异

| 站点 | 线索 |
|------|------|
| 北森 zhiye.com | 校招网申常见；URL 含 zhiye / campus |
| 其它 HR SaaS | 按 snapshot 改映射，流程不变 |

扩展新站点：在本文件追加一节「文案差异表」，不要改 SKILL.md 主流程。  
