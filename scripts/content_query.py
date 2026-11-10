#!/usr/bin/env python3
"""按需查询题库和知识卡片，避免全量加载 680+576 行内容。

用法:
  python3 scripts/content_query.py questions --scenario 识人
  python3 scripts/content_query.py questions --id 1
  python3 scripts/content_query.py card --scenario 识人
  python3 scripts/content_query.py card --id 1
  python3 scripts/content_query.py list              # 列出所有场景名和ID
"""

import json, os, sys, argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")

QUESTIONS_FILE = os.path.join(DATA_DIR, "questions.json")
CARDS_FILE = os.path.join(DATA_DIR, "cards.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_by_scenario_or_id(data, scenario=None, scenario_id=None):
    """按场景名（模糊匹配）或 ID 查找。"""
    if scenario_id is not None:
        for item in data:
            if item["id"] == scenario_id:
                return item
        return None
    if scenario:
        # 精确匹配优先
        for item in data:
            if item["name"] == scenario:
                return item
        # 模糊：包含匹配
        for item in data:
            if scenario in item["name"] or (item.get("subtitle") and scenario in item["subtitle"]):
                return item
    return None


def cmd_questions(args):
    data = load_json(QUESTIONS_FILE)
    item = find_by_scenario_or_id(data, args.scenario, args.id)
    if not item:
        print(json.dumps({"error": f"场景未找到: scenario={args.scenario}, id={args.id}"}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(item, ensure_ascii=False, indent=2))


def cmd_card(args):
    data = load_json(CARDS_FILE)
    item = find_by_scenario_or_id(data, args.scenario, args.id)
    if not item:
        print(json.dumps({"error": f"卡片未找到: scenario={args.scenario}, id={args.id}"}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(item, ensure_ascii=False, indent=2))


def cmd_list(_args):
    questions = load_json(QUESTIONS_FILE)
    result = [{"id": q["id"], "name": q["name"], "subtitle": q.get("subtitle", ""), "dimension": q.get("dimension", "")} for q in questions]
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="内容按需查询")
    sub = parser.add_subparsers(dest="command")

    p_q = sub.add_parser("questions", help="查询某场景的3道测评题")
    p_q.add_argument("--scenario", type=str, default=None, help="场景名，如 识人/破冰")
    p_q.add_argument("--id", type=int, default=None, help="场景ID 1-18")

    p_c = sub.add_parser("card", help="查询某场景的知识卡片")
    p_c.add_argument("--scenario", type=str, default=None, help="场景名")
    p_c.add_argument("--id", type=int, default=None, help="场景ID 1-18")

    sub.add_parser("list", help="列出所有场景")

    args = parser.parse_args()
    if args.command == "questions":
        cmd_questions(args)
    elif args.command == "card":
        cmd_card(args)
    elif args.command == "list":
        cmd_list(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
