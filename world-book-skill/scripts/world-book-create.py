#!/usr/bin/env python3
"""
SillyTavern 世界书 (World Book) 命令行管理工具
支持创建、编辑、删除、列出条目，输出可导入 SillyTavern 的 JSON 文件。
"""

import argparse
import json
import os
import sys
import re

POSITION_LABELS = {
    0: "↑Char",
    1: "↓Char",
    2: "↑AT",
    3: "↓AT",
    4: "@D",
    5: "↑EM",
    6: "↓EM",
    7: "Outlet",
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_existing(path):
    """加载已有世界书，自动处理有/无 name 顶层字段"""
    if os.path.exists(path):
        book = load_json(path)
        entries = book.get("entries", {})
        name = book.get("name", None)
        return book, entries, name
    return None, {}, None


def get_next_uid(entries):
    """获取下一个可用 UID"""
    if not entries:
        return 0
    existing = [int(k) for k in entries.keys()]
    return max(existing) + 1


def get_next_order(entries):
    """获取下一个 order 值"""
    if not entries:
        return 100
    orders = [e.get("order", 0) for e in entries.values()]
    return max(orders) + 100 if orders else 100


def get_next_display_index(entries):
    """获取下一个 displayIndex"""
    if not entries:
        return 0
    indices = [e.get("displayIndex", 0) for e in entries.values()]
    return max(indices) + 1


def read_content(value):
    """读取内容：如果是 @filepath 则从文件读取，否则直接返回字符串"""
    if value.startswith("@"):
        filepath = value[1:]
        if not os.path.exists(filepath):
            print(f"错误: 文件不存在 - {filepath}", file=sys.stderr)
            sys.exit(1)
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    return value


def parse_key_list(value):
    """解析逗号分隔或数组格式的 key 列表"""
    if not value:
        return []
    if isinstance(value, list):
        return [str(k).strip() for k in value if k and str(k).strip()]
    return [k.strip() for k in value.split(",") if k.strip()]


class _Args:
    """把 dict 伪装成 argparse.Namespace，让 build_entry 同时兼容 CLI 和 batch"""
    _camel_to_snake = staticmethod(lambda s: ''.join(['_' + c.lower() if c.isupper() else c for c in s]).lstrip('_'))

    def __init__(self, d):
        normalized = {}
        for k, v in d.items():
            normalized[self._camel_to_snake(k)] = v
        self.__dict__.update(normalized)
    def __getattr__(self, name):
        return None


def build_entry(args, uid=None, display_index=None, existing_entry=None):
    """根据参数构建一个条目。args 可以是 argparse.Namespace 或 _Args(dict)"""
    if isinstance(args, dict):
        args = _Args(args)
    if existing_entry:
        entry = dict(existing_entry)
    else:
        entry = {
            "uid": uid,
            "key": [],
            "keysecondary": [],
            "comment": "",
            "content": "",
            "constant": False,
            "vectorized": False,
            "selective": False,
            "selectiveLogic": 0,
            "addMemo": True,
            "order": get_next_order({}),
            "position": 0,
            "disable": False,
            "ignoreBudget": False,
            "excludeRecursion": False,
            "preventRecursion": False,
            "matchPersonaDescription": False,
            "matchCharacterDescription": False,
            "matchCharacterPersonality": False,
            "matchCharacterDepthPrompt": False,
            "matchScenario": False,
            "matchCreatorNotes": False,
            "delayUntilRecursion": False,
            "probability": 100,
            "useProbability": True,
            "depth": 1,
            "outletName": "",
            "group": "",
            "groupOverride": False,
            "groupWeight": 100,
            "scanDepth": None,
            "caseSensitive": None,
            "matchWholeWords": None,
            "useGroupScoring": False,
            "automationId": "",
            "role": 0,
            "sticky": 0,
            "cooldown": 0,
            "delay": 0,
            "triggers": [],
            "displayIndex": display_index if display_index is not None else 0,
            "extensions": {},
            "characterFilter": {"isExclude": False, "names": [], "tags": []},
        }

    # ---------- 逐字段更新 ----------
    if args.comment is not None:
        entry["comment"] = args.comment
    if args.content is not None:
        entry["content"] = read_content(args.content)
    if args.keys is not None:
        entry["key"] = parse_key_list(args.keys)
    if args.keys2 is not None:
        entry["keysecondary"] = parse_key_list(args.keys2)
    if args.depth is not None:
        entry["depth"] = args.depth
    if args.constant:
        entry["constant"] = True
    if args.no_constant:
        entry["constant"] = False
    if args.order is not None:
        entry["order"] = args.order
    if args.position is not None:
        entry["position"] = args.position
    if args.outlet_name is not None:
        entry["outletName"] = args.outlet_name
    if args.disable:
        entry["disable"] = True
    if args.enable:
        entry["disable"] = False
    if args.selective:
        entry["selective"] = True
    if args.no_selective:
        entry["selective"] = False
    if args.selective_logic is not None:
        entry["selectiveLogic"] = args.selective_logic
    if args.probability is not None:
        entry["probability"] = args.probability
        entry["useProbability"] = True
    if args.add_memo is not None:
        entry["addMemo"] = args.add_memo
    if args.group is not None:
        entry["group"] = args.group
    if args.group_weight is not None:
        entry["groupWeight"] = args.group_weight
    if args.group_override:
        entry["groupOverride"] = True
    if args.role is not None:
        entry["role"] = args.role
    if args.prevent_recursion:
        entry["preventRecursion"] = True
    if args.exclude_recursion:
        entry["excludeRecursion"] = True
    if args.scan_depth is not None:
        entry["scanDepth"] = args.scan_depth
    if args.case_sensitive is not None:
        entry["caseSensitive"] = args.case_sensitive
    if args.match_whole_words is not None:
        entry["matchWholeWords"] = args.match_whole_words
    if args.use_group_scoring:
        entry["useGroupScoring"] = True
    if args.sticky is not None:
        entry["sticky"] = args.sticky
    if args.cooldown is not None:
        entry["cooldown"] = args.cooldown
    if args.delay is not None:
        entry["delay"] = args.delay

    # ---------- 构造 extensions 镜像 ----------
    entry["extensions"] = {
        "position": entry["position"],
        "exclude_recursion": entry["excludeRecursion"],
        "display_index": entry["displayIndex"],
        "probability": entry["probability"],
        "useProbability": entry["useProbability"],
        "depth": entry["depth"],
        "selectiveLogic": entry["selectiveLogic"],
        "outlet_name": entry["outletName"],
        "group": entry["group"],
        "group_override": entry["groupOverride"],
        "group_weight": entry["groupWeight"],
        "prevent_recursion": entry["preventRecursion"],
        "delay_until_recursion": entry["delayUntilRecursion"],
        "scan_depth": entry["scanDepth"],
        "match_whole_words": entry["matchWholeWords"],
        "use_group_scoring": entry["useGroupScoring"],
        "case_sensitive": entry["caseSensitive"],
        "automation_id": entry["automationId"],
        "role": entry["role"],
        "vectorized": entry["vectorized"],
        "sticky": entry["sticky"],
        "cooldown": entry["cooldown"],
        "delay": entry["delay"],
        "match_persona_description": entry["matchPersonaDescription"],
        "match_character_description": entry["matchCharacterDescription"],
        "match_character_personality": entry["matchCharacterPersonality"],
        "match_character_depth_prompt": entry["matchCharacterDepthPrompt"],
        "match_scenario": entry["matchScenario"],
        "match_creator_notes": entry["matchCreatorNotes"],
        "triggers": entry["triggers"],
        "ignore_budget": entry["ignoreBudget"],
    }

    return entry


# ============== 主入口 ==============

def main():
    parser = argparse.ArgumentParser(
        description="SillyTavern 世界书管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 新建世界书，添加条目
  python world-book-create.py my_book.json -n --name "我的世界书" --add \\
    --comment "规则1" --content "这里写条目内容" --keys 触发词1,触发词2 --depth 2 \\
    --prevent-recursion --exclude-recursion

  # 从文件读取条目内容
  python world-book-create.py my_book.json -n --add \\
    --comment "长篇设定" --content @设定.txt --keys 战斗 --constant \\
    --prevent-recursion --exclude-recursion

  # 在已有世界书上追加条目
  python world-book-create.py existing_book.json --add \\
    --comment "新条目" --content "新内容" --keys 关键词 --depth 3 \\
    --prevent-recursion --exclude-recursion

  # 编辑已有条目 (按 UID)
  python world-book-create.py existing_book.json --edit 3 \\
    --content "修改后的内容" --depth 4

  # 删除条目
  python world-book-create.py existing_book.json --delete 3

  # 列出所有条目
  python world-book-create.py existing_book.json --list

  # 批量操作: 从 JSON 文件批量创建条目
  python world-book-create.py existing_book.json --batch entries.json

  # 批量编辑: 从 JSON 文件批量修改已有条目 (每个对象必须含 uid)
  python world-book-create.py existing_book.json --batch-edit edits.json
        """,
    )

    # ---- 文件与模式参数 ----
    parser.add_argument("output", help="世界书 JSON 文件路径")
    parser.add_argument("-n", "--new", action="store_true",
                        help="强制新建世界书（即使文件已存在则覆盖）")
    parser.add_argument("--name", help="世界书名称（仅新建时有效）")
    parser.add_argument("--list", action="store_true",
                        help="列出世界书中所有条目（不修改）")
    parser.add_argument("--delete", type=int, metavar="UID",
                        help="删除指定 UID 的条目")
    parser.add_argument("--batch",
                        help="从 JSON 文件批量添加条目（文件内容为条目对象数组）")
    parser.add_argument("--batch-edit",
                        help="从 JSON 文件批量编辑条目（数组，每个对象必须含 uid）")

    # ---- 条目操作参数 ----
    parser.add_argument("--add", action="store_true",
                        help="添加新条目")
    parser.add_argument("--edit", type=int, metavar="UID",
                        help="编辑指定 UID 的条目")

    # ---- 条目字段参数 ----
    parser.add_argument("--comment", help="条目标题/备注")
    parser.add_argument("--content", help="条目正文内容，或 @文件路径 从文件读取")
    parser.add_argument("--keys", help="主触发词，逗号分隔")
    parser.add_argument("--keys2", help="辅助触发词，逗号分隔")
    parser.add_argument("--depth", type=int, help="深度层级 (1-999)")
    parser.add_argument("--constant", action="store_true",
                        help="设为常驻条目（始终激活）")
    parser.add_argument("--no-constant", action="store_true",
                        help="取消常驻")
    parser.add_argument("--order", type=int, help="排序值（越大越靠后）")
    parser.add_argument("--position", type=int, choices=[0, 1, 2, 3, 4, 5, 6, 7],
                        help="注入位置: 0=↑Char 1=↓Char 2=↑AT 3=↓AT 4=@D 5=↑EM 6=↓EM 7=Outlet")
    parser.add_argument("--outlet-name", dest="outlet_name",
                        help="Outlet 名称（position=7 时使用）")
    parser.add_argument("--disable", action="store_true",
                        help="设为禁用状态")
    parser.add_argument("--enable", action="store_true",
                        help="设为启用状态")
    parser.add_argument("--selective", action="store_true",
                        help="设为选择性激活")
    parser.add_argument("--no-selective", action="store_true",
                        help="取消选择性激活")
    parser.add_argument("--selective-logic", type=int, choices=[0, 1],
                        help="选择性逻辑: 0=AND 1=OR")
    parser.add_argument("--probability", type=int,
                        help="触发概率 (0-100, 默认100)")
    parser.add_argument("--add-memo", type=lambda x: x.lower() in ("true", "1", "yes"),
                        help="是否添加到备注 (true/false)")
    parser.add_argument("--group", help="分组名")
    parser.add_argument("--group-weight", type=int,
                        help="分组权重")
    parser.add_argument("--group-override", action="store_true",
                        help="覆盖分组设置")
    parser.add_argument("--role", type=int, choices=[0, 1, 2],
                        help="角色: 0=System 1=User 2=Assistant")
    parser.add_argument("--prevent-recursion", action="store_true",
                        help="不可进一步递归（本条目不触发其他条目）")
    parser.add_argument("--exclude-recursion", action="store_true",
                        help="无法被其他条目激活（本条目不被其他条目触发）")
    parser.add_argument("--scan-depth", type=int,
                        help="扫描深度")
    parser.add_argument("--case-sensitive", type=lambda x: x.lower() in ("true", "1", "yes"),
                        help="大小写敏感 (true/false)")
    parser.add_argument("--match-whole-words", type=lambda x: x.lower() in ("true", "1", "yes"),
                        help="全词匹配 (true/false)")
    parser.add_argument("--use-group-scoring", action="store_true",
                        help="使用分组评分")
    parser.add_argument("--sticky", type=int,
                        help="粘性值")
    parser.add_argument("--cooldown", type=int,
                        help="冷却值")
    parser.add_argument("--delay", type=int,
                        help="延迟值")

    args = parser.parse_args()

    # ========== 列表模式 ==========
    if args.list:
        if not os.path.exists(args.output):
            print(f"错误: 文件不存在 - {args.output}", file=sys.stderr)
            sys.exit(1)
        book, entries, name = load_existing(args.output)
        print(f"世界书: {args.output}")
        if name:
            print(f"名称: {name}")
        print(f"共 {len(entries)} 个条目:\n")
        for k in sorted(entries.keys(), key=int):
            e = entries[k]
            pos_label = POSITION_LABELS.get(e.get("position"), str(e.get("position", "?")))
            print(
                f"  UID={e.get('uid', k)}  |  "
                f"pos={pos_label}  |  "
                f"depth={e['depth']}  |  "
                f"常驻={'Y' if e.get('constant') else 'N'}  |  "
                f"disable={'Y' if e.get('disable') else 'N'}  |  "
                f"preventRec={'Y' if e.get('preventRecursion') else 'N'}  |  "
                f"excludeRec={'Y' if e.get('excludeRecursion') else 'N'}  |  "
                f"order={e.get('order')}  |  "
                f"触发词={e.get('key', [])}"
            )
            print(f"    标题: {e.get('comment', '')[:80]}")
            print()
        return

    # ========== 加载 / 新建 ==========
    book, entries, book_name = load_existing(args.output)

    if args.new or not os.path.exists(args.output):
        # 新建
        book = {}
        entries = {}
        book_name = args.name
        print(f"创建新的世界书: {args.output}")

    is_modified = False

    # ========== 删除 ==========
    if args.delete is not None:
        uid_str = str(args.delete)
        if uid_str not in entries:
            print(f"错误: 未找到 UID={args.delete} 的条目", file=sys.stderr)
            sys.exit(1)
        comment = entries[uid_str].get("comment", "")
        del entries[uid_str]
        print(f"已删除 UID={args.delete}: {comment}")
        is_modified = True

    # ========== 编辑 ==========
    if args.edit is not None:
        uid_str = str(args.edit)
        if uid_str not in entries:
            print(f"错误: 未找到 UID={args.edit} 的条目", file=sys.stderr)
            sys.exit(1)
        existing = entries[uid_str]
        new_entry = build_entry(args, uid=args.edit, display_index=existing.get("displayIndex"),
                                existing_entry=existing)
        entries[uid_str] = new_entry
        print(f"已编辑 UID={args.edit}: {new_entry.get('comment', '')}")
        is_modified = True

    # ========== 添加 ==========
    if args.add:
        uid = get_next_uid(entries)
        display_index = get_next_display_index(entries)
        if args.order is None:
            args.order = get_next_order(entries)
        new_entry = build_entry(args, uid=uid, display_index=display_index)
        entries[str(uid)] = new_entry
        print(f"已添加 UID={uid}: {new_entry.get('comment', '')}")
        is_modified = True

    # ========== 批量 ==========
    if args.batch:
        batch_data = load_json(args.batch)
        if not isinstance(batch_data, list):
            print("错误: batch 文件内容必须是一个 JSON 数组", file=sys.stderr)
            sys.exit(1)
        for item in batch_data:
            uid = get_next_uid(entries)
            display_index = get_next_display_index(entries)
            if "order" not in item or item["order"] is None:
                item["order"] = get_next_order(entries)
            new_entry = build_entry(item, uid=uid, display_index=display_index)
            entries[str(uid)] = new_entry
            print(f"已添加 UID={uid}: {new_entry.get('comment', '')}")
            is_modified = True
        print(f"批量完成: 共添加 {len(batch_data)} 个条目")

    # ========== 批量编辑 ==========
    if args.batch_edit:
        batch_data = load_json(args.batch_edit)
        if not isinstance(batch_data, list):
            print("错误: batch-edit 文件内容必须是一个 JSON 数组", file=sys.stderr)
            sys.exit(1)
        for item in batch_data:
            if "uid" not in item:
                print(f"错误: batch-edit 每个对象必须含 uid 字段: {item}", file=sys.stderr)
                sys.exit(1)
            uid_str = str(item["uid"])
            if uid_str not in entries:
                print(f"错误: 未找到 UID={item['uid']} 的条目", file=sys.stderr)
                sys.exit(1)
            existing = entries[uid_str]
            # remove uid from item dict so build_entry doesn't try to overwrite it
            edit_item = {k: v for k, v in item.items() if k != "uid"}
            new_entry = build_entry(edit_item, uid=item["uid"], display_index=existing.get("displayIndex"),
                                    existing_entry=existing)
            entries[uid_str] = new_entry
            print(f"已编辑 UID={item['uid']}: {new_entry.get('comment', '')}")
            is_modified = True
        print(f"批量编辑完成: 共修改 {len(batch_data)} 个条目")

    # ========== 保底检查 ==========
    if not is_modified and not args.list:
        print("提示: 未执行任何操作。使用 --add / --edit / --delete / --list 指定操作。", file=sys.stderr)
        parser.print_help()
        sys.exit(0)

    # ========== 保存 ==========
    book["entries"] = entries
    if book_name:
        book["name"] = book_name

    save_json(book, args.output)
    print(f"已保存至: {os.path.abspath(args.output)}")


if __name__ == "__main__":
    main()
