<sub>[⬅ All missions](../README.md) · [⬅ AM02 The Case of the Misrouted Cargo Droids](../AM02-gateway-tool-routing/README.md) · [AM04 The Forgetful Flight Computer ➡](../AM04-agentcore-memory/README.md)</sub>

<p align="center"><img src="assets/mission-banner.png" alt="Mission C — The Vanishing Starport Manuals" width="100%"></p>

# AM03 · Mission C: The Vanishing Starport Manuals — After-Class Runbook

> 🚨 The manuals exist, but the flight controller can't answer from them: the specialist was never deployed and the document library never connected.

| | |
|---|---|
| **You'll practise** | Bedrock Knowledge Bases on S3 Vectors, Titan embeddings, a second AgentCore runtime, agent-to-agent delegation |
| **Fix time** | about 60 minutes |
| **Deploy time** | about 2½ min broken · about 3 min solution (it also embeds the manuals) |
| **Cost** | Cents (Titan embeddings for three short manuals, S3 Vectors storage). **Never** let the knowledge-base wizard create an OpenSearch Serverless collection. |
| **Files here** | [`HANDOUT.md`](HANDOUT.md) (the brief, no answers) · [`SOLUTION.md`](SOLUTION.md) (the answer key) · `student-terraform/` (broken) · `student-terraform-solution/` (fixed) |

New to the loop? [02-RUN-A-MISSION.md](../02-RUN-A-MISSION.md) explains every step in detail. Below are the exact commands for this mission. Replace `jsmith42` with your id everywhere.

## ① Deploy the broken environment

```bash
cd AM03-knowledge-base-specialist/student-terraform
terraform init
terraform apply -var 'student_id=jsmith42'
```

## ② Load your values

Run this from `student-terraform/` (needs `jq`). It fills every variable that [SOLUTION.md](SOLUTION.md)'s CLI uses, so its commands work as written:

```bash
ME=jsmith42                                                   # your student_id
KB_JSON=$(terraform output -json solution_resources_kb)
KB_ROLE=$(echo "$KB_JSON" | jq -r .KnowledgeBaseRoleArn)
INDEX_ARN=$(echo "$KB_JSON" | jq -r .VectorIndexArn)
BUCKET=$(echo "$KB_JSON" | jq -r .KnowledgeBaseBucketName)
SPEC_ROLE=$(echo "$KB_JSON" | jq -r .KBSpecialistRoleArn)
DISC=$(terraform output -raw cognito_discovery_url)
CLIENT=$(terraform output -raw m2m_client_ids)
RT_ID=$(terraform output -raw orchestrator_runtime_ids)
CHAT=$(terraform output -raw chat_urls)
echo "chat console: $CHAT"
```

<details><summary><b>Every output of this stack</b> (the handout's <code>name[&lt;you&gt;]</code> is just <code>terraform output</code> here)</summary>

| Output | What it is | Print it |
|---|---|---|
| `chat_urls` | OrbitOps chat console URL (open in a browser; GET /health shows the config state). | `terraform output -raw chat_urls` |
| `chat_function_names` | Chat handler Lambda name. | `terraform output -raw chat_function_names` |
| `orchestrator_runtime_arns` | Orchestrator AgentCore Runtime ARN. | `terraform output -raw orchestrator_runtime_arns` |
| `orchestrator_runtime_ids` | Orchestrator AgentCore Runtime id. | `terraform output -raw orchestrator_runtime_ids` |
| `cognito_user_pool_id` | Shared Cognito user pool id. | `terraform output -raw cognito_user_pool_id` |
| `cognito_domain` | Cognito hosted domain (token endpoint is https://<domain>/oauth2/token). | `terraform output -raw cognito_domain` |
| `cognito_discovery_url` | OIDC discovery URL used by every JWT authorizer. | `terraform output -raw cognito_discovery_url` |
| `m2m_client_ids` | Machine-to-machine app client id. | `terraform output -raw m2m_client_ids` |
| `m2m_client_secrets` | Machine-to-machine app client secret (sensitive). | `terraform output -raw m2m_client_secrets` |
| `tool_function_arns` | Tool Lambda ARN and domain. | `terraform output -json tool_function_arns` |
| `code_bucket` | Shared S3 bucket holding agent zips, tool schemas and manuals. | `terraform output -raw code_bucket` |
| `quality_schema_s3_uri` | S3 URI of the quality tool schema (used when creating quality-target). | `terraform output -raw quality_schema_s3_uri` |
| `solution_resources_kb` | Mission C 'Solution resources': everything a student needs to build the knowledge base and specialist. | `terraform output -json solution_resources_kb` |

</details>

## ③ Confirm it's broken

```bash
python3 ../../tools/flight_test.py .
```

**Expect:** 3 of 4 checks fail. The reply says no manuals specialist is connected (`specialist_configured=False`), so the question is never delegated. Open the chat URL in a browser too, and read the trace yourself.

## ④ Fix it

- **Practise for real:** open [HANDOUT.md](HANDOUT.md), work the objectives with the hint ladder, and keep SOLUTION.md closed.
- **Follow along:** open [SOLUTION.md](SOLUTION.md) **§6 Step-by-step solution**. Console steps work as written; for the CLI, run the block in ② first.

## ⑤ Prove it's fixed

```bash
python3 ../../tools/flight_test.py .
```

The Flight Test checks that:

- the specialist is configured
- the orchestrator delegates via `consult_manuals`
- the answer cites the manuals (72-hour cycle counts)
- no warnings

It exits `0` with **Mission accomplished** when everything passes.

## ⑥ Compare with the solution

```bash
cd ../student-terraform-solution
terraform init
terraform apply -var 'student_id=jsmith42' -var 'course_prefix=orbitsol'
python3 ../../tools/flight_test.py .                  # passes out of the box
diff ../student-terraform/main.tf main.tf             # every fix, as code
```

<details><summary><b>Spoiler:</b> every fault and its fix, in one list</summary>

1. **Fault 1, no knowledge base:** create one on the *existing* S3 Vectors index (`bedrock-knowledge-base-index`, Titan Text Embeddings V2, 1024 dimensions) with the `docs/` S3 data source, then **sync** it.
2. **Fault 2, no specialist:** deploy the `kb_specialist` AgentCore runtime from the provided zip, with `KNOWLEDGE_BASE_ID` set and the same JWT authorizer as the orchestrator.
3. **Fault 3, no delegation:** set `KB_SPECIALIST_RUNTIME_ARN` on the orchestrator runtime.

</details>

## ⑦ Clean up

**Things you created by hand:**

Delete these **before** `terraform destroy`. The knowledge base keeps the vector bucket in use, and destroy fails without this step:

1. **Bedrock → Knowledge Bases →** your `orbit-<you>-am03-kb` → **Delete** (this also deletes its data source).
2. **Bedrock AgentCore → Runtime →** your `<you>_kb_specialist` → **Delete**.

CLI (AWS CLI 2.30+):

```bash
KB=$(aws bedrock-agent list-knowledge-bases --query "knowledgeBaseSummaries[?contains(name, '$ME')].knowledgeBaseId" --output text)
for id in $KB; do aws bedrock-agent delete-knowledge-base --knowledge-base-id "$id"; done
SPEC=$(aws bedrock-agentcore-control list-agent-runtimes --query "agentRuntimes[?contains(agentRuntimeName, '${ME}_kb')].agentRuntimeId" --output text)
for id in $SPEC; do aws bedrock-agentcore-control delete-agent-runtime --agent-runtime-id "$id"; done
```

**Then destroy both stacks**, with the same flags you applied with:

```bash
# from the repo root
cd AM03-knowledge-base-specialist/student-terraform-solution && terraform destroy -var 'student_id=jsmith42' -var 'course_prefix=orbitsol'
cd ../student-terraform              && terraform destroy -var 'student_id=jsmith42'
python3 ../../tools/find_leftovers.py jsmith42        # should find nothing
```

<sub>[⬅ All missions](../README.md) · [⬅ AM02 The Case of the Misrouted Cargo Droids](../AM02-gateway-tool-routing/README.md) · [AM04 The Forgetful Flight Computer ➡](../AM04-agentcore-memory/README.md)</sub>
