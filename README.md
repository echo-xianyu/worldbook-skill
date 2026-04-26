# SillyTavern 世界书制作机 — World Book Maker

一句话让 AI 读轻小说/设定集，自动生成结构化世界书 JSON。

**注意：本项目基本由AI生成，可能会出现意料之外的问题。作者并不很懂编程，但欢迎提出issue。**

---

## 这是什么

一个 **AI Skill + CLI 工具** 的组合包。给 AI 装上它，SAY：

> "帮我读这本轻小说，生成世界书，把所有角色、世界观做成条目"
> "为我生成一个有关于赛车的世界书"
> "写一个学习这个小说作者写作风格的世界书"

AI 就会自动做三件事：
1. **读** — 理解小说/设定文本
2. **拆** — 按角色卡编写铁律提取角色、世界观、场景、NPC
3. **生成** — 输出可直接导入 SillyTavern 的世界书 JSON

## 功能一览

| 功能 | 说明 |
|------|------|
| 轻小说→世界书 | 喂文本，AI 自动抽取角色/世界观，生成 JSON |
| CLI 管理 | 新建/添加/编辑/删除/列表，全命令行操作 |
| 批量操作 | `--batch` 一次性从 JSON 创建全部条目 |
| 8 种注入位置 | ↑Char ↓Char ↑AT ↓AT @D ↑EM ↓EM Outlet |
| 单角色/多角色卡 | 自动按铁律配置蓝灯/绿灯策略 |
| 条目编写铁律 | 内置角色卡编写指南，生成高质量条目 |

## 支持场景

| 场景 | 使用的 reference |
|------|-----------------|
| 原创角色卡/世界书 | character-guide + worldbuilding-guide + config-guide |
| 轻小说/游戏转化 | conversion-guide + 全部 extract-* + 全部创作 guide |
| 纯世界观设定 | worldbuilding-guide + config-guide |
| 物品/能力设定 | extract-item + worldbuilding-guide + config-guide |
| 文风提取 | extract-style + config-guide |
| 故事/章节提取 | extract-story + config-guide |
| 修改已有世界书 | query.py + 对应内容类型的 reference |

---

## 使用：

把 `world-book-skill/` 文件夹装进你的 AI Agent（如 Codex/claude 等支持 skill 的终端），AI 就能独立完成：

- 读取用户提供的轻小说/设定文本
- 按 `references/entry-conventions.md` 铁律提取角色信息
- 按 `references/position-guide.md` 配置注入位置
- 调用 `scripts/world-book-create.py` 生成 JSON 文件

---

## 目录结构

```
world-book-skill/
├── SKILL.md                     # 技能入口：分步工作流 + 工具使用指引
├── agents/openai.yaml           # 技能注册元数据
├── scripts/
│   ├── world-book-create.py    # 世界书 JSON 增删改查 CLI
│   └── query.py                # 世界书轻量查询/导出 CLI
└── references/
    ├── guide.md                # 场景路由器（AI 第一步读取）
    ├── entry-conventions.md    # 总索引
    ├── character-guide.md      # 角色条目创作铁律
    ├── worldbuilding-guide.md  # 世界观写作 + 压缩 + 嵌套
    ├── config-guide.md         # 世界书配置规则
    ├── position-guide.md       # ST 注入位置参考
    ├── extract-worldbuilding.md # 世界观提取指南
    ├── extract-character.md    # 角色提取指南
    ├── extract-item.md         # 物品/能力提取创建指南
    ├── extract-story.md        # 故事/章节提取指南
    ├── extract-style.md        # 文风提取指南
    └── conversion-guide.md     # 转化完整工作流
```

## 依赖

- Python 3.8+
- SillyTavern（用于导入生成的 JSON）

## 更多

详见 `world-book-skill/SKILL.md` 查看完整命令参考。

---

# 更新日志

## v2.0 — 2026-04-26

### 新增脚本
- `scripts/query.py` — 世界书轻量查询/导出工具。支持总览摘要、完整条目查询（兼容 `world-book-create.py --batch-edit` 输入）、关键词搜索、极简浏览、嵌套引用解析。省去模型阅读原始 JSON 的大量 token 开销。

### 新增 Reference 文件（7个）
- `references/guide.md` — 场景路由器。模型第一步必读，自判任务类型后选择对应指南
- `references/conversion-guide.md` — 轻小说/游戏转化完整工作流（通读→大纲→复读重要章节→逐条创建→验证）
- `references/extract-item.md` — 物品/能力/装备提取与创建指南（武器/防具/道具/技能/体系，含 XML 模板）
- `references/extract-worldbuilding.md` — 世界观提取指南
- `references/extract-character.md` — 角色提取指南（XML 格式输出）
- `references/extract-style.md` — 文风提取指南
- `references/extract-story.md` — 故事/章节提取指南（一章一条目，含 rp_hooks）

### 拆分原有 Reference
- `references/entry-conventions.md` → 拆分为：
  - `references/character-guide.md` — 角色条目创作铁律（XML 结构，更丰满的字段）
  - `references/worldbuilding-guide.md` — 世界观写作 + 压缩 + 分层 + 嵌套引用
  - `references/config-guide.md` — 世界书配置规则（位置/激活/顺序/递归/关键词）
- 原 `entry-conventions.md` 保留为总索引

### SKILL.md 重写
- 加入**分步工作流**：场景识别（读取 guide.md）→ 大纲先行（outline.txt）→ 复读重要章节 → 写入总纲 → 逐条填充 → 验证
- 加入章节行号索引 + 重要章节标注 + 强制复读机制
- 完整记载 `world-book-create.py` 和 `query.py` 的全部操作（新建/添加/编辑/删除/批量/文件读取/查询/搜索/嵌套解析）
- 新增嵌套引用说明（`@UID` / `@名称`）

### 角色条目格式升级
- 从 YAML 键值对升级为 **XML 结构**
- 新增字段：声线、三围、MBTI、核心驱动力、习惯、隐藏面
- 能力增加 `<acquisition>` 来源说明和编号化 `<effects>` 列表
- 关系改为每人一段叙事性描述

### 文件结构变化

```
world-book-skill/
├── SKILL.md                         # 重写
├── README.md                        # 新增
├── agents/openai.yaml               # 更新
├── scripts/
│   ├── world-book-create.py         # 不变
│   └── query.py                     # 新增
└── references/
    ├── guide.md                     # 新增
    ├── entry-conventions.md         # 改为总索引
    ├── character-guide.md           # 新增（拆分+升级）
    ├── worldbuilding-guide.md       # 新增（拆分）
    ├── config-guide.md              # 新增（拆分）
    ├── position-guide.md            # 不变
    ├── conversion-guide.md          # 新增
    ├── extract-worldbuilding.md     # 新增
    ├── extract-character.md         # 新增
    ├── extract-item.md              # 新增
    ├── extract-story.md             # 新增
    └── extract-style.md             # 新增
```

---

## v1.0 — 2025

### 初始版本
- `SKILL.md` — 基础角色卡编写指引
- `scripts/world-book-create.py` — JSON 增删改查 CLI
- `references/entry-conventions.md` — 角色卡 + 世界观编写铁律（单一指南）
- `references/position-guide.md` — ST 注入位置参考
- `agents/openai.yaml` — 技能注册

