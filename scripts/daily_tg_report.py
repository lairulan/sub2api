#!/usr/bin/env python3
"""
neo-faheng Sub2API Daily Report -> Telegram
Runs via GitHub Actions daily at 09:00 CST.
Fetches usage data from Admin API and sends formatted report to Telegram.
"""

import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

# ─── Configuration (from environment / secrets) ─────────────
API_BASE = "https://relay.0xfaheng.xyz/api/v1"
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")
TZ = "Asia/Shanghai"


# ─── HTTP Helpers ────────────────────────────────────────────
def api_get(path, token, params=None):
    url = f"{API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  API error {path}: {e}")
        return {"error": str(e)}


def api_post(path, data):
    url = f"{API_BASE}{path}"
    payload = json.dumps(data).encode()
    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json"
    }, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}


def tg_send(text, parse_mode="HTML"):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": "true"
    }).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  TG error: {e}")
        return {"ok": False, "error": str(e)}


def fmt_n(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(int(n))


def fmt_c(c):
    return f"${c:.2f}"


# ─── Main ────────────────────────────────────────────────────
def main():
    if not all([TG_BOT_TOKEN, TG_CHAT_ID, ADMIN_EMAIL, ADMIN_PASSWORD]):
        print("ERROR: Missing required environment variables")
        sys.exit(1)

    cst = timezone(timedelta(hours=8))
    now = datetime.now(cst)
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")

    print(f"[neo-faheng] Daily report for {yesterday}")

    # Login
    login = api_post("/auth/login", {
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
    })
    token = login.get("data", {}).get("access_token")
    if not token:
        tg_send(f"[neo-faheng] Login failed")
        sys.exit(1)
    print("  Logged in")

    # ─── Fetch all data ──────────────────────────────────────
    dq = {"start_date": yesterday, "end_date": yesterday, "timezone": TZ}

    stats = api_get("/admin/usage/stats", token, dq).get("data", {})

    model_list = api_get("/admin/dashboard/models", token, dq
        ).get("data", {}).get("models", [])

    key_trend = api_get("/admin/dashboard/api-keys-trend", token,
        {**dq, "granularity": "day"}).get("data", {}).get("trend", [])

    group_list = api_get("/admin/dashboard/groups", token, dq
        ).get("data", {}).get("groups", [])

    hourly = api_get("/admin/dashboard/trend", token,
        {**dq, "granularity": "hour"}).get("data", {}).get("trend", [])

    weekly = api_get("/admin/dashboard/trend", token, {
        "start_date": week_ago, "end_date": yesterday,
        "granularity": "day", "timezone": TZ
    }).get("data", {}).get("trend", [])

    # User ranking: aggregate from usage logs
    usage_items = []
    page = 1
    while page <= 10:
        r = api_get("/admin/usage", token, {
            **dq, "page": page, "per_page": 100
        })
        items = r.get("data", {}).get("items", [])
        if not items:
            break
        usage_items.extend(items)
        page += 1

    user_agg = {}
    for item in usage_items:
        uid = item.get("user_id", 0)
        email = item.get("user", {}).get("email", f"user_{uid}")
        if uid not in user_agg:
            user_agg[uid] = {"email": email, "requests": 0, "cost": 0, "tokens": 0}
        user_agg[uid]["requests"] += 1
        user_agg[uid]["cost"] += item.get("total_cost", 0)
        user_agg[uid]["tokens"] += (
            item.get("input_tokens", 0) + item.get("output_tokens", 0) +
            item.get("cache_creation_tokens", 0) + item.get("cache_read_tokens", 0)
        )
    user_list = sorted(user_agg.values(), key=lambda x: x["cost"], reverse=True)

    # Dashboard stats (cumulative + accounts)
    dash = api_get("/admin/dashboard/stats", token, {"timezone": TZ}).get("data", {})

    # Upstream accounts
    accounts = api_get("/admin/accounts", token, {
        "page": 1, "per_page": 20
    }).get("data", {}).get("items", [])

    print("  Data fetched")

    # ─── Parse ───────────────────────────────────────────────
    total_req = stats.get("total_requests", 0)
    total_tokens = stats.get("total_tokens", 0)
    total_cost = stats.get("total_cost", 0)
    avg_dur = stats.get("average_duration_ms", 0) / 1000
    cum_cost = dash.get("total_cost", 0)
    cum_req = dash.get("total_requests", 0)
    active_users = dash.get("active_users", 0)
    total_users = dash.get("total_users", 0)
    normal_accts = dash.get("normal_accounts", 0)
    error_accts = dash.get("error_accounts", 0)
    total_accts = dash.get("total_accounts", 0)
    uptime_s = dash.get("uptime", 0)
    uptime_h = uptime_s // 3600
    uptime_d = uptime_h // 24

    # Peak hours
    peak_h, peak_req_h = "", 0
    peak_cost_h, peak_cost_v = "", 0
    for h in hourly:
        hr = h.get("requests", 0)
        hc = h.get("cost", 0)
        dt = h.get("date", "")
        hh = dt[-8:-3] if len(dt) > 8 else dt[-5:]
        if hr > peak_req_h:
            peak_req_h, peak_h = hr, hh
        if hc > peak_cost_v:
            peak_cost_v, peak_cost_h = hc, hh

    # Weekly totals
    w_cost = sum(d.get("cost", 0) for d in weekly)
    w_req = sum(d.get("requests", 0) for d in weekly)

    # ─── Build Messages ─────────────────────────────────────
    def bar(pct, w=10):
        filled = int(pct / 100 * w)
        return "\u2588" * filled + "\u2591" * (w - filled)

    # 消息1: 总览 + 上游账号 + 高峰时段
    lines1 = [
        f"<b>neo-法恒 每日运营报告</b>",
        f"<code>{yesterday}</code> | relay.0xfaheng.xyz",
        "",
        "━━ <b>总览</b> ━━━━━━━━━━━━",
        f"请求数:    <b>{total_req}</b>",
        f"Token消耗: <b>{fmt_n(total_tokens)}</b>",
        f"费用:      <b>{fmt_c(total_cost)}</b>",
        f"平均响应:  <b>{avg_dur:.1f}秒</b>",
        f"活跃Key:   <b>{len(key_trend)}个</b>",
        f"用户:      {active_users}活跃 / {total_users}总计",
        f"运行时长:  {uptime_d}天{uptime_h % 24}小时",
        f"累计总计:  {fmt_c(cum_cost)} / {fmt_n(cum_req)}次请求",
    ]

    # 上游账号状态
    acct_ok = sum(1 for a in accounts if a.get("status") == "active")
    acct_total = len(accounts)
    lines1 += [
        "",
        "━━ <b>上游账号</b> ━━━━━━━━━",
        f"状态: {acct_ok}/{acct_total}正常" +
            (f" ({acct_total - acct_ok}个异常!)" if acct_ok < acct_total else " (全部正常)"),
    ]
    for a in accounts:
        name = a.get("name", "?")
        status = a.get("status", "?")
        status_cn = "正常" if status == "active" else "异常"
        dot = "+" if status == "active" else "!"
        err = a.get("error_message", "")
        extra = f" - {err[:25]}" if err else ""
        lines1.append(f"  [{dot}] {name}: {status_cn}{extra}")

    # 高峰时段
    if peak_h:
        lines1 += [
            "",
            "━━ <b>高峰时段</b> ━━━━━━━━━",
            f"最多请求: {peak_h} ({peak_req_h}次)",
            f"最高费用: {peak_cost_h} ({fmt_c(peak_cost_v)})",
        ]

    # 消息2: 模型 + Key + 分组
    lines2 = [f"<b>模型使用分布</b> ({yesterday})", ""]
    for m in sorted(model_list, key=lambda x: x.get("cost", 0), reverse=True):
        name = m.get("model", "?")
        mreq = m.get("requests", 0)
        mcost = m.get("cost", 0)
        pct = (mcost / total_cost * 100) if total_cost > 0 else 0
        lines2.append(
            f"  <code>{name[:20]:20s}</code> {mreq:>3}次 {fmt_c(mcost):>7} ({pct:.0f}%)"
        )

    lines2 += ["", "━━ <b>API Key 用量</b> ━━━━━━━", ""]
    for k in sorted(key_trend, key=lambda x: x.get("requests", 0), reverse=True):
        kname = k.get("key_name", k.get("name", "?"))
        kreq = k.get("requests", 0)
        ktok = k.get("tokens", 0)
        pct = (kreq / total_req * 100) if total_req > 0 else 0
        lines2.append(
            f"  <code>{kname[:12]:12s}</code> {kreq:>3}次 {fmt_n(ktok):>6}tok ({pct:.0f}%)"
        )

    lines2 += ["", "━━ <b>分组统计</b> ━━━━━━━━━━", ""]
    for g in sorted(group_list, key=lambda x: x.get("cost", 0), reverse=True):
        gname = g.get("group_name", g.get("group", "?"))
        greq = g.get("requests", 0)
        gcost = g.get("cost", 0)
        lines2.append(
            f"  <code>{gname[:12]:12s}</code> {greq:>3}次 {fmt_c(gcost):>7}"
        )

    # 消息3: 用户排名 + 7天趋势
    lines3 = [f"<b>用户费用排名</b> ({yesterday})", ""]
    for i, u in enumerate(user_list[:10], 1):
        email = u.get("email", "?")
        at_pos = email.find("@")
        if at_pos > 3:
            masked = email[:3] + "***" + email[at_pos:]
        else:
            masked = email
        ureq = u.get("requests", 0)
        ucost = u.get("cost", 0)
        lines3.append(
            f"  {i}. <code>{masked[:22]:22s}</code> {ureq:>3}次 {fmt_c(ucost):>7}"
        )

    lines3 += [
        "",
        "━━ <b>近7天趋势</b> ━━━━━━━━",
        f"合计: {fmt_c(w_cost)} / {fmt_n(w_req)}次请求",
        ""
    ]
    max_req_w = max((d.get("requests", 0) for d in weekly), default=1)
    for d in weekly:
        dd = d.get("date", "")[-5:]
        dreq = d.get("requests", 0)
        dcost = d.get("cost", 0)
        blen = int(dreq / max_req_w * 10) if max_req_w > 0 else 0
        b = "\u2588" * blen + "\u2591" * (10 - blen)
        mark = " <b>\u25c0</b>" if dd == yesterday[-5:] else ""
        lines3.append(
            f"  <code>{dd} {b}</code> {dreq:>4}次 {fmt_c(dcost):>7}{mark}"
        )

    lines3 += [
        "",
        f"<i>生成时间: {now.strftime('%Y-%m-%d %H:%M')} 北京时间</i>",
    ]

    # ─── Send ────────────────────────────────────────────────
    msgs = ["\n".join(lines1), "\n".join(lines2), "\n".join(lines3)]
    ok_count = 0
    for i, msg in enumerate(msgs, 1):
        print(f"  Sending msg {i} ({len(msg)} chars)...")
        r = tg_send(msg)
        if r.get("ok"):
            ok_count += 1
        else:
            print(f"  FAILED: {r}")

    print(f"Done: {ok_count}/{len(msgs)} messages sent.")
    return 0 if ok_count == len(msgs) else 1


if __name__ == "__main__":
    sys.exit(main())
