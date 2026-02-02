# OMEN Infrastructure (Terraform)

Infrastructure as Code for OMEN API: ECS Fargate, ALB, EFS, Blue-Green deployment, CloudWatch alarms.

## Prerequisites

- Terraform >= 1.0
- AWS CLI configured (or `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`)
- For VPC module: `terraform-aws-modules/vpc/aws` ~> 5.0

## Backend

By default no remote backend is set. To use S3:

1. Create an S3 bucket and DynamoDB table for state locking (optional).
2. Uncomment the `backend "s3"` block in `main.tf` and set `bucket`, `key`, `region`.

## Usage

```bash
cd terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

## Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `aws_region` | AWS region | `us-east-1` |
| `environment` | Environment name | `production` |
| `project` | Project name | `omen` |
| `acm_certificate_arn` | ACM cert ARN for HTTPS | (empty) |
| `api_keys_secret_name` | Secrets Manager secret for API keys | `omen/api-keys` |
| `ecr_repository_url` | ECR image URL (optional) | (uses created ECR) |
| `desired_count_blue` | Blue service task count | `2` |
| `desired_count_green` | Green service task count | `0` |
| `enable_https_listener` | Create HTTPS listener | `false` |

## Blue-Green Deployment

- **Blue** and **Green** ECS services point to separate target groups.
- Default HTTP listener forwards to **blue**. For blue-green:
  1. Deploy new image to **green** and set `desired_count_green = 2`.
  2. Run smoke tests against green (e.g. internal URL).
  3. Change listener default action to green target group (manual or CI step).
  4. Set `desired_count_blue = 0`, `desired_count_green = 2` and apply.
- Rollback: switch listener back to blue and scale blue up.

## Outputs

- `alb_dns_name` — ALB DNS (for Route53 or smoke tests)
- `blue_target_group_arn` / `green_target_group_arn` — for CI listener switch
- `efs_file_system_id` — EFS for ledger storage
- `alerts_sns_topic_arn` — SNS for CloudWatch alarms

## API Keys

Create or update the secret value in AWS Secrets Manager for `api_keys_secret_name`. Value must be a JSON array of API key strings, e.g. `["your-api-key"]`.
