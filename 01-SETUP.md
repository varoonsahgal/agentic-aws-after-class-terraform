<sub>[⬅ Back to the kit](README.md) · Next: [02-RUN-A-MISSION ➡](02-RUN-A-MISSION.md)</sub>

# 01 · Setup: From Zero to a Passing Preflight

You do this once. After it, deploying any mission is three commands.

**Time:** 20–40 minutes the first time · **Cost:** $0

---

## Step 1 · Get an AWS account you're allowed to break things in

These missions create IAM roles, AI agents, a Cognito user pool, Lambda functions with a **public URL**, S3 buckets and (in AM05) a VPC. Use one of these:

| Option | Good for |
|---|---|
| **A personal AWS account** ([sign up](https://aws.amazon.com/free/)) | Most people. You pay the few cents yourself. |
| **A sandbox account from your employer** | Ask your cloud team for one with Bedrock and AgentCore enabled in `us-west-2`. |
| **Your company's production account** | ❌ Please don't. |

> [!IMPORTANT]
> Sign in to your account's **root user only to create an admin user**, then never use root again. Turn on MFA for root.

## Step 2 · Set a budget alarm (2 minutes, strongly recommended)

A full run of every mission costs well under **$5**. The alarm is there in case you forget to destroy something.

**Console:** Billing and Cost Management → **Budgets** → *Create budget* → **Use a template** → *Monthly cost budget* → amount **$10** → your email → *Create*.

**Or with the CLI** (after Step 4):

```bash
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
aws budgets create-budget --account-id "$ACCOUNT" \
  --budget '{"BudgetName":"agentic-labs","BudgetLimit":{"Amount":"10","Unit":"USD"},"TimeUnit":"MONTHLY","BudgetType":"COST"}' \
  --notifications-with-subscribers '[{"Notification":{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN","Threshold":80},"Subscribers":[{"SubscriptionType":"EMAIL","Address":"you@example.com"}]}]'
```

## Step 3 · Create an identity to deploy with

Terraform needs credentials that can create and delete everything the missions use.

**Simplest (personal account):** IAM → Users → *Create user* → `lab-admin` → *Attach policies directly* → **AdministratorAccess** → create → open the user → **Security credentials** → *Create access key* → *Command Line Interface (CLI)*. Copy the key ID and secret somewhere safe for Step 4.

**Least privilege (shared or work account):** attach the policy in [`iam/deployer-policy.json`](iam/deployer-policy.json) instead of AdministratorAccess. It covers Bedrock, AgentCore, S3 Vectors, Cognito, Lambda, CloudWatch Logs, S3, IAM roles (incl. `iam:PassRole`) and EC2/VPC.

**IAM Identity Center (SSO) users:** skip access keys and use `aws configure sso` in Step 4.

> [!CAUTION]
> Access keys are passwords. Never commit them to Git, paste them in chat, or put them in a `.tf` file.

## Step 4 · Install the tools

| Tool | Version | macOS | Linux | Windows |
|---|---|---|---|---|
| **Terraform** | ≥ 1.6 | `brew tap hashicorp/tap && brew install hashicorp/tap/terraform` | [install page](https://developer.hashicorp.com/terraform/install) | inside WSL2 (below) |
| **Python** | ≥ 3.10 + pip | `brew install python` | `sudo apt install python3 python3-pip` | inside WSL2 |
| **boto3** | any recent | `python3 -m pip install --upgrade boto3` | same | same |
| **AWS CLI v2** | ≥ 2.30 | `brew install awscli` | [installer](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) | inside WSL2 |
| **jq** | any | `brew install jq` | `sudo apt install jq` | inside WSL2 |
| **git** | any | `xcode-select --install` | `sudo apt install git` | inside WSL2 |

> [!NOTE]
> **On Windows, use WSL2** (`wsl --install` in an admin PowerShell, reboot, open *Ubuntu*), then follow the Linux column. The stacks run small Python helpers from Terraform, and they expect a Unix-style `python3`.
>
> **On Debian/Ubuntu,** if `pip install` says *externally-managed-environment*, use `sudo apt install python3-boto3`, or install into a virtual environment (`python3 -m venv ~/labs-venv && source ~/labs-venv/bin/activate && pip install boto3`) and run Terraform from that same shell.

Then connect the CLI to your account:

```bash
aws configure
#   AWS Access Key ID:     <from step 3>
#   AWS Secret Access Key: <from step 3>
#   Default region name:   us-west-2
#   Default output format: json

aws sts get-caller-identity      # prints your account and user: it works
```

Using a named profile? Run `export AWS_PROFILE=<name>` in every new terminal. Terraform, the tools in this repo and the AWS CLI all honour it.

## Step 5 · Check model access

All missions use **Amazon Nova 2 Lite**; AM03 and AM05 also use **Titan Text Embeddings V2**. In most accounts these work straight away. The preflight in the next step calls both. If either fails, open the **Amazon Bedrock console in `us-west-2` → Model access** (or *Model catalog*), find the model and request or enable access, then run the preflight again.

## Step 6 · Clone the kit and run the preflight

```bash
git clone https://github.com/varoonsahgal/agentic-aws-after-class-terraform.git
cd agentic-aws-after-class-terraform
python3 tools/preflight.py
```

It checks your tool versions, your credentials, that AgentCore, S3 Vectors, Knowledge Bases and Cognito answer, that both models respond (two tiny calls, well under a cent), and that you have a free VPC for AM05:

```text
1. Tools on this machine
    OK  Terraform >= 1.6 (found 1.12.2)
    OK  Python >= 3.10 (found 3.11)
    OK  pip is available (the agent zips are built at plan time)
    OK  boto3 installed (1.43.40)
    OK  AWS CLI >= 2.30 for the solution guides' agentcore commands (found 2.31.4)
    OK  jq (used by the solution guides' CLI snippets)
2. AWS identity and region (us-west-2)
    OK  credentials work: arn:aws:iam::123456789012:user/lab-admin
3. Services and model access
    OK  Bedrock AgentCore control plane
    OK  Amazon S3 Vectors
    OK  Bedrock Knowledge Bases
    OK  Amazon Cognito
    OK  Amazon Nova 2 Lite (us.amazon.nova-2-lite-v1:0) answers
    OK  Titan Text Embeddings V2 answers (AM03, AM05)
4. Quotas
    OK  VPCs: 1 of 5 used (AM05 needs 1, or 2 with the solution stack too)

All clear. You're ready to deploy a mission.
```

**FAIL** lines must be fixed before you deploy (each one says how). **WARN** lines only affect optional CLI steps.

## Step 7 · Pick your id

Every resource you create is named `orbit-<your id>-amNN-…`. Choose **3–12 lowercase letters or digits, no hyphens**, e.g. `jsmith42`, and use the same one every time.

To stop typing it, create a `terraform.tfvars` file inside a mission's `student-terraform/` folder:

```hcl
student_id = "jsmith42"
```

(It's git-ignored.) Then a plain `terraform apply` works. The command examples in this kit keep the `-var` so you can see what's happening.

---

**Setup done.** Continue with [02-RUN-A-MISSION.md](02-RUN-A-MISSION.md).
