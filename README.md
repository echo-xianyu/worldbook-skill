# SillyTavern 世界书制作机 — World Book Maker

一句话让 AI 读轻小说/设定集，自动生成结构化世界书 JSON。

**注意：本项目基本由AI生成，可能会出现意料之外的问题。作者并不很懂编程，但欢迎提出issue。**

## 这是什么

一个 **AI Skill + CLI 工具** 的组合包。给 AI 装上它，SAY：

> "帮我读这本轻小说，生成世界书，把所有角色、世界观做成条目"

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


## 使用：

把 `world-book-skill/` 文件夹装进你的 AI Agent（如 Codex/claude 等支持 skill 的终端），AI 就能独立完成：

- 读取用户提供的轻小说/设定文本
- 按 `references/entry-conventions.md` 铁律提取角色信息
- 按 `references/position-guide.md` 配置注入位置
- 调用 `scripts/world-book-create.py` 生成 JSON 文件

## 目录结构

```
publish/
├── world-book-skill/           # AI Skill 包（给 AI Agent 用）
│   ├── SKILL.md                # 技能入口 + 操作指令
│   ├── scripts/
│   │   └── world-book-create.py    # CLI 管理工具
│   ├── references/
│   │   ├── entry-conventions.md # 角色卡编写铁律
│   │   └── position-guide.md   # 注入位置参考
│   └── agents/
│       └── openai.yaml         # 技能名片
```

## 依赖

- Python 3.8+
- SillyTavern（用于导入生成的 JSON）

## 更多

详见 `world-book-skill/SKILL.md` 查看完整命令参考。
