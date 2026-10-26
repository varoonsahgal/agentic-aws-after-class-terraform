#!/usr/bin/env python3
"""List anything the OrbitOps missions left behind in your account (read-only).

    python3 tools/find_leftovers.py                 # everything with 'orbit' in it, us-west-2
    python3 tools/find_leftovers.py jsmith42        # only resources carrying your id
    python3 tools/find_leftovers.py jsmith42 --region us-east-1

Run it after `terraform destroy`. It deletes nothing: it prints what it found and the
console page or command to remove it. Things you created by hand during a mission
(app clients aside) are never in Terraform state, so destroy cannot remove them.
"""
import sys

import boto3

args = [a for a in sys.argv[1:] if not a.startswith("--")]
REGION = sys.argv[sys.argv.index("--region") + 1] if "--region" in sys.argv else "us-west-2"
if "--region" in sys.argv:
    args = [a for a in args if a != REGION]
NEEDLE = args[0].lower() if args else "orbit"
s = boto3.session.Session(region_name=REGION)
found = 0


def show(kind, items, how):
    global found
    items = [i for i in items if NEEDLE in str(i).lower()]
    if not items:
        return
    found += len(items)
    print(f"\n● {kind} ({len(items)})")
    for i in items:
        print(f"    {i}")
    print(f"    → {how}")


def safe(fn, default=()):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        print(f"  (skipped: {type(e).__name__}: {str(e)[:120]})")
        return default


print(f"Looking for '{NEEDLE}' in {REGION} …")
ac = s.client("bedrock-agentcore-control")
show("AgentCore runtimes", safe(lambda: [f"{r['agentRuntimeName']}  ({r['agentRuntimeId']}, {r['status']})" for r in ac.list_agent_runtimes(maxResults=100)["agentRuntimes"]]),
     "Bedrock AgentCore → Runtime → select → Delete   ·   aws bedrock-agentcore-control delete-agent-runtime --agent-runtime-id <id>")
show("AgentCore gateways", safe(lambda: [f"{g['name']}  ({g['gatewayId']})" for g in ac.list_gateways(maxResults=100)["items"]]),
     "delete its targets first, then the gateway   ·   aws bedrock-agentcore-control delete-gateway --gateway-identifier <id>")
show("AgentCore memories (AM04)", safe(lambda: [f"{m['id']}  ({m.get('status')})" for m in ac.list_memories(maxResults=100)["memories"]]),
     "Bedrock AgentCore → Memory → Delete   ·   aws bedrock-agentcore-control delete-memory --memory-id <id>")
ba = s.client("bedrock-agent")
show("Knowledge bases (AM03, AM05)", safe(lambda: [f"{k['name']}  ({k['knowledgeBaseId']})" for k in ba.list_knowledge_bases(maxResults=100)["knowledgeBaseSummaries"]]),
     "Bedrock → Knowledge Bases → Delete   ·   aws bedrock-agent delete-knowledge-base --knowledge-base-id <id>   (a KB blocks deleting its vector bucket)")
show("Guardrails (AM06)", safe(lambda: [f"{g['name']}  ({g['id']})" for g in s.client("bedrock").list_guardrails(maxResults=100)["guardrails"]]),
     "Bedrock → Guardrails → Delete   ·   aws bedrock delete-guardrail --guardrail-identifier <id>")
show("S3 Vectors buckets (AM03, AM05)", safe(lambda: [b["vectorBucketName"] for b in s.client("s3vectors").list_vector_buckets(maxResults=100)["vectorBuckets"]]),
     "re-run terraform destroy once the knowledge base is gone")
show("S3 buckets", safe(lambda: [b["Name"] for b in s.client("s3").list_buckets()["Buckets"]]),
     "re-run terraform destroy (the code bucket is force-destroyed by Terraform)")
show("Lambda functions", safe(lambda: [f["FunctionName"] for p in s.client("lambda").get_paginator("list_functions").paginate() for f in p["Functions"]]),
     "re-run terraform destroy")
show("Cognito user pools", safe(lambda: [f"{p['Name']}  ({p['Id']})" for p in s.client("cognito-idp").list_user_pools(MaxResults=60)["UserPools"]]),
     "re-run terraform destroy (it deletes the pool with every app client in it)")
ec2 = s.client("ec2")
vpcs = safe(lambda: ec2.describe_vpcs(Filters=[{"Name": "tag:Module", "Values": ["am05"]}])["Vpcs"], [])
vpc_names = [f"{next((t['Value'] for t in v.get('Tags', []) if t['Key'] == 'Name'), '')}  ({v['VpcId']})" for v in vpcs]
show("VPCs (AM05)", vpc_names, "delete your interface endpoints first, then re-run terraform destroy")
for v in vpcs:
    eps = safe(lambda: ec2.describe_vpc_endpoints(Filters=[{"Name": "vpc-id", "Values": [v["VpcId"]]}, {"Name": "vpc-endpoint-type", "Values": ["Interface"]}])["VpcEndpoints"], [])
    label = next((t["Value"] for t in v.get("Tags", []) if t["Key"] == "Name"), v["VpcId"])
    show(f"Interface endpoints in {label} (billed hourly!)", [f"{e['ServiceName']}  ({e['VpcEndpointId']})  {label}" for e in eps],
         "VPC → Endpoints → select → Actions → Delete   ·   aws ec2 delete-vpc-endpoints --vpc-endpoint-ids <ids>")
    enis = safe(lambda: ec2.describe_network_interfaces(Filters=[{"Name": "vpc-id", "Values": [v["VpcId"]]}])["NetworkInterfaces"], [])
    show(f"Network interfaces still in {label}", [f"{n['NetworkInterfaceId']}  {n.get('Description', '')[:60]}  {label}" for n in enis],
         "AgentCore releases its runtime ENIs on its own, sometimes hours later; re-run terraform destroy then")
logs = s.client("logs")
show("CloudWatch log groups", safe(lambda: [g["logGroupName"] for p in logs.get_paginator("describe_log_groups").paginate() for g in p["logGroups"]
                                            if "/aws/lambda/" in g["logGroupName"] or "/aws/bedrock-agentcore/" in g["logGroupName"]]),
     "harmless and nearly free, but you can delete them: CloudWatch → Log groups → Delete")

print("\nNothing left behind. 🎉" if not found else f"\n{found} item(s) found. Delete the ones that are yours.")
