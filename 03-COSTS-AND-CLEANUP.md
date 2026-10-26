<sub>[⬅ 02-RUN-A-MISSION](02-RUN-A-MISSION.md) · [Back to the kit](README.md) · Next: [04-TROUBLESHOOTING ➡](04-TROUBLESHOOTING.md)</sub>

# 03 · Costs and Cleanup

Everything in these missions is **pay-per-use and close to $0 when idle**, with one exception: **AM05's VPC interface endpoints bill by the hour.** Running every mission once, broken and solution, typically costs **well under $5**.

## What costs money

| Item | Missions | Price (us-west-2, approx.) | Idle cost |
|---|---|---|---|
| **VPC interface endpoints** | AM05 | ~$0.01 per endpoint per AZ per hour. The AM05 solution has 5 endpoints × 2 AZs ≈ **$0.10/hour, about $2.40/day** | ⚠️ **yes: destroy AM05 the same day** |
| NAT gateway | AM05, only with `-var enable_nat_gateway=true` (off by default) | ~$0.045/hour + data | ⚠️ yes |
| Amazon Nova 2 Lite tokens | all | fractions of a cent per chat message | no |
| AgentCore Runtime | all | billed only for active seconds while a request is processed | no |
| Cognito M2M token requests | all | ~$0.00225 per token (the chat console caches it for an hour) | no |
| Titan Embeddings + S3 Vectors | AM03, AM05 | cents for the three short manuals | storage: fractions of a cent |
| AgentCore Memory | AM04 | events, extraction and retrieval: cents | no |
| Guardrail evaluations | AM06 | cents | no |
| Lambda, S3, CloudWatch Logs | all | free tier / fractions of a cent (logs are kept for 7 days) | no |

> [!CAUTION]
> **The one expensive mistake:** in AM03 or AM05, letting a console wizard **create a new vector store** for the knowledge base. *Quick create* defaults to **OpenSearch Serverless**, which bills around **$350+/month** until you delete it. Always choose **"Use an existing vector store" → S3 Vectors** and the index the handout names.

## Security: your chat URL is public

The chat console is a Lambda **Function URL with no authentication**. Anyone who learns the URL can chat with your agent, and that costs you model tokens. Don't post it anywhere, and **destroy the stack when you're done** rather than leaving it up for weeks.

## Cleanup, the right way

Terraform deletes **only what Terraform created**. Anything you built by hand while fixing a mission must be deleted by hand, *before* `terraform destroy`, because some of it blocks the destroy:

| Mission | You might have created | Blocks destroy? | Delete it |
|---|---|---|---|
| AM01 | an M2M app client | no: it lives inside the user pool Terraform deletes | nothing to do |
| AM02 | a `quality-target` on your gateway | no: Terraform deletes the gateway with its targets (verified) | nothing to do |
| AM03 | a knowledge base (+ data source) and a `…_kb_specialist` runtime | **yes**: the knowledge base keeps the vector bucket in use | Bedrock → Knowledge Bases → Delete; AgentCore → Runtime → Delete |
| AM04 | an AgentCore memory | no, but it lingers | AgentCore → Memory → Delete |
| AM05 | interface endpoints | **yes**: they keep the subnets and security group in use (and **bill hourly**) | VPC → Endpoints → select yours → Delete |
| AM06 | a guardrail | no, but it lingers | Bedrock → Guardrails → Delete |

Then destroy each stack you applied, with the **same `-var` flags**, and check:

```bash
python3 tools/find_leftovers.py jsmith42      # from the repo root
```

It lists anything with your id still in the account (runtimes, gateways, memories, knowledge bases, guardrails, vector buckets, Lambdas, user pools, VPCs, endpoints, network interfaces, log groups) with the console page or command that removes it. It deletes nothing itself.

## If `terraform destroy` fails

1. **Read the error**: it names the resource it couldn't delete and, usually, why ("in use", "has dependencies").
2. Delete the hand-made resource that's in the way (table above, or `find_leftovers.py`).
3. Run `terraform destroy` again. It picks up where it stopped.
4. **AM05 solution (or after you fixed AM05): this is expected.** AgentCore keeps a deleted VPC-mode runtime's network interfaces (type `agentic_ai`, *in-use*) in your subnets for a while. Terraform waits about 15 minutes on the security group, then fails with `DependencyViolation`. You can't delete those interfaces yourself, and they cost nothing (the hourly endpoints are already gone by then). Wait, sometimes a few hours, and run the same `terraform destroy` again.

## The morning after

Open **Billing and Cost Management → Bills** (or **Cost Explorer**) the next day. You should see a few cents of Bedrock, and AM05's endpoint hours if you did that mission. Anything else, run `find_leftovers.py` again.
