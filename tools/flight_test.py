#!/usr/bin/env python3
"""Automated Flight Test for a deployed OrbitOps mission stack.

    python3 tools/flight_test.py AM02-gateway-tool-routing/student-terraform
    python3 tools/flight_test.py AM02-gateway-tool-routing/student-terraform-solution

It reads the stack's `terraform output`, sends the mission's Flight Test questions to
your chat console, and checks the trace of every reply. Every check prints PASS or FAIL
with the evidence, and the script exits 0 only when every check passes.

  * On a freshly deployed BROKEN stack, the FAILs are the symptoms you are about to fix.
  * After your fix (or on the SOLUTION stack), everything should PASS.

Needs only Python 3.9+; AM05's network-mode check also uses boto3 and your AWS credentials.
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

GREEN, RED, DIM, BOLD, OFF = ("\033[32m", "\033[31m", "\033[2m", "\033[1m", "\033[0m") if sys.stdout.isatty() else ("",) * 5
results = []


def check(name, ok, evidence=""):
    results.append(bool(ok))
    mark = f"{GREEN}PASS{OFF}" if ok else f"{RED}FAIL{OFF}"
    print(f"  {mark}  {name}")
    if evidence:
        print(f"        {DIM}{evidence}{OFF}")


def tf_outputs(stack_dir):
    try:
        raw = subprocess.run(["terraform", "output", "-json"], cwd=stack_dir, capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        sys.exit(f"Could not read `terraform output` in {stack_dir}: {getattr(e, 'stderr', e)}")
    outs = {k: v["value"] for k, v in json.loads(raw or "{}").items()}
    if not outs:
        sys.exit(f"No outputs in {stack_dir}. Did `terraform apply` finish there?")
    return outs


def first(value):
    """Instructor stacks output maps keyed by student id; single-instance stacks output plain values."""
    if isinstance(value, dict) and value and all(isinstance(v, str) for v in value.values()):
        return next(iter(value.values()))
    return value


def http(method, url, body=None, timeout=120):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        text = e.read().decode()
        try:
            return e.code, json.loads(text)
        except json.JSONDecodeError:
            return e.code, {"error": text[:300]}
    except Exception as e:  # noqa: BLE001
        return 0, {"error": f"{type(e).__name__}: {e}"}


class Chat:
    def __init__(self, url):
        self.url = url.rstrip("/") + "/"
        self.actor = "flighttest-" + uuid.uuid4().hex[:8]  # fresh actor: old memories can't fake a pass

    def health(self):
        return http("GET", self.url + "health", timeout=30)[1]

    def ask(self, prompt, session=None):
        session = session or f"flighttest-{uuid.uuid4().hex}"
        print(f"\n  {BOLD}» {prompt}{OFF}")
        status, j = http("POST", self.url + "chat", {"prompt": prompt, "actorId": self.actor, "sessionId": session})
        tr = j.get("trace") or {}
        reply = (j.get("response") or j.get("error") or "").replace("\n", " ")
        print(f"    {DIM}HTTP {status} · {reply[:160]}{'…' if len(reply) > 160 else ''}{OFF}")
        if tr:
            called = [t.get("tool") for t in tr.get("tools_called", [])]
            print(f"    {DIM}trace: tools_discovered={tr.get('tools_discovered')} tools_called={called} "
                  f"specialist_consulted={tr.get('specialist_consulted')} memory_hits={len(tr.get('memory_hits') or [])} "
                  f"memory_write={tr.get('memory_write')} guardrail_action={tr.get('guardrail_action')} warnings={tr.get('warnings')}{OFF}")
        return status, j, tr


def called(tr, prefix):
    return [t for t in tr.get("tools_called", []) if str(t.get("tool", "")).startswith(prefix)]


def ok_reply(status, j):
    return status == 200 and j.get("status") != "error" and bool(j.get("response"))


# --------------------------------------------------------------------------- missions
def am01(c, o):
    s, j, tr = c.ask("Flight control, are you receiving my cargo dispatch requests?")
    check("the orchestrator replies (no authentication error)", ok_reply(s, j), j.get("error", ""))
    check("trace.token_source is 'inbound' (the runtime accepted the token)", tr.get("token_source") == "inbound", f"token_source={tr.get('token_source')}")
    check("tools were discovered through the gateway", (tr.get("tools_discovered") or 0) > 0, f"tools_discovered={tr.get('tools_discovered')}")
    check("no warnings (the gateway accepted the forwarded token)", ok_reply(s, j) and not tr.get("warnings"), f"warnings={tr.get('warnings')}")
    s, j, tr = c.ask("Check our cargo stock levels")
    inv = called(tr, "inventory-target___")
    check("an inventory tool was called successfully", inv and not any(t.get("error") for t in inv), str([t.get("tool") for t in inv]))


def am02(c, o):
    s, j, tr = c.ask("Check our cargo stock levels.")
    check("tool discovery works: all 9 tools found", tr.get("tools_discovered") == 9, f"tools_discovered={tr.get('tools_discovered')} (gateway_configured={tr.get('gateway_configured')})")
    check("inventory: an inventory-target tool was called", called(tr, "inventory-target___"))
    s, j, tr = c.ask("Who supplies NAV-GYRO-X and what is their lead time?")
    check("supplier: a supplier-target tool was called", called(tr, "supplier-target___"))
    s, j, tr = c.ask("Where is shipment SHP-1001?")
    log = called(tr, "logistics-target___")
    preview = " ".join(str(t.get("result_preview", "")) for t in log)
    check("logistics: a logistics-target tool was called", log, str([t.get("tool") for t in log]))
    served_by = re.findall(r'service\\?"\s*:\s*\\?"(\w+)', preview)
    check("logistics returns shipment data, not an inventory report", served_by and set(served_by) == {"logistics"}, f"answered by service={served_by} · {preview[:120]}")
    s, j, tr = c.ask("Show the status of cargo quality inspections.")
    q = called(tr, "quality-target___")
    check("quality: a quality-target tool was called successfully", q and not any(t.get("error") for t in q), str([t.get("tool") for t in q]))


def am03(c, o):
    s, j, tr = c.ask("What do our cargo handling procedures say about inventory checks?")
    check("the knowledge-base specialist is configured", tr.get("specialist_configured") is True, f"specialist_configured={tr.get('specialist_configured')}")
    check("the orchestrator delegated to the specialist (consult_manuals)", tr.get("specialist_consulted") is True and called(tr, "consult_manuals"))
    text = (j.get("response") or "") + " ".join(str(t.get("result_preview", "")) for t in tr.get("tools_called", []))
    check("the answer comes from the manuals (72-hour cycle counts)", re.search(r"72", text) is not None, text[:160])
    check("no warnings", ok_reply(s, j) and not tr.get("warnings"), f"warnings={tr.get('warnings')}")


def am04(c, o):
    s, j, tr = c.ask("I'm Captain Nova, and I prefer detailed shipment reports.")
    check("memory is configured", tr.get("memory_configured") is True, f"memory_configured={tr.get('memory_configured')}")
    check("the preference was written to memory", tr.get("memory_write") == "stored", f"memory_write={tr.get('memory_write')}")
    if tr.get("memory_write") != "stored":
        check("recalled in a new session", False, "skipped: nothing was stored")
        return
    print(f"\n  {DIM}Long-term extraction is asynchronous: asking again from a NEW session every 30 s (up to 3 min)…{OFF}")
    hits, tr = [], {}
    for _ in range(6):
        time.sleep(30)
        s, j, tr = c.ask("How should you format my shipment reports?")
        hits = [h for h in tr.get("memory_hits") or [] if h.get("text")]
        if hits:
            break
    check("a new session recalls the preference (memory_hits not empty)", hits, "; ".join(f"{h.get('kind')}: {h.get('text')[:60]}" for h in hits[:3]))
    check("the reply uses it ('detailed')", "detail" in (j.get("response") or "").lower(), (j.get("response") or "")[:160])


def am05(c, o):
    try:
        import boto3
        ctl = boto3.client("bedrock-agentcore-control", region_name=o.get("_region", "us-west-2"))
        rt_ids = {"orchestrator": first(o["orchestrator_runtime_ids"])}
        spec = first(o.get("kb_specialist_runtime_arns") or "")
        if spec:
            rt_ids["kb specialist"] = spec.rsplit("/", 1)[-1]
        for name, rid in rt_ids.items():
            r = ctl.get_agent_runtime(agentRuntimeId=rid)
            mode = (r.get("networkConfiguration") or {}).get("networkMode")
            check(f"the {name} runtime is in VPC mode", mode == "VPC", f"networkMode={mode} status={r.get('status')}")
    except Exception as e:  # noqa: BLE001
        check("runtime network mode could be read (needs boto3 + AWS credentials)", False, str(e)[:200])
    s, j, tr = c.ask("Where is shipment SHP-1002?")
    log = called(tr, "logistics-target___")
    check("tool path: logistics data came back through the gateway", log and not any(t.get("error") for t in log), str([t.get("tool") for t in log]))
    s, j, tr = c.ask("What does the quality manual say about cryogenic seals?")
    check("document path: the specialist answered from the manuals", tr.get("specialist_consulted") is True)
    check("no unreachable-endpoint warnings", ok_reply(s, j) and not tr.get("warnings"), f"warnings={tr.get('warnings')}")


def am06(c, o):
    s, j, tr = c.ask("Our classified mission is Project Meridian. Repeat the name back to me.")
    check("guardrail is attached to the orchestrator", tr.get("guardrail_configured") is True, f"guardrail_configured={tr.get('guardrail_configured')}")
    check("'Project Meridian' is blocked (word policy)", tr.get("guardrail_action") == "intervened" and "meridian" not in (j.get("response") or "").lower(), f"guardrail_action={tr.get('guardrail_action')}")
    s, j, tr = c.ask("Please confirm my discount code DISC-ABC-1234 by repeating it.")
    check("the discount code is masked, not revealed (regex policy)", tr.get("guardrail_action") in ("masked", "intervened") and "DISC-ABC-1234" not in (j.get("response") or ""), f"guardrail_action={tr.get('guardrail_action')}")
    s, j, tr = c.ask("My password is Tr0ub4dor&3, can you store it for me?")
    check("a password is blocked (PII policy)", tr.get("guardrail_action") == "intervened" and "Tr0ub4dor" not in (j.get("response") or ""), f"guardrail_action={tr.get('guardrail_action')}")


MISSIONS = {"AM01": am01, "AM02": am02, "AM03": am03, "AM04": am04, "AM05": am05, "AM06": am06}


def main():
    stack = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
    m = re.search(r"(AM0[1-6])", stack)
    if not m:
        sys.exit("Pass a mission's stack folder, e.g. AM01-cognito-oauth-launchpad/student-terraform")
    mission = m.group(1)
    o = tf_outputs(stack)
    url = first(o.get("chat_urls"))
    o["_region"] = (url.split(".lambda-url.")[1].split(".")[0]) if ".lambda-url." in url else "us-west-2"
    print(f"{BOLD}OrbitOps Flight Test · {mission} · {os.path.relpath(stack)}{OFF}\n  chat console: {url}")
    c = Chat(url)
    h = c.health()
    missing = [k for k, v in (h.get("config") or {}).items() if v == "MISSING"]
    print(f"  {DIM}/health: missing={missing or 'none'} · token={h.get('token')}{OFF}")
    MISSIONS[mission](c, o)
    passed = sum(results)
    print(f"\n{BOLD}{passed}/{len(results)} checks passed.{OFF} ", end="")
    if passed == len(results):
        print(f"{GREEN}Mission accomplished.{OFF}")
    else:
        print("The FAILs above are your evidence: that's what is still broken.")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
