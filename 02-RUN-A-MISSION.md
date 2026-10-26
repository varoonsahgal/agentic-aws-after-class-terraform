<sub>[⬅ 01-SETUP](01-SETUP.md) · [Back to the kit](README.md) · Next: [03-COSTS-AND-CLEANUP ➡](03-COSTS-AND-CLEANUP.md)</sub>

# 02 · Run a Mission: The Complete Loop

Every mission follows the same seven steps. This page explains each one; each mission's own `README.md` gives the exact values, timings and cleanup for that mission.

```
 ① deploy broken ──▶ ② load your values ──▶ ③ confirm it's broken ──▶ ④ fix it
                                                                         │
 ⑦ destroy ◀── ⑥ compare with the solution ◀── ⑤ prove it's fixed ◀──────┘
```

The examples use **AM02** and the id **`jsmith42`**. Swap in your mission and your id.

---

## ① Deploy the broken environment

```bash
cd AM02-gateway-tool-routing/student-terraform
terraform init                                   # first time only: downloads providers (~1 min)
terraform apply -var 'student_id=jsmith42'
```

Terraform shows a **plan** (everything it will create, around 40 resources) and asks `Do you want to perform these actions?`. Read the summary line, type `yes`, and wait. Most stacks take about 2½ minutes; the AM05 solution takes about 7½ and the AM04 solution about 11 (see each mission's README).

What happens behind the scenes:

- `terraform plan` runs `agents/build_agents.py`, which installs boto3 into `agents/build/` and zips the two Python agents. The first time takes about 20 seconds.
- Terraform creates a Cognito user pool, four tool Lambdas, the chat-console Lambda with a public URL, IAM roles, the AgentCore Gateway, the orchestrator agent in AgentCore Runtime, and whatever this mission needs (a VPC, a vector index, …). Then it **plants the mission's faults**.

When it finishes you'll see `Apply complete! Resources: NN added`, followed by the outputs.

> [!TIP]
> Running the **same** `terraform apply` again later **resets** every setting Terraform manages back to broken. It's a handy "start the mission over" button. It doesn't delete resources you created by hand, though, so remove those first (see ⑦).

## ② Load your values

In class your instructor handed you a card of values. Here, `terraform output` *is* that card:

```bash
terraform output                         # everything
terraform output -raw chat_urls          # one value, ready to paste
```

The handout writes values the classroom way, `chat_urls[<you>]`. In your own stack each output holds **only your value**, so `chat_urls[<you>]` simply means `terraform output -raw chat_urls`.

Each mission's README has a **copy-paste block** that loads every value the solution guide's CLI needs into your shell (`ME`, `GW_ID`, `RT_ID`, `CHAT`, …). Run it from the `student-terraform/` folder.

Open the chat console in your browser:

```bash
terraform output -raw chat_urls ; echo    # copy the URL into a browser tab
```

## ③ Confirm it's broken

```bash
python3 ../../tools/flight_test.py .
```

The Flight Test sends the mission's test questions to your chat console and checks the **trace** of each reply. On a freshly deployed broken stack it should report **FAIL**s: those are the symptoms the handout describes, now with evidence:

```text
OrbitOps Flight Test · AM02 · .
  » Where is shipment SHP-1001?
    trace: tools_discovered=0 tools_called=[] … warnings=[]
  FAIL  tool discovery works: all 9 tools found
        tools_discovered=0 (gateway_configured=False)
  …
0/6 checks passed. The FAILs above are your evidence: that's what is still broken.
```

## ④ Fix it

Open **`HANDOUT.md`** (it renders nicely on GitHub, or use your editor's Markdown preview) and work the mission the way you did in class:

1. Read the **Dispatch alert**, the **Repair objectives** and the **Concept briefing**.
2. Collect the evidence in the **evidence checklist**. The browser console's trace panel and the Flight Test output are both evidence.
3. Write a hypothesis, make **one** change, and re-run the Flight Test.
4. Stuck? Open the **hint ladder** one level at a time.

Use the **AWS console** (region **`us-west-2`**) like in class. Your resources all contain your id: search for `jsmith42`.

> [!NOTE]
> **Following the solution instead?** Open `SOLUTION.md` at **§6 Step-by-step solution**. The console path works as written. For the CLI path, first run your mission README's copy-paste block, so `ME`, `GW_ID` and the rest hold your values. The CLI needs AWS CLI **2.30+**.

## ⑤ Prove it's fixed

```bash
python3 ../../tools/flight_test.py .
```

```text
6/6 checks passed. Mission accomplished.
```

Also do the handout's **Flight Test** by hand in the chat console at least once. Reading the trace yourself is the skill the assessment checks.

> [!IMPORTANT]
> Some fixes take a minute to land: a runtime update publishes a new version (status `UPDATING` → `READY`), memory extraction is asynchronous (AM04), new VPC endpoints need about 2 minutes after *Available* (AM05). If a check fails right after a change, wait a minute and run it again before you change something else.

## ⑥ Compare with the solution

Deploy the **fixed** environment next to your broken one. It needs a different `course_prefix` so the names don't collide:

```bash
cd ../student-terraform-solution
terraform init
terraform apply -var 'student_id=jsmith42' -var 'course_prefix=orbitsol'
python3 ../../tools/flight_test.py .                 # every check passes out of the box
```

Then:

- **Read the fixes as code.** Every change carries a `# FIX` comment:
  ```bash
  diff ../student-terraform/main.tf main.tf
  ```
- **Compare in the console.** Open the same resource in both copies (`orbit-jsmith42-…` and `orbitsol-jsmith42-…`) side by side. What does the correct gateway target, authorizer, memory strategy or endpoint look like?
- **Read `SOLUTION.md`** from §3 on: the *why* behind each fix, the knowledge check and the exam angle.

## ⑦ Destroy everything

1. **Delete what you created by hand first.** Terraform doesn't know about anything you built in the console or CLI during step ④, and some of it blocks the destroy. Each mission's README lists exactly what to delete.
2. Destroy each stack you applied, **using the same `-var` flags you applied with**:

   ```bash
   cd AM02-gateway-tool-routing/student-terraform-solution
   terraform destroy -var 'student_id=jsmith42' -var 'course_prefix=orbitsol'

   cd ../student-terraform
   terraform destroy -var 'student_id=jsmith42'
   ```

3. Check that nothing is left behind:

   ```bash
   python3 ../../tools/find_leftovers.py jsmith42
   ```

> [!WARNING]
> **Don't delete `terraform.tfstate`** until after `terraform destroy` has succeeded. It's Terraform's only record of what it built. Without it you'd have to find and delete everything by hand.

---

**Next:** [03-COSTS-AND-CLEANUP.md](03-COSTS-AND-CLEANUP.md), or jump straight into a mission from the [kit's mission table](README.md#the-missions).
