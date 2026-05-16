# card-generator.py 使用指南

`card-generator.py` 是基于 Python 3.8+ 标准库的 `chara_card_v3` 角色卡 JSON 生成工具。通过配置文件驱动，自动生成包含世界书、正则脚本、MVU系统、HTML美化在内的完整角色卡。

---

## 基本概念

### 工作流

```
AI 生成配置JSON → 用户确认 → card-generator.py 生成角色卡JSON → Python脚本导入酒馆
```

你也可以反向操作：
```
已有角色卡JSON → card-generator.py --decompile 解包 → 修改配置 → 重新生成
```

### 依赖

- Python 3.8+（仅标准库，无外部依赖）
- JSON 文件使用 UTF-8 编码
- 所有 UUID 自动生成
- 创建时间自动设为当前 UTC 时间

---

## 模式与命令

| 模式 | 命令 | 说明 |
|------|------|------|
| 从配置生成 | `python card-generator.py --config config.json -o card.json` | 从JSON配置生成角色卡 |
| 交互式创建 | `python card-generator.py --interactive` | 命令行问答式逐步创建 |
| **解包** | `python card-generator.py --decompile card.json -o config.json` | 从角色卡反向提取配置（含MVU/状态栏检测） |
| **原位编辑** | `python card-generator.py card.json --edit --name "新名"` | 修改已有角色卡的字段 |
| **列表** | `python card-generator.py --list card.json` | 查看角色卡概要 |
| 提取模板 | `python card-generator.py --extract card.json -o template.json` | 提取简化配置模板 |
| 验证 | `python card-generator.py --validate card.json` | 检查角色卡JSON结构合法性 |

---

## 配置JSON格式

### 完整配置结构

```json
{
  "card": {
    "name": "角色名",
    "description": "YAML格式的角色描述",
    "personality": "性格简述",
    "scenario": "场景设定",
    "first_mes": "默认开场...<StatusPlaceHolderImpl/>",
    "creator_notes": "作者备注",
    "system_prompt": "系统提示词",
    "post_history_instructions": "历史后指令",
    "creator": "作者名",
    "character_version": "1.0",
    "alternate_greetings": [
      "开场2...<StatusPlaceHolderImpl/>",
      "开场3...<StatusPlaceHolderImpl/>"
    ]
  },
  "extensions": {
    "talkativeness": "0.5"
  },
  "worldbook": {
    "name": "世界书名",
    "entries": [
      {
        "comment": "条目名称",
        "keys": ["触发词1,触发词2"],
        "content": "条目内容（YAML格式，可XML包裹）",
        "constant": true,
        "position": "after_char",
        "order": 100,
        "enabled": true,
        "depth": 4
      }
    ]
  },
  "regex_scripts": [
    {
      "name": "正则名称",
      "findRegex": "/<tag>.*?<\\/tag>/gs",
      "replaceString": "<div>HTML美化</div>",
      "markdownOnly": true,
      "placement": [2],
      "runOnEdit": true
    }
  ],
  "tavern_helper": {
    "scripts": [
      {
        "name": "自定义脚本",
        "content": "import '...';",
        "buttons": [{"name": "按钮名", "visible": true}]
      }
    ]
  },
  "mvu": {
    "enabled": true,
    "schema_script": "完整的Zod Schema JS代码",
    "initvar": "角色名:\n  好感度: 20\n  心情: 平静",
    "update_rules": "变量更新规则",
    "output_format": "变量输出格式",
    "variable_list_path": "stat_data",
    "hide_regex": true,
    "beautify_regex": true
  },
  "statusbar": {
    "enabled": true,
    "html": "完整的HTML状态栏代码",
    "hide_regex": true
  }
}
```

### card 字段（必填）

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 角色卡名称（必填） |
| description | string | 角色描述，YAML格式 |
| first_mes | string | 默认开场，末尾含 `<StatusPlaceHolderImpl/>` |
| alternate_greetings | string[] | 可选开场，也建议含占位符 |
| personality | string | 性格简述（可选） |
| scenario | string | 场景设定（可选） |
| creator_notes | string | 作者备注（可选） |
| creator | string | 作者名（可选） |
| character_version | string | 版本号（可选） |

### worldbook（可选）

条目 `position` 取值：
- `"before_char"` — ↑Char（角色定义之前）
- `"after_char"` — ↓Char（角色定义之后）
- `"at_depth"` — @D（深度注入）

注意：`prevent_recursion` 和 `exclude_recursion` 默认为 true，无需手动指定。

### mvu（仅 enabled=true 时生效）

| 字段 | 类型 | 说明 |
|------|------|------|
| enabled | boolean | 启用MVU |
| schema_script | string | Zod Schema JS代码（含 registerMvuSchema） |
| initvar | string | YAML格式变量初始值 |
| update_rules | string | 变量更新规则 |
| output_format | string | 输出格式（可选） |
| variable_list_path | string | 变量路径（默认 stat_data） |
| hide_regex | boolean | 自动添加变量更新隐藏正则 |
| beautify_regex | boolean | false | 自动添加变量更新美化正则 |
| inline_cdn | boolean | false | 使用内联模式（不依赖CDN加载 bundle.js） |

**启用 mvu 后自动生成：**
1. MVU 核心脚本（bundle.js）
2. Zod Schema 脚本
3. `[initvar]` 条目（enabled=false）
4. 变量列表条目（@D depth=0）
5. 变量更新规则条目（@D depth=0）
6. 变量输出格式条目（@D depth=0）
7. 去除变量更新正则（minDepth=4）
8. 变量更新美化正则 ×2

### statusbar（仅 enabled=true 时生效）

| 字段 | 类型 | 说明 |
|------|------|------|
| enabled | boolean | 启用状态栏 |
| html | string | 完整HTML代码 |
| hide_regex | boolean | 自动添加隐藏正则 |

**启用 statusbar 后自动生成：**
1. 状态栏美化正则（`<StatusPlaceHolderImpl/>` → HTML）
2. 状态栏隐藏正则（不发送给AI）

### regex_scripts（可选）

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| name | string | | 正则名称 |
| findRegex | string | | `/pattern/flags` 格式 |
| replaceString | string | `""` | 替换内容 |
| markdownOnly | boolean | `true` | 仅显示 |
| promptOnly | boolean | `false` | 仅提示词 |
| placement | number[] | `[2]` | [1]=显示, [2]=提示词 |
| minDepth | number\|null | `null` | 最小深度 |
| maxDepth | number\|null | `null` | 最大深度 |
| runOnEdit | boolean | `false` | 编辑时运行 |

---

## AI 工作流：生成配置JSON → 生成角色卡

作为角色卡/世界书管理助手，你应该按以下流程操作：

### 步骤1：与用户交互，生成配置JSON内容

根据 `card-writing-guide.md` 的规范，通过对话确定：
- 角色档案（description YAML）
- 性格设定（世界书条目 content）
- 世界观设定（世界书条目 content）
- 开场白（first_mes + alternate_greetings）
- 是否需要 MVU（仅用户要求时）
- 是否需要 HTML 美化（仅用户要求时）

### 步骤2：输出配置JSON草稿

将以上内容组装为配置 JSON，展示给用户确认：

```json
{
  "card": {
    "name": "角色名",
    "description": "角色档案的YAML内容",
    "first_mes": "开场白文本<StatusPlaceHolderImpl/>",
    "alternate_greetings": ["开场2...", "开场3..."],
    "creator": "作者名"
  },
  "worldbook": {
    "name": "角色名_世界书",
    "entries": [
      {"comment": "世界背景","content": "...","constant":true,"position":"before_char","order":1,"keys":[""]},
      {"comment": "角色性格","content": "...","constant":true,"position":"after_char","order":30,"keys":[""]}
    ]
  }
}
```

### 步骤3：用户确认后生成

```bash
python card-generator.py --config config.json -o 角色名.json
```

### 步骤4：验证

```bash
python card-generator.py --validate 角色名.json
python card-generator.py --list 角色名.json
```

---

## 解包 → 修改 → 重新生成流程

### 解包

```bash
python card-generator.py --decompile 已有角色卡.json -o config.json
```

输出与 `--config` 输入格式完全兼容，自动检测：
- MVU 配置（Schema脚本、initvar、变量列表、更新规则、输出格式）
- HTML 状态栏配置（美化正则、隐藏正则）
- 所有世界书条目
- 所有正则脚本
- 酒馆助手脚本

### 修改配置

编辑 `config.json`，修改角色设定、更新世界书条目、调整 MVU 配置等。

### 重新生成

```bash
python card-generator.py --config config.json -o new_card.json
```

### 原位编辑（小修改）

```bash
# 修改名称和描述
python card-generator.py card.json --edit --name "新名" --description "新描述"

# 追加开场
python card-generator.py card.json --edit --add-greeting "新开场..."

# 启用MVU
python card-generator.py card.json --edit --enable-mvu true

# 启用状态栏
python card-generator.py card.json --edit --enable-statusbar true
```

---

## 配置JSON中的世界书条目注意事项

1. **不要包含** initvar 和变量列表条目——它们由 `mvu.enabled=true` 自动生成
2. 条目 content 使用 YAML 格式（可用 XML 标签包裹）
3. `prevent_recursion` 和 `exclude_recursion` 默认为 true
4. 单角色卡所有条目 constant=true
5. 多角色卡：速览 constant=true，详情 constant=false + keys

---

## 测试命令

```bash
# 查看角色卡概要
python card-generator.py --list card.json

# 验证结构
python card-generator.py --validate card.json

# 生成测试角色卡
python card-generator.py --config 测试角色卡_config.json -o 输出.json
```

---

## 自动校验与安全特性（本地修补）

本地的 card-generator.py 比上游版本多了以下校验，生成时自动执行：

### 配置输入校验
- 缺 `card.name` 或同时缺 `first_mes`/`description` → 报错中断
- MVU 启用但缺 `schema_script`/`initvar`/`update_rules` → 打印警告（不中断）
- MVU 启用但开场缺 `<StatusPlaceHolderImpl/>` → 打印警告
- `statusbar.enabled=true` 但无 `html` → 报错中断

### MVU 风格冲突检测
检测 `schema_script` 是否混用了 `registerMvuSchema`（zod风格）和 `_.add()`/`_.set()`/`getvar()`（beta风格）。两种风格不兼容，混用时报错中断。

### 正则自动排序与校验
生成后在后台执行 `_sort_and_validate_regex`：
1. **排序**：状态栏美化正则 → 全局美化正则（`<chat>`包裹）→ 其他正则
2. **/s flag 自动补全**：全局美化正则缺 dotAll flag 时自动加上
3. **`white-space: pre-wrap` 检测**：全局美化 HTML 模板中内层内容区缺少此属性时报警

### 内联 CDN 模式
设 `mvu.inline_cdn: true` 则 MVU 核心脚本以骨架备注形式嵌入（不加载 CDN 的 bundle.js）。适合网络受限环境，需手动填入实际 JS 内容。默认 `false`（从 CDN 加载）。
