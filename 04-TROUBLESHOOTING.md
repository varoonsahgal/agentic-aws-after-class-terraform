<sub>[⬅ 03-COSTS-AND-CLEANUP](03-COSTS-AND-CLEANUP.md) · [Back to the kit](README.md)</sub>

# 04 · Troubleshooting

Find your symptom, apply the fix. If you're not sure where a problem is, run `python3 tools/preflight.py` first: it rules out tools, credentials and model access in one go.

## `terraform init` / `plan` / `apply`

| Symptom | Cause | Fix |
|---|---|---|
| Terraform asks `var.student_id … Enter a value:` (or `No value for required variable`) | no `-var` and no `terraform.tfvars` | Type your id, or add `-var 'student_id=jsmith42'`. There's deliberately no default. |
| `Invalid value for variable` … `student_id` | uppercase, hyphen, or too short/long | 3–12 lowercase letters or digits, e.g. `jsmith42`. |
| `data.external.build` … `exit status 1` / `No module named pip` | Python, pip or boto3 missing (the agent zips are built at plan time) | `python3 -m pip install --upgrade boto3`; on Ubuntu see the venv note in [01-SETUP](01-SETUP.md#step-4--install-the-tools). |
| `NoCredentialProviders` / `no valid credential sources` | Terraform can't find AWS credentials | `aws sts get-caller-identity` must work in the **same terminal**; `export AWS_PROFILE=<name>` if you use profiles; `aws sso login` if SSO expired. |
| `AccessDeniedException` on `bedrock-agentcore`, `bedrock`, `s3vectors`, `iam` … | your identity lacks permissions | Attach [`iam/deployer-policy.json`](iam/deployer-policy.json) (or AdministratorAccess in your own account). |
| `ValidationException` … model / `You don't have access to the model` | Nova 2 Lite or Titan V2 not enabled for your account | Bedrock console → Model access → enable, then `python3 tools/preflight.py`. |
| Cognito `Domain already exists` | you applied the same id + prefix before and didn't destroy it | `terraform destroy` the old one, or use another `course_prefix`. |
| AgentCore runtime `CREATE_FAILED` / role not assumable | IAM changes need a few seconds to propagate | Run `terraform apply` again: it continues where it stopped. |
| `ThrottlingException` / `TooManyRequestsException` on gateway targets | AgentCore control-plane rate limits | Run `terraform apply` again. |
| `VpcLimitExceeded` (AM05) | your region already has 5 VPCs (the default quota) | Delete an unused VPC, or request an increase in **Service Quotas**. |
| `Error acquiring the state lock` | a previous run was interrupted | Make sure no other `terraform` is running, then `terraform force-unlock <ID>`. |
| `timeout while waiting for plugin to start` | the AWS provider is a ~800 MB binary; antivirus / endpoint security (or macOS) scans a freshly downloaded one before it may run, which can take minutes | Wait a few minutes and run the command again. Run one `terraform` at a time (not several stacks in parallel) the first time. If it persists, ask your IT team to allow `terraform-provider-aws`. |

## The chat console and the Flight Test

| Symptom | Cause | Fix |
|---|---|---|
| Flight Test: `No outputs in …` | you're pointing at the wrong folder, or apply didn't finish | Pass the stack folder: `python3 ../../tools/flight_test.py .` from inside `student-terraform/`. |
| Every reply: **⚠ Authentication service unavailable** | expected in **AM01** (that's the mission) | Elsewhere: `terraform apply` again; the stack was changed by hand. |
| HTTP **424** / "Flight controller fault" | the agent code crashed or the runtime is mid-update | Wait for the runtime to show `READY`, then retry. Logs: CloudWatch → `/aws/bedrock-agentcore/runtimes/<runtime id>-DEFAULT`. |
| A fix "did nothing" | runtime updates publish a new version; the old one answers until the new one is `READY` | Wait about a minute and re-test. **One change at a time.** |
| AM04 recall fails right after storing | long-term memory extraction is asynchronous (30–90 s, sometimes more) | The Flight Test retries for 3 minutes. By hand: wait, then ask from a **New session** with the **same actor**. |
| AM05 document question hangs, then warns about a hostname | that service has no interface endpoint yet, or it was created under 2 minutes ago | The trace names the unreachable hostname: add or wait for that endpoint. |
| AM06 guardrail never masks the input | the guardrail rule only has the legacy action set | Set **input** and **output** actions (see SOLUTION.md §6). |
| The agent invents data or tool calls | no tools are connected (expected in AM02's broken state) | Fix the mission; the trace's `tools_discovered` tells you what the agent can see. |

## The AWS CLI

| Symptom | Cause | Fix |
|---|---|---|
| `Invalid choice … bedrock-agentcore-control` or `s3vectors` | AWS CLI older than 2.30 | Upgrade the CLI, use **CloudShell** (always current), or do that step in the console. |
| `jq: command not found` | jq not installed | `brew install jq` / `sudo apt install jq`. |
| A CLI step says a variable is empty | the copy-paste block wasn't run in this terminal, or not from `student-terraform/` | `cd` into the mission's `student-terraform/` and run the mission README's value block again. |
| `update-agent-runtime` wiped other settings | that API **replaces** the whole configuration | Start from `get-agent-runtime` and send everything back, as SOLUTION.md does. Or `terraform apply` to reset and try again. |

## Still stuck?

1. `terraform apply` again resets everything Terraform manages to the broken starting state (delete your hand-made resources first).
2. Or destroy and redeploy: about 10 minutes for a completely clean start.
3. Compare against the working copy: deploy `student-terraform-solution/` with `-var course_prefix=orbitsol` and look at the same resource in both.
