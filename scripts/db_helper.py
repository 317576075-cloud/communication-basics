#!/usr/bin/env python3
"""
communication-basics 数据读写统一脚本（数据回写框架）。
本脚本为数据回写框架，数据库地址与密钥需自行配置；表结构见各 write/query 函数的 JSON 字段。
（若无需数据回写，可不配置数据库，Skill 其余功能不受影响。）

用法：
用法：
  # 写入陪练记录
  python3 scripts/db_helper.py write-training --json '{...}'

  # 写入反馈记录
  python3 scripts/db_helper.py write-feedback --json '{...}'

  # 查询测评结果
  python3 scripts/db_helper.py query-assessment --mis zhangsan

  # 查询陪练历史
  python3 scripts/db_helper.py query-training --mis zhangsan [--limit 20]

依赖：Python 3.7+，无第三方依赖（数据库需支持 PostgREST 风格 REST API）。
"""
import json
import ssl
import sys
import urllib.request
from urllib.parse import quote

# ─── 数据库配置 ───
# TODO: 将以下地址替换为自建数据库（需支持 PostgREST 风格 REST API）的地址
_TRAINING_DB = "TODO_YOUR_DB_URL"
# TODO: 填入你的 API key（或改用环境变量读取）
import os
_K1_P = os.environ.get("TRAINING_DB_TOKEN", "")
_K1 = _K1_P

# TODO: 将以下地址替换为自建测评数据库的地址
_ASSESSMENT_DB = "TODO_YOUR_DB_URL"
# TODO: 填入你的 API key（或改用环境变量读取）
_K2_P = os.environ.get("ASSESSMENT_DB_TOKEN", "")
_K2 = _K2_P

_TRAINING_TOKEN = _K1
_ASSESSMENT_TOKEN = _K2

# ─── 数据质量校验说明 ───
# 原内部版本含六道防刷分闸门（轮数门槛/每日上限/低分不计分/评语查重/单位校验/双重加权检测）。
# 开源版无积分、发币等激励机制，前四道计分类闸门已移除；
# 仅保留两项数据质量校验：评分单位校验、双重加权检测，防止脏分数入库。

# ─── 场景权重表（与 path-c-practice.md 一致） ───
WEIGHTS = {
    "识人":         {"influence":0.20,"relationship":0.25,"information":0.10,"perception":0.35,"emotion":0.10},
    "破冰":         {"influence":0.15,"relationship":0.40,"information":0.10,"perception":0.20,"emotion":0.15},
    "倾听":         {"influence":0.05,"relationship":0.15,"information":0.25,"perception":0.40,"emotion":0.15},
    "回应":         {"influence":0.20,"relationship":0.10,"information":0.40,"perception":0.20,"emotion":0.10},
    "接好任务":     {"influence":0.20,"relationship":0.15,"information":0.40,"perception":0.15,"emotion":0.10},
    "请教求助":     {"influence":0.10,"relationship":0.40,"information":0.25,"perception":0.15,"emotion":0.10},
    "同步汇报":     {"influence":0.20,"relationship":0.15,"information":0.40,"perception":0.15,"emotion":0.10},
    "回应批评":     {"influence":0.15,"relationship":0.15,"information":0.15,"perception":0.20,"emotion":0.35},
    "会议发言":     {"influence":0.35,"relationship":0.15,"information":0.20,"perception":0.15,"emotion":0.15},
    "澄清提问":     {"influence":0.20,"relationship":0.10,"information":0.40,"perception":0.15,"emotion":0.15},
    "发表不同意见": {"influence":0.30,"relationship":0.20,"information":0.15,"perception":0.15,"emotion":0.20},
    "说服他人":     {"influence":0.40,"relationship":0.15,"information":0.15,"perception":0.20,"emotion":0.10},
    "给TA建议":     {"influence":0.30,"relationship":0.25,"information":0.15,"perception":0.15,"emotion":0.15},
    "为TA点赞":     {"influence":0.15,"relationship":0.45,"information":0.10,"perception":0.20,"emotion":0.10},
    "进度催办":     {"influence":0.40,"relationship":0.15,"information":0.15,"perception":0.15,"emotion":0.15},
    "主动道歉":     {"influence":0.15,"relationship":0.35,"information":0.10,"perception":0.15,"emotion":0.25},
    "学会拒绝":     {"influence":0.20,"relationship":0.20,"information":0.10,"perception":0.15,"emotion":0.35},
    "处理冲突":     {"influence":0.10,"relationship":0.20,"information":0.10,"perception":0.20,"emotion":0.40},
}
DEFAULT_W = {"influence":0.20,"relationship":0.20,"information":0.20,"perception":0.20,"emotion":0.20}

# ─── 用户标识错拼归并 ────────────────────────────
# 如发现 AI 层曾把同一用户的标识拼错导致人员统计分裂，在此维护归并映射表，
# 写入前强制归并到正确标识。
USER_ID_ALIASES = {
}

# ─── 场景名归一化 ────────────────────────────────
# 原因：陪练菜单曾启用新场景展示名（识人调频/破冰开场/倾听对焦/回应对齐），
# 但 WEIGHTS 表只有旧 18 个名字，get 匹配不到就落到 DEFAULT_W 均匀 20%，
# 导致这 4 个场景的五维加权分失真。
# 处理：写入前先归一化——新名 → 对应旧名；常见 AI 自由发挥变体也一并归并。
# 归一化后查表仍命不中的，才降级 DEFAULT_W。
SCENARIO_ALIASES = {
    # 新场景展示名 → 对应标准名
    "识人调频": "识人",
    "破冰开场": "破冰",
    "倾听对焦": "倾听",
    "回应对齐": "回应",
    # 历史变体归并（AI 填模板时自由发挥产生）
    "识人：disc读人术": "识人",
    "识人：disc": "识人",
    "disc读人术": "识人",
    "disc四型识别法": "识人",
    "disc四象限识别法": "识人",
    "为他点赞": "为TA点赞",
    "为她点赞": "为TA点赞",
    "倾听共情": "倾听",
    "向上汇报": "同步汇报",
    "接受批评": "回应批评",
    "回应：四层对齐": "回应",
}

def normalize_scenario(name):
    """场景名归一化：去首尾空格 → 别名映射 → 命中标准场景才返回。
    匹配不到标准 18 场景时返回 "自定义场景"（由 DEFAULT_W 兜底，但场景名入库统一）。"""
    if not name:
        return "自定义场景"
    n = name.strip()
    # 别名表全小写比较，避免大小写/DISC 大小写不一致
    key = n.casefold()
    # 先查小写别名表
    folded_aliases = {k.casefold(): v for k, v in SCENARIO_ALIASES.items()}
    if key in folded_aliases:
        return folded_aliases[key]
    # 再查标准权重表（即标准 18 场景）
    if n in WEIGHTS:
        return n
    # 兜底：无法映射到标准场景的，统一归为「自定义场景」，防止脏名入库
    return "自定义场景"


def _ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _post(url, token, payload_dict, retries=2):
    """POST JSON 到数据库 REST API（return=representation 拿新行），重试 retries 次。
    返回 (rows: list|None, err: str|None)。成功时 rows 为包含新行(含id)的列表。"""
    data = json.dumps(payload_dict, ensure_ascii=False).encode()
    headers = {
        "apikey": token,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    ctx = _ssl_ctx()
    last_err = "unknown"
    for i in range(retries):
        # 测试钩子：外部可通过 _TEST_POST_HOOK 拦截请求（dry-run 用），返回 (rows, err)
        hook = globals().get("_TEST_POST_HOOK")
        if hook is not None:
            return hook(url, token, payload_dict)
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            resp = urllib.request.urlopen(req, timeout=10, context=ctx)
            body = resp.read().decode()
            rows = json.loads(body) if body else []
            if isinstance(rows, dict):  # 个别版本返回单对象
                rows = [rows]
            return rows, None
        except urllib.error.HTTPError as e:
            try:
                last_err = "HTTP %s %s" % (e.code, e.read().decode()[:200])
            except Exception:
                last_err = "HTTP %s" % e.code
        except Exception as e:
            last_err = str(e)
    return None, last_err


def _verify_row(url, token, row_id):
    """按 id 二次 GET 校验记录确实落库。返回 True/False。"""
    # 测试钩子：dry-run 模式下跳过真实校验
    if globals().get("_TEST_POST_HOOK") is not None:
        return True
    headers = {"apikey": token, "Authorization": f"Bearer {token}"}
    ctx = _ssl_ctx()
    try:
        req = urllib.request.Request(url + "?id=eq.%s&select=id" % row_id,
                                     headers=headers, method="GET")
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        rows = json.loads(resp.read().decode())
        return bool(rows)
    except Exception:
        return False


def _get(url, token):
    """GET 数据库 REST API，返回解析后的 JSON。"""
    if not url.startswith("http"):
        print(json.dumps({"success": False, "error": "数据库地址未配置（scripts/db_helper.py 顶部 TODO_YOUR_DB_URL）"}))
        return None
    headers = {
        "apikey": token,
        "Authorization": f"Bearer {token}",
    }
    req = urllib.request.Request(url, headers=headers, method="GET")
    ctx = _ssl_ctx()
    try:
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        return json.loads(resp.read().decode())
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
        return None


# ════════════════════════════════════════════════════════
#  命令 1：write-training  写入陪练记录
# ════════════════════════════════════════════════════════

def cmd_write_training(args):
    """
    正常完成（is_complete 缺省或 true）：原 14 字段及原加权计分逻辑。
    超时（is_complete=false）：原始分可省略，忽略所有传入分数，
    五维得分和总分显式写为 null，避免数据库默认值生成分数；仍保存其余练习信息。
    """
    raw = json.loads(args.json_data)
    if not isinstance(raw, dict):
        print("WRITE_FAIL table=training_records reason=JSON_must_be_object")
        sys.exit(1)
    is_complete = raw.get("is_complete", True)
    # 防止字符串 "false" 被 bool() 转成 True，误把超时分数写入。
    if type(is_complete) is not bool:
        print("WRITE_FAIL table=training_records reason=is_complete_must_be_boolean")
        sys.exit(1)

    required = [
        "mis", "name", "scenario", "role_target", "rounds",
        "highlights", "improvement", "method_used", "water_level",
    ]
    dims = ["influence", "relationship", "information", "perception", "emotion"]
    if is_complete:
        required += ["raw_" + d for d in dims]
    missing = [f for f in required if f not in raw]
    if missing:
        print(json.dumps({"success": False, "error": f"缺少必填字段: {missing}"}))
        sys.exit(1)

    # 不接受后台任务丢失用户上下文后生成的占位身份。
    for key in ("mis", "name"):
        value = raw[key]
        if not isinstance(value, str) or not value.strip():
            print("WRITE_FAIL table=training_records reason=missing_identity field=%s" % key)
            sys.exit(1)
        value = value.strip()
        lowered = value.casefold()
        if (lowered in {"unknown", "anonymous", "null", "none", "n/a", "未知", "匿名", "未提供"}
                or lowered.startswith(("unknown_", "anonymous_"))
                or any(char in value for char in "{}<>")):
            print("WRITE_FAIL table=training_records reason=placeholder_identity field=%s" % key)
            sys.exit(1)
        raw[key] = value

    # 标识错拼归并：AI 层可能拼错用户标识，强制查表归并，防止同一人分裂多套账号
    if raw["mis"] in USER_ID_ALIASES:
        print("WARN user_id_alias_merged %s -> %s" % (raw["mis"], USER_ID_ALIASES[raw["mis"]]), file=sys.stderr)
        raw["mis"] = USER_ID_ALIASES[raw["mis"]]

    # 场景名先归一化再入 payload/查权重表（强制收口到标准18场景）
    scenario = normalize_scenario(raw["scenario"])
    if scenario == "自定义场景" and raw["scenario"].strip() not in ("自定义场景", "自定义"):
        # 无法识别为标准场景时打印告警，方便运营定位 AI 层没传标准名的问题
        print(f"WARN scenario_fallback unknown_scenario={raw['scenario']!r} -> 自定义场景", file=sys.stderr)

    # ─── 数据质量校验（仅对 is_complete=true 生效）──────────
    # 有效轮数：用户有效消息轮数（重复输入由 AI 层在 rounds 中先剔除，脚本信任传入的 rounds）
    effective_rounds = int(raw["rounds"])
    if is_complete:
        # 单位校验：五维原始分全部 ≤10，疑似按 1-10 锚点打分混入百分制体系，
        # 拒绝写入（不写库、不重试），要求 AI 层按百分制重新评分。
        if all(float(raw[f"raw_{d}"]) <= 10 for d in dims):
            print("WRITE_FAIL table=training_records reason=score_scale_suspect_10pt (五维原始分全部≤10，疑似按1-10锚点打分；请按百分制0-100重新评分后再写入)")
            sys.exit(1)
        w = WEIGHTS.get(scenario, DEFAULT_W)
        # ─── 双重加权检测与自动还原 ───
        # 背景：AI 层偶发把「已按场景权重加权后的分数」当原始分传入，
        # 脚本再乘一次权重导致总分严重失真。
        # 数学特征：若传入 input_i = R_i × w_i（已加权），则 input_i / w_i = R_i 恰为真实原始分；
        # 五维的 input_i / w_i 离散度（CV）极低。正常原始分各维独立打分，除以权重后 CV 高，
        # 几乎不可能与场景权重成比例。检测命中即自动还原，写 WARN 供审计，无需 AI 重试。
        # 注：均匀权重场景（自定义场景 DEFAULT_W）下该特征不可区分，跳过检测。
        weights_uniform = all(abs(w[d] - 0.20) < 1e-9 for d in dims)
        raw_inputs = {d: float(raw["raw_" + d]) for d in dims}
        input_sum = sum(raw_inputs.values())
        if (not weights_uniform and input_sum > 0 and max(raw_inputs.values()) >= 10
                and input_sum <= 120):
            est = [raw_inputs[d] / w[d] for d in dims]
            mean_est = sum(est) / len(est)
            cv = (sum((x - mean_est) ** 2 for x in est) / len(est)) ** 0.5 / mean_est
            if cv < 0.18:
                recovered = {d: int(max(0, min(100, round(raw_inputs[d] / w[d])))) for d in dims}
                print("WARN double_weight_recovered scenario=%s input=%s recovered=%s cv=%.3f"
                      % (scenario, raw_inputs, recovered, cv), file=sys.stderr)
                for d in dims:
                    raw["raw_" + d] = recovered[d]
        scores = {}
        for d in dims:
            raw_score = float(raw[f"raw_{d}"])
            weighted = round(raw_score * w[d])
            cap = round(w[d] * 100)
            scores[d] = int(min(weighted, cap))
        score_total = sum(scores.values())

    # 水位字段强制校验——禁止默认填 L3/L4，取值必须与档位映射一致
    wl = raw.get("water_level", "")
    if not isinstance(wl, str) or wl.strip().upper() not in {"L1", "L2", "L3", "L4"}:
        print("WRITE_FAIL table=training_records reason=invalid_water_level value=%r "
              "(须为 L1/L2/L3/L4，与真实水位来源对应，禁止默认填 L3/L4)" % (wl,))
        sys.exit(1)

    payload = {
        "mis": raw["mis"],
        "name": raw["name"],
        "scenario": scenario,
        "role_target": raw["role_target"],
        "rounds": effective_rounds,
        "highlights": raw["highlights"],
        "improvement": raw["improvement"],
        "method_used": raw["method_used"],
        "water_level": wl.strip().upper(),
        "is_complete": is_complete,
    }
    if is_complete:
        # 正常完成：写入按场景权重加权后的五维得分与总分。
        payload.update({"score_" + d: scores[d] for d in dims})
        payload["score_total"] = score_total
    else:
        # 超时收尾：正常写档但分数置 NULL；绝不填 0。
        payload.update({"score_" + d: None for d in dims})
        payload["score_total"] = None

    url = f"{_TRAINING_DB}/rest/v1/training_records"
    table = "training_records"
    rows, err = _post(url, _TRAINING_TOKEN, payload)
    if rows is None:
        print("WRITE_FAIL table=%s reason=%s" % (table, err))
        sys.exit(1)
    row_id = rows[0].get("id") if rows and isinstance(rows[0], dict) else None
    if row_id is None:
        print("WRITE_FAIL table=%s reason=no_id_returned" % table)
        sys.exit(1)
    if not _verify_row(url, _TRAINING_TOKEN, row_id):
        print("WRITE_FAIL table=%s reason=verify_failed id=%s" % (table, row_id))
        sys.exit(1)
    if not is_complete:
        # 校验真实落库内容，不能仅凭有 ID 就将错误数据认作写入成功。
        fields = ["mis", "name", "is_complete"] + ["score_" + d for d in dims] + ["score_total"]
        check_url = url + "?id=eq." + quote(str(row_id), safe="") + "&select=" + ",".join(fields)
        saved = _get(check_url, _TRAINING_TOKEN)
        if (not isinstance(saved, list) or len(saved) != 1
                or not isinstance(saved[0], dict)
                or any(key not in saved[0] or saved[0][key] != payload[key] for key in fields)
                or saved[0].get("is_complete") is not False):
            # 记录已存在：不可再次 POST 复制脏记录，应排查数据库默认值/触发器。
            print("WRITE_FAIL table=%s reason=stored_data_mismatch id=%s retryable=false" % (table, row_id))
            sys.exit(1)
    if is_complete:
        print("WRITE_OK table=%s id=%s score_total=%s" % (table, row_id, score_total))
    else:
        print("WRITE_OK table=%s id=%s is_complete=false" % (table, row_id))


# ════════════════════════════════════════════════════════
#  命令 2：write-feedback  写入反馈记录
# ════════════════════════════════════════════════════════

def cmd_write_feedback(args):
    """
    输入 JSON 必须包含以下 6 个字段（缺一不可）：
      mis, name, path, scenario, rating, comment
    """
    raw = json.loads(args.json_data)

    required = ["mis", "name", "path", "scenario", "rating", "comment"]
    missing = [f for f in required if f not in raw]
    if missing:
        print(json.dumps({"success": False, "error": f"缺少必填字段: {missing}"}))
        sys.exit(1)

    payload = {
        "mis": raw["mis"],
        "name": raw["name"],
        "path": raw["path"],
        "scenario": normalize_scenario(raw["scenario"]),
        "rating": int(raw["rating"]),
        "comment": raw.get("comment", ""),
    }

    url = f"{_TRAINING_DB}/rest/v1/feedback_records"
    table = "feedback_records"
    rows, err = _post(url, _TRAINING_TOKEN, payload)
    if rows is None:
        print("WRITE_FAIL table=%s reason=%s" % (table, err))
        sys.exit(1)
    row_id = rows[0].get("id") if rows and isinstance(rows[0], dict) else None
    if row_id is None:
        print("WRITE_FAIL table=%s reason=no_id_returned" % table)
        sys.exit(1)
    if not _verify_row(url, _TRAINING_TOKEN, row_id):
        print("WRITE_FAIL table=%s reason=verify_failed id=%s" % (table, row_id))
        sys.exit(1)
    print("WRITE_OK table=%s id=%s" % (table, row_id))


# ════════════════════════════════════════════════════════
#  命令 3：query-assessment  查询测评结果
# ════════════════════════════════════════════════════════

def cmd_query_assessment(args):
    """查询用户最新一条测评记录。输出 JSON。"""
    mis = quote(args.mis, safe="")
    url = (
        f"{_ASSESSMENT_DB}/rest/v1/assessment_results"
        f"?select=name,mis,d1,d2,d3,d4,d5,total,grade,created_at"
        f"&mis=eq.{mis}&order=created_at.desc&limit=1"
    )
    data = _get(url, _ASSESSMENT_TOKEN)
    if data is None:
        print(json.dumps({"success": False, "error": "查询失败"}))
        sys.exit(1)
    if not data:
        print(json.dumps({"success": True, "found": False, "data": None}))
    else:
        record = data[0]
        print(json.dumps({"success": True, "found": True, "data": record}, ensure_ascii=False))


# ════════════════════════════════════════════════════════
#  命令 4：query-training  查询陪练历史
# ════════════════════════════════════════════════════════

def cmd_query_training(args):
    """查询用户的陪练记录列表。"""
    mis = quote(args.mis, safe="")
    limit = args.limit or 20
    url = (
        f"{_TRAINING_DB}/rest/v1/training_records"
        f"?mis=eq.{mis}&order=created_at.desc&limit={limit}"
    )
    data = _get(url, _TRAINING_TOKEN)
    if data is None:
        print(json.dumps({"success": False, "error": "查询失败"}))
        sys.exit(1)
    print(json.dumps({"success": True, "count": len(data), "records": data}, ensure_ascii=False))


# ════════════════════════════════════════════════════════
#  CLI 入口
# ════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="communication-basics 数据读写工具")
    sub = parser.add_subparsers(dest="command")

    # write-training
    p1 = sub.add_parser("write-training", help="写入陪练记录")
    p1.add_argument("--json", dest="json_data", required=True, help="JSON 字符串，包含全部必填字段")

    # write-feedback
    p2 = sub.add_parser("write-feedback", help="写入反馈记录")
    p2.add_argument("--json", dest="json_data", required=True, help="JSON 字符串，包含 6 个必填字段")

    # query-assessment
    p3 = sub.add_parser("query-assessment", help="查询测评结果")
    p3.add_argument("--mis", required=True, help="用户标识")

    # query-training
    p4 = sub.add_parser("query-training", help="查询陪练历史")
    p4.add_argument("--mis", required=True, help="用户标识")
    p4.add_argument("--limit", type=int, default=20, help="返回记录数（默认20）")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "write-training": cmd_write_training,
        "write-feedback": cmd_write_feedback,
        "query-assessment": cmd_query_assessment,
        "query-training": cmd_query_training,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
