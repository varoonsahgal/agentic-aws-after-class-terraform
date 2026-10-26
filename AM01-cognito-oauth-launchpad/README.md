<sub>[⬅ All missions](../README.md) · [AM02 The Case of the Misrouted Cargo Droids ➡](../AM02-gateway-tool-routing/README.md)</sub>

<p align="center"><img src="assets/mission-banner.png" alt="Mission A — The Locked Launchpad" width="100%"></p>

# AM01 · Mission A: The Locked Launchpad — After-Class Runbook

> 🚨 The chat console can't reach its AI flight controller: every message ends with **Authentication service unavailable**.

| | |
|---|---|
| **You'll practise** | Cognito OAuth 2.0 machine-to-machine, AgentCore JWT authorizers, Lambda configuration |
| **Fix time** | about 40 minutes |
| **Deploy time** | about 2½ min for either stack (plus ~1 min for the first `terraform init`) |
| **Cost** | Cents. Nothing bills by the hour. |
| **Files here** | [`HANDOUT.md`](HANDOUT.md) (the brief, no answers) · [`SOLUTION.md`](SOLUTION.md) (the answer key) · `student-terraform/` (broken) · `student-terraform-solution/` (fixed) |

New to the loop? [02-RUN-A-MISSION.md](../02-RUN-A-MISSION.md) explains every step in detail. Below are the exact commands for this mission. Replace `jsmith42` with your id everywhere.

## ① Deploy the broken environment

```bash
cd AM01-cognito-oauth-launchpad/student-terraform
terraform init
terraform apply -var 'student_id=jsmith42'
```

## ② Load your values

Run this from `student-terraform/` (needs `jq`). It fills every variable that [SOLUTION.md](SOLUTION.md)'s CLI uses, so its commands work as written:

```bash
ME=jsmith42                                                   # your student_id
POOL=$(terraform output -raw cognito_user_pool_id)
GW_ID=$(terraform output -raw gateway_ids)
RT_ID=$(terraform output -raw orchestrator_runtime_ids)
FN=$(terraform output -raw chat_function_names)
CHAT=$(terraform output -raw chat_urls)
RUNTIME_ARN=$(terraform output -raw orchestrator_runtime_arns)  # the guide's <runtime arn>
DOMAIN_HOST=$(terraform output -raw cognito_domain)            # the guide's <domain host>
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
| `legacy_client_ids` | The unusable (public, no-secret) app client id. | `terraform output -raw legacy_client_ids` |
| `tool_function_arns` | Tool Lambda ARN and domain. | `terraform output -json tool_function_arns` |
| `code_bucket` | Shared S3 bucket holding agent zips, tool schemas and manuals. | `terraform output -raw code_bucket` |
| `quality_schema_s3_uri` | S3 URI of the quality tool schema (used when creating quality-target). | `terraform output -raw quality_schema_s3_uri` |
| `gateway_urls` | AgentCore Gateway MCP endpoint (value for GATEWAY_URL). | `terraform output -raw gateway_urls` |
| `gateway_ids` | AgentCore Gateway id. | `terraform output -raw gateway_ids` |

</details>

## ③ Confirm it's broken

```bash
python3 ../../tools/flight_test.py .
```

**Expect:** 0 of 5 checks pass: every message gets HTTP 503 *Authentication service unavailable*, and `/health` lists five `MISSING` values. Open the chat URL in a browser too, and read the trace yourself.

## ④ Fix it

- **Practise for real:** open [HANDOUT.md](HANDOUT.md), work the objectives with the hint ladder, and keep SOLUTION.md closed.
- **Follow along:** open [SOLUTION.md](SOLUTION.md) **§6 Step-by-step solution**. Console steps work as written; for the CLI, run the block in ② first.

## ⑤ Prove it's fixed

```bash
python3 ../../tools/flight_test.py .
```

The Flight Test checks that:

- the orchestrator replies
- `token_source` is `inbound`
- tools are discovered through the gateway
- no warnings
- an inventory tool is called successfully

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

1. **Fault 1, no M2M client:** create a *confidential* Cognito app client (with a secret) that allows the `client_credentials` grant and the `supplychain/read` + `supplychain/write` scopes.
2. **Fault 2, wrong trust list:** put that client's id in **allowed clients** on *both* JWT authorizers, the gateway's and the orchestrator runtime's.
3. **Fault 3, wiped config:** give the chat-handler Lambda its five environment variables (`ORCHESTRATOR_RUNTIME_ARN`, `COGNITO_DOMAIN`, `COGNITO_CLIENT_ID`, `COGNITO_CLIENT_SECRET`, `COGNITO_USER_POOL_ID`).

</details>

## ⑦ Clean up

**Things you created by hand:**

The **M2M app client** you create lives inside the user pool that Terraform owns, so `terraform destroy` deletes it with the pool. Nothing to delete by hand.

**Then destroy both stacks**, with the same flags you applied with:

```bash
# from the repo root
cd AM01-cognito-oauth-launchpad/student-terraform-solution && terraform destroy -var 'student_id=jsmith42' -var 'course_prefix=orbitsol'
cd ../student-terraform              && terraform destroy -var 'student_id=jsmith42'
python3 ../../tools/find_leftovers.py jsmith42        # should find nothing
```

<sub>[⬅ All missions](../README.md) · [AM02 The Case of the Misrouted Cargo Droids ➡](../AM02-gateway-tool-routing/README.md)</sub>
