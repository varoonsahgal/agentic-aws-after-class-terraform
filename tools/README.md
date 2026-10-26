<sub>[⬅ Back to the kit](../README.md)</sub>

# Tools

Three small Python scripts. They need Python 3.10+ and boto3, use your normal AWS credentials (`AWS_PROFILE` is honoured), and change nothing in your account.

| Script | Run it | What it does |
|---|---|---|
| [`preflight.py`](preflight.py) | once, before your first mission: `python3 tools/preflight.py` | Checks Terraform, Python, boto3, the AWS CLI and jq; your credentials; that AgentCore, S3 Vectors, Knowledge Bases and Cognito answer; that **Nova 2 Lite** and **Titan Embeddings V2** respond (two tiny calls); and your VPC quota. |
| [`flight_test.py`](flight_test.py) | from a stack folder: `python3 ../../tools/flight_test.py .` | Reads the stack's `terraform output`, sends the mission's Flight Test questions to your chat console and checks each reply's trace. **FAIL** lines tell you what's still broken; exits `0` with *Mission accomplished* when everything passes. Works on the broken stack, after your fix, and on the solution stack. |
| [`find_leftovers.py`](find_leftovers.py) | after destroying: `python3 tools/find_leftovers.py jsmith42` | Lists anything with your id still in the account: runtimes, gateways, memories, knowledge bases, guardrails, vector buckets, Lambdas, user pools, VPCs, interface endpoints, network interfaces, log groups. Each comes with the console page or command that removes it. |

All three accept `--region <name>` if you deployed somewhere other than `us-west-2` (`flight_test.py` reads the region from your chat URL).
