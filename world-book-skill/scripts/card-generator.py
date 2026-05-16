#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SillyTavern chara_card_v3 角色卡生成器
========================================
支持：从JSON配置生成 / 交互式创建 / 从现有角色卡提取模板 / 验证角色卡

用法：
  python card-generator.py --config config.json --output card.json
  python card-generator.py --interactive
  python card-generator.py --extract existing.json --output template.json
  python card-generator.py --validate card.json
  python card-generator.py --help

依赖：Python 3.8+ (仅标准库)
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone

# ============================================================
# 工具函数
# ============================================================

def parse_key_list(value):
    """将逗号分隔的触发词字符串拆分为数组，兼容已拆分的数组"""
    if not value:
        return []
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, str) and ',' in item:
                result.extend([k.strip() for k in item.split(',') if k.strip()])
            elif item:
                result.append(item)
        return result
    if isinstance(value, str):
        return [k.strip() for k in value.split(',') if k.strip()]
    return []

def gen_uuid():
    """生成UUID v4"""
    return str(uuid.uuid4())

def gen_id(prefix="id"):
    """生成带前缀的时间戳ID"""
    return f"{prefix}_{int(datetime.now().timestamp() * 1000)}_{abs(hash(str(uuid.uuid4()))) % 100000}"

def now_iso():
    """返回ISO 8601格式的当前UTC时间"""
    return datetime.now(timezone.utc).isoformat()

def escape_regex_body(text):
    """转义正则体内的 / 字符. 参照 EasyVibeCard buildFindRegexString."""
    normalized = str(text).replace("\\/", "/")
    return normalized.replace("/", "\\/")

def build_find_regex(pattern, flags="gs"):
    """构建 slash风格的 findRegex 字符串"""
    return f"/{escape_regex_body(pattern)}/{flags}"

def clamp(value, min_val, max_val):
    """限制数值范围"""
    return max(min_val, min(value, max_val))

def first(*values):
    """返回第一个非空值"""
    for v in values:
        if v is not None and v != "":
            return v
    return ""

# ============================================================
# 默认模板
# ============================================================

DEFAULT_MVU_BUNDLE = (
    "import 'https://testingcf.jsdelivr.net/gh/MagicalAstrogy/MagVarUpdate/artifact/bundle.js';"
)

# 内联模式：将CDN内容复制到本地嵌入。用户需自行下载 bundle.js 放到脚本同目录。
# 设 mvu.inline_cdn=true 时使用本地加载。
INLINE_MVU_BUNDLE = (
    "// 内联模式：请将 MagVarUpdate bundle.js 下载到此脚本同目录后取消注释以下行\n"
    "// import './bundle.js';\n"
    "// 或替换为内联 JS 内容\n"
)

DEFAULT_MVU_BUTTONS = [
    {"name": "重新处理变量", "visible": True},
    {"name": "重新读取初始变量", "visible": True},
    {"name": "清除旧楼层变量", "visible": False},
    {"name": "快照楼层", "visible": False},
    {"name": "重演楼层", "visible": False},
    {"name": "重试额外模型解析", "visible": False},
]

# ============================================================
# CardBuilder: 核心构建器
# ============================================================

class CardBuilder:
    """SillyTavern chara_card_v3 角色卡构建器"""

    def __init__(self):
        self._init_empty()

    def _init_empty(self):
        self.card = {
            "name": "",
            "description": "",
            "personality": "",
            "scenario": "",
            "first_mes": "",
            "mes_example": "",
            "creatorcomment": "",
            "avatar": "none",
            "talkativeness": "0.5",
            "fav": False,
            "tags": [],
            "spec": "chara_card_v3",
            "spec_version": "3.0",
            "data": {
                "name": "",
                "description": "",
                "personality": "",
                "scenario": "",
                "first_mes": "",
                "mes_example": "",
                "creator_notes": "",
                "system_prompt": "",
                "post_history_instructions": "",
                "tags": [],
                "creator": "",
                "character_version": "1.0",
                "alternate_greetings": [],
                "group_only_greetings": [],
                "extensions": {
                    "talkativeness": "0.5",
                    "fav": False,
                    "world": "",
                    "depth_prompt": {"prompt": "", "depth": 4, "role": "system"},
                },
                "character_book": {
                    "name": "",
                    "entries": [],
                },
            },
            "create_date": now_iso(),
        }

    # === 基本信息 ===
    def set_name(self, name):
        self.card["name"] = name
        self.card["data"]["name"] = name
        self.card["data"]["extensions"]["world"] = name
        return self

    def set_card_info(self, *, name=None, description="", personality="",
                      scenario="", creator_notes="", system_prompt="",
                      post_history_instructions="", creator="", version="1.0"):
        if name:
            self.set_name(name)
        d = self.card["data"]
        if description: d["description"] = description
        if personality: d["personality"] = personality
        if scenario: d["scenario"] = scenario
        if creator_notes: d["creator_notes"] = creator_notes
        if system_prompt: d["system_prompt"] = system_prompt
        if post_history_instructions: d["post_history_instructions"] = post_history_instructions
        if creator: d["creator"] = creator
        if version: d["character_version"] = version
        return self

    def set_talkativeness(self, value):
        v = str(value)
        self.card["talkativeness"] = v
        self.card["data"]["extensions"]["talkativeness"] = v
        return self

    # === 开场 ===
    def set_first_message(self, text):
        self.card["first_mes"] = text
        self.card["data"]["first_mes"] = text
        return self

    def add_alternate_greeting(self, text):
        self.card["data"]["alternate_greetings"].append(text)
        return self

    # === 世界书 ===
    def _make_extensions(self, *, position_num=1, depth=4, role=0,
                         prevent_recursion=True, exclude_recursion=True,
                         display_index=0, probability=100,
                         selective_logic=0, enabled=True):
        return {
            "position": position_num,
            "exclude_recursion": exclude_recursion,
            "display_index": display_index,
            "probability": probability,
            "useProbability": True,
            "depth": depth,
            "selectiveLogic": selective_logic,
            "outlet_name": "",
            "group": "",
            "group_override": False,
            "group_weight": 100,
            "prevent_recursion": prevent_recursion,
            "delay_until_recursion": False,
            "scan_depth": None,
            "match_whole_words": None,
            "use_group_scoring": False,
            "case_sensitive": None,
            "automation_id": "",
            "role": role,
            "vectorized": False,
            "sticky": 0,
            "cooldown": 0,
            "delay": 0,
            "match_persona_description": False,
            "match_character_description": False,
            "match_character_personality": False,
            "match_character_depth_prompt": False,
            "match_scenario": False,
            "match_creator_notes": False,
            "triggers": [],
            "ignore_budget": False,
        }

    def set_worldbook_name(self, name):
        self.card["data"]["character_book"]["name"] = name
        return self

    def add_worldbook_entry(self, *, comment, content, keys=None,
                            secondary_keys=None, constant=True, position="after_char",
                            position_num=1, order=100, enabled=True,
                            depth=4, use_regex=True, prevent_recursion=True,
                            exclude_recursion=True):
        keys = keys or []
        secondary_keys = secondary_keys or []
        selective = not constant
        ext = self._make_extensions(
            position_num=position_num, depth=depth,
            prevent_recursion=prevent_recursion,
            exclude_recursion=exclude_recursion,
            display_index=len(self.card["data"]["character_book"]["entries"]),
        )
        entry = {
            "id": len(self.card["data"]["character_book"]["entries"]),
            "keys": keys,
            "secondary_keys": secondary_keys,
            "comment": comment,
            "content": content,
            "constant": constant,
            "selective": selective,
            "insertion_order": order,
            "enabled": enabled,
            "position": position,
            "use_regex": use_regex,
            "extensions": ext,
        }
        self.card["data"]["character_book"]["entries"].append(entry)
        return self

    # === MVU 变量组件 ===
    def add_initvar_entry(self, yaml_content, enabled=False):
        """添加 [initvar] 变量初始化条目（before_char, 内容包裹<initvar>标签）"""
        wrapped = f"<initvar>\n{yaml_content}\n</initvar>"
        return self.add_worldbook_entry(
            comment="[initvar]变量初始化勿开",
            content=wrapped,
            constant=True, position="before_char", position_num=0,
            order=14720, enabled=enabled,
        )

    def add_variable_list_entry(self, var_path="stat_data", depth=0):
        """添加变量列表条目（@D depth=0）"""
        content = (
            "---\n"
            "<status_current_variable>\n"
            f"{{{{format_message_variable::{var_path}}}}}\n"
            "</status_current_variable>"
        )
        return self.add_worldbook_entry(
            comment="变量列表",
            content=content,
            constant=True, position="at_depth", position_num=4,
            order=14720, depth=depth,
        )

    def add_variable_update_rules(self, yaml_content):
        """添加 [mvu_update] 变量更新规则条目（at_depth D0）"""
        return self.add_worldbook_entry(
            comment="[mvu_update]变量更新规则",
            content=yaml_content,
            constant=True, position="at_depth", position_num=4,
            order=14720, depth=0,
        )

    def add_variable_output_format(self, content=None):
        """添加变量输出格式条目（@D depth=0）"""
        if content is None:
            content = (
                "---\n"
                "变量输出格式:\n"
                "  rule:\n"
                "    - 你必须在回复末尾输出更新分析和实际的更新命令\n"
                "    - 更新命令遵循JSON Patch (RFC 6902)标准\n"
                "    - 支持操作: replace/delta/insert/remove\n"
                "    - 不要更新以_开头的只读变量\n"
                "  format: |-\n"
                "    <UpdateVariable>\n"
                "    <Analysis>$(按英文输出，不超过80词)\n"
                "    - ${计算经过的时间: ...}\n"
                "    - ${判断是否允许戏剧性变化: 是/否}\n"
                "    - ${基于check分析每个变量: ...}\n"
                "    </Analysis>\n"
                "    <JSONPatch>\n"
                "    [\n"
                "      { \"op\": \"replace\", \"path\": \"${路径}\", \"value\": \"${新值}\" },\n"
                "      { \"op\": \"delta\", \"path\": \"${数值路径}\", \"value\": ${变动值} },\n"
                "      { \"op\": \"insert\", \"path\": \"${对象路径/新键}\", \"value\": \"${新值}\" },\n"
                "      { \"op\": \"remove\", \"path\": \"${对象路径/键}\" }\n"
                "    ]\n"
                "    </JSONPatch>\n"
                "    </UpdateVariable>"
            )
        return self.add_worldbook_entry(
            comment="[mvu_update]变量输出格式",
            content=content,
            constant=True, position="at_depth", position_num=4,
            order=14720, depth=0,
        )

    # === 正则脚本 ===
    def _ensure_regex_scripts(self):
        d = self.card["data"]["extensions"]
        if "regex_scripts" not in d:
            d["regex_scripts"] = []

    def add_regex_script(self, *, name, find_regex=None, find_pattern=None,
                         find_flags="gs", replace_string="",
                         markdown_only=True, prompt_only=False,
                         placement=None, min_depth=None, max_depth=None,
                         run_on_edit=False, substitute_regex=0):
        self._ensure_regex_scripts()
        if find_regex is None and find_pattern is not None:
            find_regex = build_find_regex(find_pattern, find_flags)
        if find_regex is None:
            find_regex = "//"
        if placement is None:
            placement = [2]
        script = {
            "id": gen_uuid(),
            "scriptName": name,
            "findRegex": find_regex,
            "replaceString": replace_string,
            "trimStrings": [],
            "placement": placement,
            "disabled": False,
            "markdownOnly": markdown_only,
            "promptOnly": prompt_only,
            "runOnEdit": run_on_edit,
            "substituteRegex": substitute_regex,
            "minDepth": min_depth,
            "maxDepth": max_depth,
        }
        self.card["data"]["extensions"]["regex_scripts"].append(script)
        return self

    def add_statusbar_regex(self, html_template, name="[界面]状态栏"):
        """添加状态栏美化正则（HTML由调用方提供）"""
        return self.add_regex_script(
            name=name,
            find_pattern="<StatusPlaceHolderImpl/>",
            replace_string=html_template,
            markdown_only=True, placement=[2],
            run_on_edit=True,
        )

    def add_statusbar_hide_regex(self):
        """添加状态栏隐藏正则（不发送给AI）"""
        return self.add_regex_script(
            name="[不发送]界面占位符",
            find_pattern="<StatusPlaceHolderImpl/>",
            replace_string="",
            markdown_only=False, prompt_only=True,
            placement=[2], run_on_edit=True,
        )

    def add_mvu_hide_regex(self, name="[不发送]去除变量更新", min_depth=4):
        """添加变量更新隐藏正则"""
        return self.add_regex_script(
            name=name,
            find_pattern="<UpdateVariable>(.*?)<\\/UpdateVariable>",
            find_flags="gis",
            replace_string="",
            markdown_only=False, prompt_only=True,
            placement=[1, 2], min_depth=min_depth,
        )

    def add_mvu_beautify_full_regex(self):
        """添加完整变量更新美化正则"""
        return self.add_regex_script(
            name="[美化]完整变量更新",
            find_pattern="<UpdateVariable>(.*?)<\\/UpdateVariable>",
            find_flags="gis",
            replace_string="<details><summary>变量更新完成</summary>\n$1\n</details>",
            markdown_only=True, placement=[2],
        )

    def add_mvu_beautify_partial_regex(self):
        """添加不完整变量更新提示正则"""
        return self.add_regex_script(
            name="[美化]变量更新中",
            find_pattern="<updatevariable>(?!.*<\\/updatevariable>)\\s*(.*)\\s*$",
            find_flags="gsi",
            replace_string="<details><summary>变量更新中...</summary>\n$1\n</details>",
            markdown_only=True, placement=[2],
        )

    # === 酒馆助手脚本 ===
    def _ensure_tavern_helper(self):
        d = self.card["data"]["extensions"]
        if "tavern_helper" not in d:
            d["tavern_helper"] = [["scripts", []], ["variables", {}]]
        return d["tavern_helper"]

    def add_tavern_script(self, *, name, content, enabled=True,
                          info="", buttons=None, data=None):
        th = self._ensure_tavern_helper()
        script = {
            "type": "script",
            "enabled": enabled,
            "name": name,
            "id": gen_uuid(),
            "content": content,
            "info": info,
            "button": {
                "enabled": True,
                "buttons": buttons or [],
            },
            "data": data or {},
        }
        th[0][1].append(script)
        return self

    def add_mvu_core_script(self, inline=False):
        """添加MVU核心脚本

        Args:
            inline: True 时使用内联模式（不依赖CDN）
        """
        content = INLINE_MVU_BUNDLE if inline else DEFAULT_MVU_BUNDLE
        return self.add_tavern_script(
            name="MVU" if not inline else "MVU(内联)",
            content=content,
            buttons=DEFAULT_MVU_BUTTONS,
        )

    def add_mvu_schema_script(self, schema_js, name="变量结构"):
        """添加MVU ZOD变量结构脚本"""
        return self.add_tavern_script(
            name=name,
            content=schema_js,
            buttons=[],
        )

    # === 输出 ===
    def build(self):
        """构建并返回完整的角色卡JSON dict"""
        self.card["create_date"] = now_iso()
        # 确保顶层字段镜像
        data = self.card["data"]
        self.card["name"] = data["name"]
        self.card["description"] = data["description"]
        self.card["first_mes"] = data["first_mes"]
        return self.card

    def to_json_string(self, indent=2, ensure_ascii=False):
        return json.dumps(self.build(), indent=indent, ensure_ascii=ensure_ascii)

    def save(self, filepath, indent=2):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.build(), f, indent=indent, ensure_ascii=False)
        return filepath


# ============================================================
# CardConfig: JSON配置文件加载
# ============================================================

class CardConfig:
    """从JSON配置文件加载角色卡定义并应用到CardBuilder"""

    def __init__(self, config_dict):
        self.cfg = config_dict

    @classmethod
    def from_file(cls, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return cls(json.load(f))

    def apply_to(self, builder: CardBuilder):
        """将配置应用到CardBuilder"""
        c = self.cfg
        if not isinstance(c, dict):
            raise ValueError("配置必须是一个JSON对象")

        # === 输入校验 ===
        card = c.get("card", {}) or {}
        if not card.get("name"):
            raise ValueError("缺少必填字段: card.name")
        if not card.get("first_mes") and not card.get("description"):
            raise ValueError("至少需要提供 card.first_mes（默认开场）或 card.description")

        # MVU 风格冲突检测
        mvu = c.get("mvu", {})
        if mvu.get("enabled"):
            schema = mvu.get("schema_script", "")
            has_zod_style = "registerMvuSchema" in schema
            has_beta_style = any(kw in schema for kw in ["_.add(", "_.set(", "getvar("])
            if has_zod_style and has_beta_style:
                raise ValueError(
                    "MVU 风格冲突：schema_script 同时包含 MVU zod（registerMvuSchema）"
                    "和 MVU beta（_.add/_.set/getvar）的代码。"
                    "两种风格不兼容，请统一为一种。"
                )

        # 配置校验警告
        warnings = []
        if mvu.get("enabled"):
            if not mvu.get("schema_script"):
                warnings.append("  ⚠ MVU 已启用但未提供 schema_script——变量结构将不完整")
            if not mvu.get("initvar"):
                warnings.append("  ⚠ MVU 已启用但未提供 initvar——变量初始值将为空")
            if not mvu.get("update_rules"):
                warnings.append("  ⚠ MVU 已启用但未提供 update_rules——AI 不知道如何更新变量")
        statusbar = c.get("statusbar", {})
        if statusbar.get("enabled") and not statusbar.get("html"):
            raise ValueError("statusbar.enabled=true 但未提供 statusbar.html")

        # 开场占位符检查
        first_mes = card.get("first_mes", "")
        if mvu.get("enabled") and first_mes and "<StatusPlaceHolderImpl/>" not in first_mes:
            warnings.append("  ⚠ MVU 已启用但默认开场缺少 <StatusPlaceHolderImpl/>——状态栏占位符不会渲染")
        for i, g in enumerate(card.get("alternate_greetings", [])):
            if mvu.get("enabled") and g and "<StatusPlaceHolderImpl/>" not in g:
                warnings.append(f"  ⚠ 开场 {i+2} 缺少 <StatusPlaceHolderImpl/>——状态栏占位符不会渲染")

        if warnings:
            print("\n[配置校验]" + "\n".join(warnings) + "\n")

        # === 基本信息 ===
        card = c.get("card", {})
        if card:
            builder.set_card_info(
                name=card.get("name"),
                description=card.get("description", ""),
                personality=card.get("personality", ""),
                scenario=card.get("scenario", ""),
                creator_notes=card.get("creator_notes", ""),
                system_prompt=card.get("system_prompt", ""),
                post_history_instructions=card.get("post_history_instructions", ""),
                creator=card.get("creator", ""),
                version=card.get("character_version", "1.0"),
            )

        # === 扩展 ===
        ext = c.get("extensions", {})
        if ext.get("talkativeness"):
            builder.set_talkativeness(ext["talkativeness"])

        # === 开场 ===
        if card.get("first_mes"):
            builder.set_first_message(card["first_mes"])
        for g in card.get("alternate_greetings", []):
            builder.add_alternate_greeting(g)

        # === 世界书 ===
        wb = c.get("worldbook", {})
        if wb.get("name"):
            builder.set_worldbook_name(wb["name"])
        for entry in wb.get("entries", []):
            builder.add_worldbook_entry(
                comment=entry.get("comment", ""),
                content=entry.get("content", ""),
                keys=parse_key_list(entry.get("keys", [])),
                secondary_keys=parse_key_list(entry.get("secondary_keys", [])),
                constant=entry.get("constant", True),
                position=entry.get("position", "after_char"),
                position_num=entry.get("extensions", {}).get("position",
                    _position_str_to_num(entry.get("position", "after_char"))),
                order=entry.get("order", entry.get("insertion_order", 100)),
                enabled=entry.get("enabled", True),
                depth=entry.get("extensions", {}).get("depth", 4),
            )

        # === 正则脚本 ===
        for rs in c.get("regex_scripts", []):
            builder.add_regex_script(
                name=rs.get("name", rs.get("scriptName", "")),
                find_regex=rs.get("findRegex"),
                replace_string=rs.get("replaceString", ""),
                markdown_only=rs.get("markdownOnly", True),
                prompt_only=rs.get("promptOnly", False),
                placement=rs.get("placement", [2]),
                min_depth=rs.get("minDepth"),
                max_depth=rs.get("maxDepth"),
                run_on_edit=rs.get("runOnEdit", False),
                substitute_regex=rs.get("substituteRegex", 0),
            )

        # === 酒馆助手脚本 ===
        th = c.get("tavern_helper", {})
        for script in th.get("scripts", []):
            builder.add_tavern_script(
                name=script.get("name", ""),
                content=script.get("content", ""),
                enabled=script.get("enabled", True),
                buttons=script.get("buttons", []),
            )

        # === MVU专用（快捷配置） ===
        mvu = c.get("mvu", {})
        if mvu.get("enabled"):
            if mvu.get("schema_script"):
                builder.add_mvu_schema_script(mvu["schema_script"])
            inline_cdn = mvu.get("inline_cdn", False)
            builder.add_mvu_core_script(inline=inline_cdn)
            if mvu.get("initvar"):
                builder.add_initvar_entry(mvu["initvar"])
            if mvu.get("variable_list_path") is not False:
                builder.add_variable_list_entry(
                    mvu.get("variable_list_path", "stat_data"))
            if mvu.get("update_rules"):
                builder.add_variable_update_rules(mvu["update_rules"])
            if mvu.get("output_format"):
                builder.add_variable_output_format(mvu["output_format"])
            else:
                builder.add_variable_output_format()
            if mvu.get("hide_regex", True):
                builder.add_mvu_hide_regex()
            if mvu.get("beautify_regex", True):
                builder.add_mvu_beautify_full_regex()
                builder.add_mvu_beautify_partial_regex()

        # === 状态栏 ===
        statusbar = c.get("statusbar", {})
        if statusbar.get("enabled"):
            html = statusbar.get("html", "")
            if not html:
                raise ValueError("statusbar.enabled=true 但未提供 statusbar.html")
            builder.add_statusbar_regex(html)
            if statusbar.get("hide_regex", True):
                builder.add_statusbar_hide_regex()

        # === 正则后处理：排序 + 校验 ===
        self._sort_and_validate_regex(builder)
        return builder

    def _sort_and_validate_regex(self, builder):
        """正则排序（状态栏先→全局后）+ 校验 /s flag + white-space"""
        regex_list = builder.card["data"]["extensions"].get("regex_scripts", [])
        if not regex_list:
            return

        # 1) 检测全局美化正则（匹配 <chat> 包裹的）
        global_indices = []
        statusbar_indices = []
        other_indices = []
        warns = []

        for i, rs in enumerate(regex_list):
            fr = rs.get("findRegex", "")
            # 全局美化：匹配 <chat>...</chat>
            if "<chat>" in fr and "<\\/chat>" in fr:
                global_indices.append(i)
                # 校验 /s flag
                if not fr.endswith("s"):
                    flags = fr.rsplit("/", 1)[-1] if fr.count("/") >= 2 else ""
                    if "s" not in flags and "S" not in flags:
                        warns.append(f"  ⚠ 正则「{rs.get('scriptName','')}」缺 /s flag（dotAll），换行符不匹配。已自动补上。")
                        parts = fr.rsplit("/", 1)
                        if len(parts) == 2:
                            rs["findRegex"] = parts[0] + "/" + parts[1] + "s"
            elif "StatusPlaceHolderImpl" in fr or "statusbar" in fr.lower():
                statusbar_indices.append(i)
            else:
                other_indices.append(i)

        # 2) 排序重组：状态栏 → 全局 → 其他
        sorted_list = (
            [regex_list[i] for i in statusbar_indices] +
            [regex_list[i] for i in global_indices] +
            [regex_list[i] for i in other_indices]
        )
        builder.card["data"]["extensions"]["regex_scripts"] = sorted_list

        if statusbar_indices and global_indices:
            # 验证排序是否真的把状态栏放前面了
            first_global_idx_in_sorted = None
            for i, rs in enumerate(sorted_list):
                if "<chat>" in rs.get("findRegex", "") and "<\\/chat>" in rs.get("findRegex", ""):
                    first_global_idx_in_sorted = i
                    break
            last_statusbar_idx_in_sorted = None
            for i in range(len(sorted_list) - 1, -1, -1):
                if "StatusPlaceHolderImpl" in sorted_list[i].get("findRegex", "") or "statusbar" in sorted_list[i].get("findRegex", "").lower():
                    last_statusbar_idx_in_sorted = i
                    break
            if first_global_idx_in_sorted is not None and last_statusbar_idx_in_sorted is not None:
                if first_global_idx_in_sorted < last_statusbar_idx_in_sorted:
                    warns.append("  ⚠ 状态栏正则和全局美化正则在同一条目内，排序无法保障。请检查正则配置。")

        # 3) 校验全局美化 HTML 模板是否含 white-space: pre-wrap
        for rs in sorted_list:
            replace = rs.get("replaceString", "")
            if "<chat>" in rs.get("findRegex", "") and "<\\/chat>" in rs.get("findRegex", "") and replace:
                if "white-space" not in replace:
                    # 如果 replaceString 中有 $1，检查外层 div 是否缺少 white-space
                    if "$1" in replace:
                        warns.append(f"  ⚠ 全局美化正则「{rs.get('scriptName','')}」的HTML模板缺少 white-space: pre-wrap——AI输出的换行会被浏览器塌缩。请在内层内容区 div 加上 style='white-space: pre-wrap'。")

        if warns:
            print("\n[正则校验]" + "\n".join(warns) + "\n")


# ============================================================
# CardConfig: JSON配置文件加载
# ============================================================

def _position_str_to_num(pos_str):
    """位置字符串转数字"""
    mapping = {"before_char": 0, "after_char": 1, "at_depth": 4}
    return mapping.get(pos_str, 1)
# InteractiveCLI: 交互式创建
# ============================================================

class InteractiveCLI:
    """命令行交互式角色卡创建"""

    def __init__(self):
        self.builder = CardBuilder()

    def _input(self, prompt, default=None):
        if default:
            val = input(f"{prompt} [{default}]: ").strip()
            return val if val else default
        return input(f"{prompt}: ").strip()

    def _input_yn(self, prompt, default="n"):
        val = input(f"{prompt} (y/n) [{default}]: ").strip().lower()
        if not val:
            val = default
        return val == "y" or val == "yes"

    def _input_multiline(self, prompt):
        print(f"{prompt} (输入空行结束):")
        lines = []
        while True:
            line = input()
            if line == "" and lines:
                break
            lines.append(line)
        return "\n".join(lines)

    def run(self):
        print("\n=== SillyTavern 角色卡生成器 (交互模式) ===\n")

        # 1. 角色名
        name = self._input("角色卡名称")
        self.builder.set_name(name)

        # 2. 作者
        creator = self._input("作者名", "")
        if creator:
            self.builder.set_card_info(creator=creator)

        # 3. 角色描述
        desc = self._input_multiline("角色描述 (YAML格式)")
        if desc:
            self.builder.set_card_info(description=desc)

        # 4. 人格
        personality = self._input("人格/性格简述 (可选)", "")
        if personality:
            self.builder.set_card_info(personality=personality)

        # 5. 世界书
        if self._input_yn("是否需要世界书"):
            wb_name = self._input("世界书名称", f"{name}_worldbook")
            self.builder.set_worldbook_name(wb_name)
            print("  (稍后可在JSON配置中批量添加条目)")

        # 6. MVU
        if self._input_yn("是否需要MVU ZOD变量系统"):
            print("  MVU复杂度: (1)简单好感度 (2)完整游戏系统")
            choice = self._input("  选择", "1")
            self._setup_mvu(choice)

        # 7. 美化
        if self._input_yn("是否需要HTML美化"):
            self._setup_beautify()

        # 8. 开场
        self._setup_openings()

        # 9. 保存
        out_name = self._input("输出文件名", f"{name}.json")
        if not out_name.endswith(".json"):
            out_name += ".json"
        self.builder.save(out_name)
        print(f"\n 角色卡已生成: {out_name}")

    def _setup_mvu(self, choice):
        # MVU核心脚本
        self.builder.add_mvu_core_script()

        if choice == "1":
            schema = (
                "import { registerMvuSchema } from "
                "'https://testingcf.jsdelivr.net/gh/StageDog/tavern_resource/dist/util/mvu_zod.js';\n\n"
                "export const Schema = z.object({\n"
                "  角色: z.object({\n"
                "    好感度: z.coerce.number().transform(v => _.clamp(v, 0, 100)).prefault(20),\n"
                "    心情: z.string().prefault('平静'),\n"
                "  }),\n"
                "});\n\n"
                "$(() => { registerMvuSchema(Schema); });"
            )
            self.builder.add_mvu_schema_script(schema)
            self.builder.add_initvar_entry(
                "角色:\n  好感度: 20\n  心情: 平静\n")
            self.builder.add_variable_list_entry()
            self.builder.add_variable_update_rules(
                "---\n变量更新规则:\n  角色:\n    好感度:\n      type: number\n      range: 0~100\n      check:\n        - 根据互动调整 ±(3~6)\n    心情:\n      check:\n        - 根据剧情氛围更新\n")
            self.builder.add_variable_output_format()
        else:
            # 完整游戏系统提供框架，用户自行填充
            print("  (完整游戏系统的Schema请自行编辑JSON配置文件)")

        self.builder.add_mvu_hide_regex()
        self.builder.add_mvu_beautify_full_regex()
        self.builder.add_mvu_beautify_partial_regex()

    def _setup_beautify(self):
        # 交互模式：用纯文本显示变量值。HTML美化请通过JSON配置提供。
        html = ("<style>body{margin:0;padding:8px;background:transparent;font-family:sans-serif;"
                "display:flex;justify-content:center;color:#ccc;font-size:13px}"
                ".s{background:rgba(26,26,46,.7);border-radius:10px;padding:10px 14px;"
                "border:1px solid rgba(255,182,193,.15)}"
                ".r{display:flex;justify-content:space-between;padding:3px 0}</style>"
                "<div class='s'>"
                "<div class='r'><span>好感度</span><span>"
                "{{" + "format_message_variable::stat_data.角色.好感度" + "}}</span></div>"
                "<div class='r'><span>心情</span><span>"
                "{{" + "format_message_variable::stat_data.角色.心情" + "}}</span></div>"
                "</div>")
        self.builder.add_statusbar_regex(html)
        self.builder.add_statusbar_hide_regex()

    def _setup_openings(self):
        n = int(self._input("开场数量 (1-5)", "3"))
        default_opening = (
            f"【2026年】【清晨】\n\n"
            f"新的一天开始了。\n\n"
            f"<StatusPlaceHolderImpl/>"
        )
        opening = self._input_multiline("默认开场（可稍后在JSON中编辑）")
        self.builder.set_first_message(opening if opening else default_opening)

        for i in range(n):
            print(f"\n  开场 {i+2}:")
            text = self._input_multiline(f"  内容 (或按回车跳过)")
            if text:
                text += "\n<StatusPlaceHolderImpl/>"
                self.builder.add_alternate_greeting(text)


# ============================================================
# 提取模式：从现有角色卡提取配置模板
# ============================================================

def extract_template(card_path, output_path):
    """从现有角色卡JSON提取为可编辑的配置模板"""
    with open(card_path, "r", encoding="utf-8") as f:
        card = json.load(f)

    data = card.get("data", {})
    ext = data.get("extensions", {})
    wb = data.get("character_book", {})

    template = {
        "card": {
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "personality": data.get("personality", ""),
            "scenario": data.get("scenario", ""),
            "first_mes": data.get("first_mes", ""),
            "creator_notes": data.get("creator_notes", ""),
            "system_prompt": data.get("system_prompt", ""),
            "creator": data.get("creator", ""),
            "character_version": data.get("character_version", "1.0"),
            "alternate_greetings": data.get("alternate_greetings", []),
        },
        "extensions": {
            "talkativeness": ext.get("talkativeness", "0.5"),
            "world": ext.get("world", ""),
        },
        "worldbook": {
            "name": wb.get("name", ""),
            "entries": [
                {
                    "comment": e.get("comment", ""),
                    "keys": e.get("keys", []),
                    "content": e.get("content", ""),
                    "constant": e.get("constant", True),
                    "position": e.get("position", "after_char"),
                    "order": e.get("insertion_order", 100),
                    "enabled": e.get("enabled", True),
                }
                for e in wb.get("entries", [])
            ],
        },
        "regex_scripts": [],
        "tavern_helper": {"scripts": []},
        "mvu": {"enabled": False},
    }

    # 正则脚本
    for rs in ext.get("regex_scripts", []):
        template["regex_scripts"].append({
            "name": rs.get("scriptName", ""),
            "findRegex": rs.get("findRegex", ""),
            "replaceString": rs.get("replaceString", ""),
            "markdownOnly": rs.get("markdownOnly", True),
            "promptOnly": rs.get("promptOnly", False),
            "placement": rs.get("placement", [2]),
            "minDepth": rs.get("minDepth"),
            "runOnEdit": rs.get("runOnEdit", False),
        })

    # 酒馆助手
    th = ext.get("tavern_helper", [])
    if isinstance(th, list) and len(th) > 0 and isinstance(th[0], list) and len(th[0]) > 1:
        for s in th[0][1]:
            template["tavern_helper"]["scripts"].append({
                "name": s.get("name", ""),
                "content": s.get("content", ""),
            })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
    return output_path


# ============================================================
# 验证模式
# ============================================================

def validate_card(card_path):
    """验证角色卡JSON的合法性"""
    errors = []
    warnings = []

    try:
        with open(card_path, "r", encoding="utf-8") as f:
            card = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        return [f"无法读取文件: {e}"], []

    # 基础结构检查
    if "spec" not in card:
        errors.append("缺少 spec 字段")
    if card.get("spec") != "chara_card_v3":
        warnings.append(f"spec 不是 chara_card_v3: {card.get('spec')}")
    if "data" not in card:
        errors.append("缺少 data 对象")

    data = card.get("data", {})
    if "name" not in data:
        errors.append("缺少 data.name")
    if "extensions" not in data:
        errors.append("缺少 data.extensions")

    # 检查世界书条目
    wb = data.get("character_book", {})
    entries = wb.get("entries", [])
    for i, e in enumerate(entries):
        if "content" not in e:
            errors.append(f"世界书条目 {i} 缺少 content")
        ext = e.get("extensions", {})
        if not ext.get("prevent_recursion"):
            warnings.append(f"世界书条目 {i} ({e.get('comment','')}) prevent_recursion=false")
        if not ext.get("exclude_recursion"):
            warnings.append(f"世界书条目 {i} ({e.get('comment','')}) exclude_recursion=false")

    ext = data.get("extensions", {})
    for i, rs in enumerate(ext.get("regex_scripts", [])):
        if not rs.get("findRegex"):
            warnings.append(f"正则 {i} ({rs.get('scriptName','')}) findRegex为空")

    return errors, warnings


# ============================================================
# Decompile: 从角色卡解包为配置JSON
# ============================================================

def _detect_mvu_config(card):
    """从角色卡JSON检测MVU配置"""
    data = card.get("data", {})
    wb = data.get("character_book", {})
    ext = data.get("extensions", {})
    th = ext.get("tavern_helper", [])

    mvu = {"enabled": False}

    scripts_list = []
    if isinstance(th, list) and len(th) > 0 and isinstance(th[0], list) and len(th[0]) > 1:
        scripts_list = th[0][1]
    elif isinstance(th, dict):
        scripts_list = th.get("scripts", [])

    for s in scripts_list:
        content = s.get("content", "")
        if "bundle.js" in content and ("MagVarUpdate" in content):
            mvu["enabled"] = True
    if not mvu.get("enabled"):
        return mvu

    for s in scripts_list:
        content = s.get("content", "")
        if "registerMvuSchema" in content:
            mvu["schema_script"] = content
            break

    entries = wb.get("entries", [])
    for e in entries:
        comment = e.get("comment", "")
        content = e.get("content", "")
        if "[initvar]" in comment:
            inner = content
            if inner.strip().startswith("<initvar>"):
                inner = inner[inner.index("<initvar>") + len("<initvar>"):]
            if inner.strip().endswith("</initvar>"):
                inner = inner[:inner.rindex("</initvar>")]
            mvu["initvar"] = inner.strip()
        if "变量列表" in comment or ("format_message_variable" in content and "status_current_variable" in content):
            mvu["variable_list_path"] = "stat_data"
        if "[mvu_update]" in comment and ("规则" in comment or "rule" in comment.lower()):
            mvu["update_rules"] = content
        if "[mvu_update]" in comment and ("格式" in comment or "format" in comment.lower()):
            mvu["output_format"] = content

    mvu["hide_regex"] = False
    mvu["beautify_regex"] = False
    for rs in ext.get("regex_scripts", []):
        fr = rs.get("findRegex", "").lower()
        if "updatevariable" in fr:
            if rs.get("promptOnly") and rs.get("replaceString", "") == "":
                mvu["hide_regex"] = True
            if rs.get("markdownOnly") and "details" in rs.get("replaceString", ""):
                mvu["beautify_regex"] = True

    return mvu


def _detect_statusbar_config(card):
    """从角色卡JSON检测状态栏配置"""
    ext = card.get("data", {}).get("extensions", {})
    statusbar = {"enabled": False}

    for rs in ext.get("regex_scripts", []):
        fr = rs.get("findRegex", "")
        replace = rs.get("replaceString", "")
        if "StatusPlaceHolderImpl" in fr:
            if replace and not rs.get("promptOnly"):
                statusbar["enabled"] = True
                statusbar["html"] = replace
            if not replace and rs.get("promptOnly"):
                statusbar["hide_regex"] = True

    return statusbar


def decompile_card(card_path, output_path):
    """从角色卡JSON解包为完整的可编辑配置JSON（与--config输入格式兼容）"""
    with open(card_path, "r", encoding="utf-8") as f:
        card = json.load(f)

    data = card.get("data", {})
    ext = data.get("extensions", {})
    wb = data.get("character_book", {})

    template = {
        "card": {
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "personality": data.get("personality", ""),
            "scenario": data.get("scenario", ""),
            "first_mes": data.get("first_mes", ""),
            "creator_notes": data.get("creator_notes", ""),
            "system_prompt": data.get("system_prompt", ""),
            "post_history_instructions": data.get("post_history_instructions", ""),
            "creator": data.get("creator", ""),
            "character_version": data.get("character_version", "1.0"),
            "alternate_greetings": data.get("alternate_greetings", []),
        },
        "extensions": {
            "talkativeness": ext.get("talkativeness", "0.5"),
            "world": ext.get("world", ""),
        },
        "worldbook": {
            "name": wb.get("name", ""),
            "entries": [],
        },
        "regex_scripts": [],
        "tavern_helper": {"scripts": []},
        "mvu": _detect_mvu_config(card),
        "statusbar": _detect_statusbar_config(card),
    }

    mvu_enabled = template["mvu"].get("enabled", False)

    def _is_mvu_entry(comment, content):
        if "[initvar]" in comment:
            return True
        if "变量列表" in comment or ("format_message_variable" in content and "status_current_variable" in content):
            return True
        if "[mvu_update]" in comment and ("规则" in comment or "rule" in comment.lower()):
            return True
        if "[mvu_update]" in comment and ("格式" in comment or "format" in comment.lower()):
            return True
        return False

    for e in wb.get("entries", []):
        entry_comment = e.get("comment", "")
        entry_content = e.get("content", "")
        if mvu_enabled and _is_mvu_entry(entry_comment, entry_content):
            continue
        entry_ext = e.get("extensions", {})
        template["worldbook"]["entries"].append({
            "comment": entry_comment,
            "keys": e.get("keys", []),
            "secondary_keys": e.get("secondary_keys", []),
            "content": entry_content,
            "constant": e.get("constant", True),
            "position": e.get("position", "after_char"),
            "order": e.get("insertion_order", 100),
            "enabled": e.get("enabled", True),
            "depth": entry_ext.get("depth", 4),
            "prevent_recursion": entry_ext.get("prevent_recursion", True),
            "exclude_recursion": entry_ext.get("exclude_recursion", True),
        })

    for rs in ext.get("regex_scripts", []):
        template["regex_scripts"].append({
            "name": rs.get("scriptName", ""),
            "findRegex": rs.get("findRegex", ""),
            "replaceString": rs.get("replaceString", ""),
            "markdownOnly": rs.get("markdownOnly", True),
            "promptOnly": rs.get("promptOnly", False),
            "placement": rs.get("placement", [2]),
            "minDepth": rs.get("minDepth"),
            "maxDepth": rs.get("maxDepth"),
            "runOnEdit": rs.get("runOnEdit", False),
            "substituteRegex": rs.get("substituteRegex", 0),
        })

    th = ext.get("tavern_helper", [])
    scripts_list = []
    if isinstance(th, list) and len(th) > 0 and isinstance(th[0], list) and len(th[0]) > 1:
        scripts_list = th[0][1]
    elif isinstance(th, dict):
        scripts_list = th.get("scripts", [])

    for s in scripts_list:
        buttons = []
        btn_cfg = s.get("button", {})
        for b in btn_cfg.get("buttons", []):
            buttons.append({"name": b.get("name", ""), "visible": b.get("visible", True)})
        template["tavern_helper"]["scripts"].append({
            "name": s.get("name", ""),
            "content": s.get("content", ""),
            "enabled": s.get("enabled", True),
            "buttons": buttons,
        })

    # 清理：MVU/Statusbar的脚本和正则已在专用节中，从通用列表中排除
    if template["mvu"].get("enabled"):
        mvu_bundle_patterns = ["bundle.js", "MagVarUpdate"]
        mvu_schema_pattern = "registerMvuSchema"
        template["tavern_helper"]["scripts"] = [
            s for s in template["tavern_helper"]["scripts"]
            if not any(p in s["content"] for p in mvu_bundle_patterns) and mvu_schema_pattern not in s["content"]
        ]
        template["regex_scripts"] = [
            r for r in template["regex_scripts"]
            if "updatevariable" not in r.get("findRegex", "").lower()
        ]

    if template["statusbar"].get("enabled"):
        template["regex_scripts"] = [
            r for r in template["regex_scripts"]
            if "StatusPlaceHolderImpl" not in r.get("findRegex", "")
        ]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
    return output_path


# ============================================================
# Edit: 原位编辑角色卡
# ============================================================

def edit_card(card_path, *, name=None, description=None, personality=None,
              scenario=None, first_mes=None, creator_notes=None, creator=None,
              talkativeness=None, add_greeting=None, enable_mvu=None,
              enable_statusbar=None):
    """原位编辑角色卡JSON文件的字段"""
    with open(card_path, "r", encoding="utf-8") as f:
        card = json.load(f)

    data = card.get("data", {})
    ext = data.get("extensions", {})

    top_fields = {
        "name": name, "description": description,
        "personality": personality, "scenario": scenario,
        "first_mes": first_mes,
    }
    for k, v in top_fields.items():
        if v is not None:
            card[k] = v
            if k in data:
                data[k] = v

    if creator_notes is not None:
        data["creator_notes"] = creator_notes
    if creator is not None:
        data["creator"] = creator
    if talkativeness is not None:
        card["talkativeness"] = str(talkativeness)
        ext["talkativeness"] = str(talkativeness)

    if add_greeting is not None:
        if "alternate_greetings" not in data:
            data["alternate_greetings"] = []
        data["alternate_greetings"].append(add_greeting)

    if enable_mvu is not None:
        builder = CardBuilder()
        if enable_mvu:
            builder.card = card
            builder.add_mvu_core_script()
            scheme_type = input("MVU复杂度 (1=简单好感度 2=完整游戏系统) [1]: ").strip() or "1"
            if scheme_type == "1":
                schema_js = (
                    "import { registerMvuSchema } from "
                    "'https://testingcf.jsdelivr.net/gh/StageDog/tavern_resource/dist/util/mvu_zod.js';\n\n"
                    "export const Schema = z.object({\n"
                    "  角色: z.object({\n"
                    "    好感度: z.coerce.number().transform(v => _.clamp(v, 0, 100)).prefault(20),\n"
                    "    心情: z.string().prefault('平静'),\n"
                    "  }),\n"
                    "});\n\n"
                    "$(() => { registerMvuSchema(Schema); });"
                )
                builder.add_mvu_schema_script(schema_js)
                builder.add_initvar_entry("角色:\n  好感度: 20\n  心情: 平静\n")
                builder.add_variable_list_entry()
                builder.add_variable_update_rules(
                    "---\n变量更新规则:\n  角色:\n    好感度:\n      type: number\n      range: 0~100\n      check:\n        - 根据互动调整 ±(3~6)\n    心情:\n      check:\n        - 根据剧情氛围更新\n")
                builder.add_variable_output_format()
            builder.add_mvu_hide_regex()
            builder.add_mvu_beautify_full_regex()
            builder.add_mvu_beautify_partial_regex()
        card = builder.build()

    if enable_statusbar is not None:
        builder = CardBuilder()
        builder.card = card
        if enable_statusbar:
            name_val = data.get("name", "角色")
            html = (
                "<style>body{margin:0;padding:8px;background:transparent;font-family:'Noto Sans SC',sans-serif;"
                "display:flex;justify-content:center;color:#e0e0e0;font-size:13px}"
                ".s{background:linear-gradient(145deg,#1a1a2e,#16213e);border-radius:12px;padding:12px 16px;"
                "box-shadow:0 4px 20px rgba(0,0,0,.3);backdrop-filter:blur(10px);min-width:280px}"
                ".r{display:flex;justify-content:space-between;align-items:center;padding:5px 0;"
                "border-bottom:1px solid rgba(255,255,255,.06)}"
                ".bar{flex:1;height:5px;background:rgba(255,255,255,.1);border-radius:3px;margin:0 10px;overflow:hidden}"
                ".fill{height:100%;background:linear-gradient(90deg,#ff6b9d,#c44dff);border-radius:3px;"
                "transition:width .5s ease}</style>"
                f"<div class='s'>"
                f"<div class='r'><span>好感度</span><div class='bar'><div class='fill' style='width:{{{{format_message_variable::stat_data.{name_val}.好感度}}}}%'></div></div>"
                f"<span>{{{{format_message_variable::stat_data.{name_val}.好感度}}}}/100</span></div>"
                f"<div class='r'><span>心情</span><span>{{{{format_message_variable::stat_data.{name_val}.心情}}}}</span></div>"
                f"</div>"
            )
            builder.add_statusbar_regex(html)
            builder.add_statusbar_hide_regex()
        card = builder.build()

    card["create_date"] = now_iso()
    with open(card_path, "w", encoding="utf-8") as f:
        json.dump(card, f, indent=2, ensure_ascii=False)
    return card_path


# ============================================================
# List: 角色卡概要
# ============================================================

def list_card(card_path):
    """列出角色卡的关键信息概要"""
    with open(card_path, "r", encoding="utf-8") as f:
        card = json.load(f)

    data = card.get("data", {})
    ext = data.get("extensions", {})
    wb = data.get("character_book", {})

    print(f"角色卡: {os.path.abspath(card_path)}")
    print(f"  名称: {data.get('name', '')}")
    print(f"  版本: {data.get('character_version', '')}")
    print(f"  作者: {data.get('creator', '')}")
    print(f"  描述长度: {len(data.get('description', ''))} chars")
    print(f"  默认开场长度: {len(data.get('first_mes', ''))} chars")
    print(f"  可选开场: {len(data.get('alternate_greetings', []))} 个")
    print(f"  世界名: {ext.get('world', '')}")
    print()

    entries = wb.get("entries", [])
    print(f"  世界书: {wb.get('name', '')} (共 {len(entries)} 条)")
    for i, e in enumerate(entries):
        pos_map = {"before_char": "↑Char", "after_char": "↓Char", "at_depth": "@D"}
        pos_label = pos_map.get(e.get("position", ""), e.get("position", "?"))
        light = "蓝灯" if e.get("constant") else "绿灯"
        status = "禁用" if not e.get("enabled", True) else "启用"
        entry_ext = e.get("extensions", {})
        print(f"    [{i}] {e.get('comment', '')[:50]} | pos={pos_label} | {light} | {status} | "
              f"preventRec={entry_ext.get('prevent_recursion', False)} | "
              f"excludeRec={entry_ext.get('exclude_recursion', False)}")

    regex_scripts = ext.get("regex_scripts", [])
    print(f"\n  正则脚本: {len(regex_scripts)} 个")
    for i, rs in enumerate(regex_scripts):
        md = "美化" if rs.get("markdownOnly") else ""
        pt = "隐藏" if rs.get("promptOnly") else ""
        tags = "/".join(filter(None, [md, pt])) or "通用"
        print(f"    [{i}] {rs.get('scriptName', '')[:40]} | {tags} | placement={rs.get('placement')}")

    th = ext.get("tavern_helper", [])
    scripts_list = []
    if isinstance(th, list) and len(th) > 0 and isinstance(th[0], list) and len(th[0]) > 1:
        scripts_list = th[0][1]
    elif isinstance(th, dict):
        scripts_list = th.get("scripts", [])
    print(f"\n  酒馆助手脚本: {len(scripts_list)} 个")
    for i, s in enumerate(scripts_list):
        print(f"    [{i}] {s.get('name', '')[:30]} | enabled={s.get('enabled', True)}")

    errors, warnings = validate_card(card_path)
    if errors:
        print(f"\n  验证错误: {len(errors)} 个")
        for e in errors:
            print(f"    [ERROR] {e}")
    if warnings:
        print(f"  验证警告: {len(warnings)} 个")
        for w in warnings:
            print(f"    [WARN] {w}")
    if not errors and not warnings:
        print(f"\n  验证: [OK]")


# ============================================================
# CLI入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="SillyTavern chara_card_v3 角色卡生成器 — 支持创建/解包/编辑/验证",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 从配置生成
  python card-generator.py --config config.json --output card.json

  # 交互式创建
  python card-generator.py --interactive

  # 解包角色卡为可编辑配置（含MVU/状态栏检测）
  python card-generator.py --decompile card.json -o template.json

  # 查看角色卡概要
  python card-generator.py --list card.json

  # 原位编辑角色卡字段
  python card-generator.py card.json --edit --name "新名字" --description "新描述"

  # 验证角色卡
  python card-generator.py --validate card.json

  # 提取简单模板（兼容旧参数）
  python card-generator.py --extract existing.json -o template.json
        """
    )

    parser.add_argument("card_path", nargs="?", help="角色卡JSON文件路径（编辑/列表模式用）")
    parser.add_argument("--config", "-c", help="JSON配置文件路径")
    parser.add_argument("--output", "-o", help="输出JSON文件路径", default="output.json")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互式创建")
    parser.add_argument("--extract", "-e", help="从现有角色卡提取简单配置模板")
    parser.add_argument("--decompile", "-d", help="从角色卡解包为完整可编辑配置（含MVU/状态栏检测）")
    parser.add_argument("--validate", "-v", help="验证角色卡JSON")
    parser.add_argument("--list", "-l", action="store_true", help="列出角色卡概要")

    # 编辑模式参数
    parser.add_argument("--edit", action="store_true", help="原位编辑角色卡字段")
    parser.add_argument("--name", help="角色卡名称")
    parser.add_argument("--description", help="角色描述")
    parser.add_argument("--personality", help="人格/性格")
    parser.add_argument("--scenario", help="场景设定")
    parser.add_argument("--first-mes", dest="first_mes", help="默认开场消息")
    parser.add_argument("--creator-notes", dest="creator_notes", help="作者备注")
    parser.add_argument("--creator", help="作者名")
    parser.add_argument("--talkativeness", help="话痨度（如 0.5）")
    parser.add_argument("--add-greeting", dest="add_greeting", help="追加一条可选开场")
    parser.add_argument("--enable-mvu", dest="enable_mvu", type=lambda x: x.lower() in ("true", "1", "yes"),
                        help="启用/禁用MVU变量系统 (true/false)")
    parser.add_argument("--enable-statusbar", dest="enable_statusbar", type=lambda x: x.lower() in ("true", "1", "yes"),
                        help="添加/移除状态栏美化 (true/false)")

    args = parser.parse_args()

    # --list
    if args.list:
        if not args.card_path:
            print("错误: --list 需要指定角色卡路径", file=sys.stderr)
            sys.exit(1)
        list_card(args.card_path)
        return

    # --edit
    if args.edit:
        if not args.card_path:
            print("错误: --edit 需要指定角色卡路径", file=sys.stderr)
            sys.exit(1)
        print(f"编辑角色卡: {args.card_path}")
        edit_card(
            args.card_path,
            name=args.name,
            description=args.description,
            personality=args.personality,
            scenario=args.scenario,
            first_mes=args.first_mes,
            creator_notes=args.creator_notes,
            creator=args.creator,
            talkativeness=args.talkativeness,
            add_greeting=args.add_greeting,
            enable_mvu=args.enable_mvu,
            enable_statusbar=args.enable_statusbar,
        )
        print("编辑完成")
        if args.list:
            list_card(args.card_path)
        return

    # --decompile
    if args.decompile:
        out = args.output if args.output != "output.json" else args.decompile.replace(".json", "_config.json")
        path = decompile_card(args.decompile, out)
        print(f"配置已解包到: {path}")
        return

    # --extract (兼容旧参数，简单提取)
    if args.extract:
        out = args.output if args.output != "output.json" else args.extract.replace(".json", "_template.json")
        path = extract_template(args.extract, out)
        print(f"模板已提取到: {path}")
        return

    # --validate
    if args.validate:
        errors, warnings = validate_card(args.validate)
        if errors:
            print("错误:")
            for e in errors:
                print(f"  [ERROR] {e}")
        if warnings:
            print("警告:")
            for w in warnings:
                print(f"  [WARN] {w}")
        if not errors and not warnings:
            print("验证通过 [OK]")
        return 1 if errors else 0

    # --interactive
    if args.interactive:
        cli = InteractiveCLI()
        cli.run()
        return

    # --config
    if args.config:
        config = CardConfig.from_file(args.config)
        builder = CardBuilder()
        config.apply_to(builder)
        builder.save(args.output)
        print(f"角色卡已生成: {args.output}")
        return

    parser.print_help()


if __name__ == "__main__":
    sys.exit(main() or 0)
