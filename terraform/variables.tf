# ═══════════════════════════════════════════════════════════════════════════════
# OMEN Terraform — Input Variables
# ═══════════════════════════════════════════════════════════════════════════════

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (e.g. production, staging)"
  type        = string
  default     = "production"
}

variable "project" {
  description = "Project name"
  type        = string
  default     = "omen"
}

variable "acm_certificate_arn" {
  description = "ARN of ACM certificate for HTTPS listener (optional; create listener only if set)"
  type        = string
  default     = ""
}

variable "api_keys_secret_name" {
  description = "Secrets Manager secret name for OMEN_SECURITY_API_KEYS"
  type        = string
  default     = "omen/api-keys"
}

variable "ecr_repository_url" {
  description = "ECR repository URL for omen image (e.g. 123456789.dkr.ecr.us-east-1.amazonaws.com/omen)"
  type        = string
  default     = ""
}

variable "desired_count_blue" {
  description = "Desired task count for blue service"
  type        = number
  default     = 2
}

variable "desired_count_green" {
  description = "Desired task count for green service (0 when blue is active)"
  type        = number
  default     = 0
}

variable "enable_https_listener" {
  description = "Create HTTPS listener (requires acm_certificate_arn)"
  type        = bool
  default     = false
}
