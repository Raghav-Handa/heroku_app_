
# AWS S3 Bucket with Pulumi (Python) — Beginner Friendly

A **minimal and beginner-friendly Pulumi template** to create **one AWS S3 bucket using Python**.  
No fluff. No unnecessary dependencies. Just the basics to get you productive fast.

---
# What This Project Does

- Creates **one S3 bucket** in your AWS account
- Uses **Pulumi + Python**
- Exports the **bucket name** as an output

This repo is ideal if:
- You are **new to Pulumi**
- You want to understand **Infrastructure as Code (IaC)**
- You need a **clean starting point** for AWS + Python

---

# Prerequisites (Read This First)

Before running anything, make sure you have:

- An **AWS account**
- AWS credentials configured  
  (via `aws configure` or environment variables)
- **Python 3.6+** installed
- **Pulumi CLI** installed and logged in

Verify Pulumi:
```bash
pulumi version
```
---
# Getting Started
1. Create a New Pulumi Project
```bash
pulumi new aws-python
```
2. Follow the Prompts

Project name → choose any name.

AWS region → press Enter to use us-east-1 (default)

3. Enter the Project Directory
```bash
cd <project-name>
```
4. Preview the Infrastructure Changes
```bash
pulumi preview
```

This shows what Pulumi plans to create. No resources are created yet.

5. Deploy the S3 Bucket
```bash 
pulumi up 
```


Approve the changes when prompted.

6. Destroy the Resources (Cleanup)
```bash 
pulumi destroy
```
---

# Project Structure Explained

After setup, your project directory will look like this:
```bash
├── __main__.py          # Main Pulumi program (creates the S3 bucket)
├── Pulumi.yaml          # Project metadata and configuration
├── requirements.txt     # Python dependencies
└── Pulumi.<stack>.yaml  # Stack-specific config (e.g., dev, prod)
```
You mainly edit __main__.py to add or modify resources.

---


# Configuration

This project uses a Pulumi config value for AWS region.

- Key: aws:region

- Default: us-east-1

View current region
```bash
pulumi config get aws:region
```
Change region
```bash 
pulumi config set aws:region us-west-2
```
---
# Outputs

After deployment, the stack exports:
```bash
bucket_name — the name (ID) of the created S3 bucket
```
Retrieve it using:
```bash
pulumi stack output bucket_name
```
---

# Next Steps

Once you're comfortable with this setup, you can:

- Enable bucket versioning or encryption

- Add lifecycle rules

- Provision more AWS services (EC2, IAM, DynamoDB)

- Organize infrastructure into modules

- Integrate Pulumi into CI/CD pipelines

## Help and Resources

[Pulumi Documentation](https://www.pulumi.com/docs/)

[AWS SDK for Pulumi](https://www.pulumi.com/registry/packages/aws/)

[Pulumi Community Slack](https://slack.pulumi.com/)

[GitHub Issues](https://github.com/pulumi/pulumi/issues)

## Summary

- Creates one AWS S3 bucket

- Uses Pulumi with Python

- Designed for absolute beginners

- Easy to extend for real-world projects

- Clone it, deploy it, destroy it, and learn Infrastructure as Code the right way.


__Contributions and feedback are always welcome!__

---
