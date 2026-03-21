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

import paramiko

# ─── Configuration (from environment / secrets) ─────────────
API_BASE = "https://relay.0xfaheng.xyz/api/v1"
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")
SSH_HOST = "119.45.35.97"
SSH_USER = "ubuntu"
SSH_PASSWORD = os.environ.get("SSH_PASSWORD", "")
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


# ─── SSH Server Health ───────────────────────────────────────
def ssh_exec(ssh, cmd):
    """通过 SSH 执行命令并返回 stdout"""
    try:
        _, stdout, _ = ssh.exec_command(cmd, timeout=15)
        return stdout.read().decode().strip()
    except Exception:
        return ""


def get_server_health():
    """通过 SSH 采集服务器健康数据"""
    if not SSH_PASSWORD:
        print("  SSH_PASSWORD not set, skipping health check")
        return None

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SSH_HOST, username=SSH_USER, password=SSH_PASSWORD, timeout=15)
        print("  SSH connected")
    except Exception as e:
        print(f"  SSH connect failed: {e}")
        return None

    h = {}
    try:
        # CPU 使用率
        cpu_raw = ssh_exec(ssh, "top -bn1 | grep 'Cpu(s)' | awk '{print $2}'")
        h["cpu"] = float(cpu_raw.replace(",", ".")) if cpu_raw else 0

        # 内存
        mem = ssh_exec(ssh, "free -m | awk 'NR==2{printf \"%s|%s|%.1f\", $2,$3,$3/$2*100}'")
        p = mem.split("|")
        h["mem_total"] = int(p[0])
        h["mem_used"] = int(p[1])
        h["mem_pct"] = float(p[2])

        # 磁盘
        disk = ssh_exec(ssh, "df -h / | awk 'NR==2{printf \"%s|%s|%s\", $2,$3,$5}'")
        p = disk.split("|")
        h["disk_total"] = p[0]
        h["disk_used"] = p[1]
        h["disk_pct"] = int(p[2].replace("%", ""))

        # 负载
        load = ssh_exec(ssh, "cat /proc/loadavg | awk '{print $1}'")
        h["load"] = float(load) if load else 0

        # 系统运行时长
        h["uptime"] = ssh_exec(ssh, "uptime -p") or "未知"

        # Docker 容器状态
        docker_raw = ssh_exec(ssh,
            "sudo docker ps --format '{{.Names}}|{{.Status}}' 2>/dev/null || "
            "docker ps --format '{{.Names}}|{{.Status}}'")
        containers = []
        for line in docker_raw.split("\n"):
            if "|" in line:
                n, s = line.split("|", 1)
                containers.append({"name": n, "status": s})
        h["containers"] = containers

        print("  Health data collected")
    except Exception as e:
        print(f"  Health collection error: {e}")

    ssh.close()
    return h


def get_error_analysis(yesterday):
    """通过 SSH 查询数据库中的错误日志"""
    if not SSH_PASSWORD:
        return None

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SSH_HOST, username=SSH_USER, password=SSH_PASSWORD, timeout=15)
    except Exception as e:
        print(f"  SSH for error analysis failed: {e}")
        return None

    errors = {}
    try:
        # 查询当天失败的请求 (status != 'success' 或 error 不为空)
        sql_error_count = (
            f"SELECT COUNT(*) FROM usage_logs "
            f"WHERE created_at::date = '{yesterday}' "
            f"AND (status != 'success' OR error_message IS NOT NULL AND error_message != '')"
        )
        err_count_raw = ssh_exec(ssh,
            f'docker exec sub2api-postgres psql -U sub2api -d sub2api -t -A -c "{sql_error_count}"')
        errors["total_errors"] = int(err_count_raw) if err_count_raw.isdigit() else 0

        # 按错误类型分组
        sql_error_types = (
            f"SELECT COALESCE(status, 'unknown'), COUNT(*) FROM usage_logs "
            f"WHERE created_at::date = '{yesterday}' "
            f"AND (status != 'success' OR error_message IS NOT NULL AND error_message != '') "
            f"GROUP BY status ORDER BY COUNT(*) DESC LIMIT 10"
        )
        types_raw = ssh_exec(ssh,
            f'docker exec sub2api-postgres psql -U sub2api -d sub2api -t -A -c "{sql_error_types}"')
        error_types = []
        for line in types_raw.split("\n"):
            if "|" in line:
                parts = line.split("|")
                error_types.append({"type": parts[0], "count": int(parts[1])})
        errors["by_type"] = error_types

        # 最近的错误消息 (去重，取最近5条)
        sql_recent = (
            f"SELECT DISTINCT ON (error_message) error_message, model, created_at "
            f"FROM usage_logs "
            f"WHERE created_at::date = '{yesterday}' "
            f"AND error_message IS NOT NULL AND error_message != '' "
            f"ORDER BY error_message, created_at DESC LIMIT 5"
        )
        recent_raw = ssh_exec(ssh,
            f'docker exec sub2api-postgres psql -U sub2api -d sub2api -t -A -c "{sql_recent}"')
        recent_errors = []
        for line in recent_raw.split("\n"):
            if "|" in line:
                parts = line.split("|")
                recent_errors.append({
                    "message": parts[0][:60],
                    "model": parts[1] if len(parts) > 1 else "?",
                    "time": parts[2][-8:] if len(parts) > 2 else ""
                })
        errors["recent"] = recent_errors

        # 成功率
        sql_total = (
            f"SELECT COUNT(*) FROM usage_logs "
            f"WHERE created_at::date = '{yesterday}'"
        )
        total_raw = ssh_exec(ssh,
            f'docker exec sub2api-postgres psql -U sub2api -d sub2api -t -A -c "{sql_total}"')
        total_db = int(total_raw) if total_raw.isdigit() else 0
        errors["total_requests"] = total_db
        if total_db > 0:
            errors["success_rate"] = ((total_db - errors["total_errors"]) / total_db) * 100
        else:
            errors["success_rate"] = 100

        print(f"  Error analysis done: {errors['total_errors']} errors found")
    except Exception as e:
        print(f"  Error analysis failed: {e}")

    ssh.close()
    return errors


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

    # ─── Server Health + Error Analysis (via SSH) ──────────
    health = get_server_health()
    error_data = get_error_analysis(yesterday)

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

    # ─── Build Single Message ────────────────────────────────
    def bar(pct, w=8):
        filled = int(pct / 100 * w)
        return "\u2588" * filled + "\u2591" * (w - filled)

    L = [
        f"<b>neo-法恒 每日报告</b> <code>{yesterday}</code>",
        "",
        f"请求<b>{total_req}</b> | Token<b>{fmt_n(total_tokens)}</b> | "
            f"费用<b>{fmt_c(total_cost)}</b>",
        f"响应{avg_dur:.1f}s | Key{len(key_trend)}个 | "
            f"用户{active_users}/{total_users}",
        f"累计{fmt_c(cum_cost)} / {fmt_n(cum_req)}次 | "
            f"运行{uptime_d}天{uptime_h % 24}时",
    ]

    # 模型
    L += ["", "━ <b>模型</b> ━━━━━━━━━━━━━"]
    for m in sorted(model_list, key=lambda x: x.get("cost", 0), reverse=True):
        name = m.get("model", "?")
        mreq = m.get("requests", 0)
        mcost = m.get("cost", 0)
        pct = (mcost / total_cost * 100) if total_cost > 0 else 0
        L.append(f"<code>{name[:18]:18s}</code> {mreq}次 {fmt_c(mcost)} {pct:.0f}%")

    # Key
    L += ["", "━ <b>Key用量</b> ━━━━━━━━━━━"]
    for k in sorted(key_trend, key=lambda x: x.get("requests", 0), reverse=True):
        kname = k.get("key_name", k.get("name", "?"))
        kreq = k.get("requests", 0)
        ktok = k.get("tokens", 0)
        pct = (kreq / total_req * 100) if total_req > 0 else 0
        L.append(f"<code>{kname[:10]:10s}</code> {kreq}次 {fmt_n(ktok)}tok {pct:.0f}%")

    # 分组
    L += ["", "━ <b>分组</b> ━━━━━━━━━━━━━"]
    for g in sorted(group_list, key=lambda x: x.get("cost", 0), reverse=True):
        gname = g.get("group_name", g.get("group", "?"))
        greq = g.get("requests", 0)
        gcost = g.get("cost", 0)
        L.append(f"<code>{gname[:10]:10s}</code> {greq}次 {fmt_c(gcost)}")

    # 用户排名 (top 5)
    L += ["", "━ <b>用户TOP5</b> ━━━━━━━━━━"]
    for i, u in enumerate(user_list[:5], 1):
        email = u.get("email", "?")
        at_pos = email.find("@")
        masked = email[:3] + "***" + email[at_pos:] if at_pos > 3 else email
        L.append(f"{i}. <code>{masked[:18]:18s}</code> {u['requests']}次 {fmt_c(u['cost'])}")

    # 7天趋势
    L += ["", "━ <b>7天趋势</b> ━━━━━━━━━━"]
    max_req_w = max((d.get("requests", 0) for d in weekly), default=1)
    for d in weekly:
        dd = d.get("date", "")[-5:]
        dreq = d.get("requests", 0)
        dcost = d.get("cost", 0)
        blen = int(dreq / max_req_w * 8) if max_req_w > 0 else 0
        b = "\u2588" * blen + "\u2591" * (8 - blen)
        mark = "\u25c0" if dd == yesterday[-5:] else ""
        L.append(f"<code>{dd} {b}</code> {dreq}次 {fmt_c(dcost)}{mark}")

    # 上游账号
    acct_ok = sum(1 for a in accounts if a.get("status") == "active")
    acct_total = len(accounts)
    L += ["", "━ <b>上游账号</b> ━━━━━━━━━━"]
    for a in accounts:
        name = a.get("name", "?")
        dot = "+" if a.get("status") == "active" else "!"
        st = "正常" if a.get("status") == "active" else "异常"
        err = a.get("error_message", "")
        extra = f" {err[:20]}" if err else ""
        L.append(f"[{dot}] {name}: {st}{extra}")

    # 高峰时段
    if peak_h:
        L.append(f"\n高峰: {peak_h}({peak_req_h}次) | 最贵: {peak_cost_h}({fmt_c(peak_cost_v)})")

    # 服务器健康
    if health:
        L += ["", "━ <b>服务器</b> ━━━━━━━━━━━━"]
        L.append(f"CPU <code>{bar(health.get('cpu', 0))}</code>{health.get('cpu', 0):.1f}% | "
                 f"内存 <code>{bar(health.get('mem_pct', 0))}</code>{health.get('mem_pct', 0):.0f}%")
        L.append(f"磁盘<code>{bar(health.get('disk_pct', 0))}</code>"
                 f"{health.get('disk_used', '?')}/{health.get('disk_total', '?')} | "
                 f"负载{health.get('load', 0):.2f}")
        if health.get("containers"):
            for c in health["containers"]:
                dot = "+" if "up" in c["status"].lower() else "!"
                L.append(f"[{dot}] {c['name']}: {c['status'][:30]}")

    # 错误分析
    if error_data and error_data.get("total_errors", 0) > 0:
        L += ["", "━ <b>错误</b> ━━━━━━━━━━━━━"]
        L.append(f"成功率<b>{error_data.get('success_rate', 100):.1f}%</b> | "
                 f"错误{error_data['total_errors']}/{error_data.get('total_requests', 0)}")
        for et in (error_data.get("by_type") or [])[:5]:
            L.append(f"  {et['type']}: {et['count']}次")
        for re_item in (error_data.get("recent") or [])[:3]:
            L.append(f"  <code>{re_item.get('time', '')}</code> "
                     f"{re_item.get('model', '?')[:12]}: {re_item.get('message', '')[:35]}")
    elif error_data:
        L.append(f"\n成功率 <b>100%</b> (无错误)")

    L.append(f"\n<i>{now.strftime('%Y-%m-%d %H:%M')} CST</i>")

    # ─── Send ────────────────────────────────────────────────
    msg = "\n".join(L)
    print(f"  Message length: {len(msg)} chars")

    # 如果超过4096字符，截断并标注
    if len(msg) > 4090:
        msg = msg[:4080] + "\n..."
        print(f"  Truncated to {len(msg)} chars")

    r = tg_send(msg)
    if r.get("ok"):
        print("Done: message sent.")
        return 0
    else:
        print(f"  FAILED: {r}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
