# ═══════════════════════════════════════════════════════════════════════════════
# OMEN Terraform — Outputs
# ═══════════════════════════════════════════════════════════════════════════════

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ECS cluster ARN"
  value       = aws_ecs_cluster.main.arn
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "ALB zone ID for Route53 alias"
  value       = aws_lb.main.zone_id
}

output "blue_target_group_arn" {
  description = "Blue target group ARN"
  value       = aws_lb_target_group.blue.arn
}

output "green_target_group_arn" {
  description = "Green target group ARN"
  value       = aws_lb_target_group.green.arn
}

output "https_listener_arn" {
  description = "HTTPS listener ARN (if created)"
  value       = try(aws_lb_listener.https[0].arn, null)
}

output "efs_file_system_id" {
  description = "EFS file system ID for ledger storage"
  value       = aws_efs_file_system.ledger.id
}

output "cloudwatch_log_group_name" {
  description = "CloudWatch log group for ECS"
  value       = aws_cloudwatch_log_group.omen_api.name
}

output "alerts_sns_topic_arn" {
  description = "SNS topic ARN for alerts"
  value       = aws_sns_topic.alerts.arn
}
