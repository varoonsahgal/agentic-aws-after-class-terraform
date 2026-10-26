#!/usr/bin/env python3
"""Preflight: is this machine and AWS account ready to deploy the OrbitOps missions?

    python3 tools/preflight.py              # checks us-west-2
    python3 tools/preflight.py --region us-east-1

Read-only, except for two tiny model calls (well under a cent) that prove model access.
Uses your normal AWS credentials (AWS_PROFILE, `aws configure`, SSO, …).
"""
import json
import re
import shutil
import subprocess
import sys

REGION = sys.argv[sys.argv.index("--region") + 1] if "--region" in sys.argv else "us-west-2"
GREEN, YELLOW, RED, DIM, BOLD, OFF = ("\033[32m", "\033[33m", "\033[31m", "\033[2m", "\033[1m", "\033[0m") if sys.stdout.isatty() else ("",) * 6
fails = warns = 0


def report(level, name, detail=""):
    global fails, warns
    tag = {"ok": f"{GREEN}  OK{OFF}", "warn": f"{YELLOW}WARN{OFF}", "fail": f"{RED}FAIL{OFF}"}[level]
    fails += level == "fail"
    warns += level == "warn"
    print(f"  {tag}  {name}" + (f"\n        {DIM}{detail}{OFF}" if detail else ""))


def version_of(cmd, pattern):
    exe = shutil.which(cmd[0])
    if not exe:
        return None
    out = subprocess.run(cmd, capture_output=True, text=True).stdout + subprocess.run(cmd, capture_output=True, text=True).stderr
    m = re.search(pattern, out)
    return tuple(int(x) for x in m.group(1).split(".")) if m else (0,)


print(f"{BOLD}1. Tools on this machine{OFF}")
tf = version_of(["terraform", "version"], r"Terraform v(\d+\.\d+\.\d+)")
report("ok" if tf and tf >= (1, 6) else "fail", f"Terraform >= 1.6 (found {'.'.join(map(str, tf)) if tf else 'none'})",
       "" if tf and tf >= (1, 6) else "Install: https://developer.hashicorp.com/terraform/install")
py = sys.version_info
report("ok" if py >= (3, 10) else "fail", f"Python >= 3.10 (found {py.major}.{py.minor})")
pip_ok = subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True).returncode == 0
report("ok" if pip_ok else "fail", "pip is available (the agent zips are built at plan time)", "" if pip_ok else f"{sys.executable} -m ensurepip --upgrade")
try:
    import boto3
    import botocore
    report("ok", f"boto3 installed ({boto3.__version__})")
except ImportError:
    report("fail", "boto3 installed", f"{sys.executable} -m pip install boto3")
    print(f"\n{RED}Install boto3, then run preflight again.{OFF}")
    sys.exit(1)
aws = version_of(["aws", "--version"], r"aws-cli/(\d+\.\d+\.\d+)")
if not aws:
    report("warn", "AWS CLI v2 (optional: the console works for every mission)", "Install: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html")
else:
    report("ok" if aws >= (2, 30) else "warn", f"AWS CLI >= 2.30 for the solution guides' agentcore commands (found {'.'.join(map(str, aws))})",
           "" if aws >= (2, 30) else "Older CLIs lack `bedrock-agentcore-control` and `s3vectors`: upgrade, or use CloudShell / the console")
report("ok" if shutil.which("jq") else "warn", "jq (used by the solution guides' CLI snippets)", "" if shutil.which("jq") else "brew install jq · apt install jq · winget install jqlang.jq")

print(f"\n{BOLD}2. AWS identity and region ({REGION}){OFF}")
session = boto3.session.Session(region_name=REGION)
try:
    ident = session.client("sts").get_caller_identity()
    report("ok", f"credentials work: {ident['Arn']}", f"account {ident['Account']}")
except Exception as e:  # noqa: BLE001
    report("fail", "AWS credentials", f"{e}  →  run `aws configure` (or `aws configure sso`) and/or export AWS_PROFILE")
    print(f"\n{RED}Fix credentials first.{OFF}")
    sys.exit(1)


def probe(name, fn, hint=""):
    try:
        detail = fn()
        report("ok", name, detail or "")
        return True
    except botocore.exceptions.ClientError as e:
        code = e.response["Error"]["Code"]
        report("fail", name, f"{code}: {e.response['Error'].get('Message', '')[:160]}" + (f"  →  {hint}" if hint else ""))
    except Exception as e:  # noqa: BLE001
        report("fail", name, f"{type(e).__name__}: {str(e)[:160]}" + (f"  →  {hint}" if hint else ""))
    return False


print(f"\n{BOLD}3. Services and model access{OFF}")
perm = "your identity needs the actions in iam/deployer-policy.json"
probe("Bedrock AgentCore control plane", lambda: session.client("bedrock-agentcore-control").list_agent_runtimes(maxResults=1) and "", perm)
probe("Amazon S3 Vectors", lambda: session.client("s3vectors").list_vector_buckets(maxResults=1) and "", perm)
probe("Bedrock Knowledge Bases", lambda: session.client("bedrock-agent").list_knowledge_bases(maxResults=1) and "", perm)
probe("Amazon Cognito", lambda: session.client("cognito-idp").list_user_pools(MaxResults=1) and "", perm)


def nova():
    r = session.client("bedrock-runtime").converse(modelId="us.amazon.nova-2-lite-v1:0", messages=[{"role": "user", "content": [{"text": "Reply with the single word OK."}]}],
                                                   inferenceConfig={"maxTokens": 10})
    return "replied: " + "".join(c.get("text", "") for c in r["output"]["message"]["content"]).strip()[:40]


def titan():
    r = session.client("bedrock-runtime").invoke_model(modelId="amazon.titan-embed-text-v2:0", body=json.dumps({"inputText": "cargo"}))
    return f"{len(json.loads(r['body'].read())['embedding'])}-dimension embedding"


probe("Amazon Nova 2 Lite (us.amazon.nova-2-lite-v1:0) answers", nova, "check model access in the Bedrock console, and that the region is a US region")
probe("Titan Text Embeddings V2 answers (AM03, AM05)", titan, "check model access in the Bedrock console")

print(f"\n{BOLD}4. Quotas{OFF}")
try:
    vpcs = len(session.client("ec2").describe_vpcs()["Vpcs"])
    try:
        quota = int(session.client("service-quotas").get_service_quota(ServiceCode="vpc", QuotaCode="L-F678F1CE")["Quota"]["Value"])
    except Exception:  # noqa: BLE001
        quota = 5
    free = quota - vpcs
    report("ok" if free >= 2 else ("warn" if free == 1 else "fail"), f"VPCs: {vpcs} of {quota} used (AM05 needs 1, or 2 with the solution stack too)")
except Exception as e:  # noqa: BLE001
    report("warn", "VPC quota (only matters for AM05)", str(e)[:160])

print()
if fails:
    print(f"{RED}{BOLD}{fails} check(s) failed.{OFF} Fix them before `terraform apply`; see 04-TROUBLESHOOTING.md.")
elif warns:
    print(f"{YELLOW}{BOLD}Ready, with {warns} warning(s).{OFF} You can deploy; the warnings only affect optional CLI steps.")
else:
    print(f"{GREEN}{BOLD}All clear. You're ready to deploy a mission.{OFF}")
sys.exit(1 if fails else 0)
