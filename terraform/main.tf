# ═══════════════════════════════════════════════════════════════════════════════
# OMEN Production Infrastructure — ECS Fargate, ALB, EFS, Blue-Green
# ═══════════════════════════════════════════════════════════════════════════════

terraform {
  required_version = ">= 1.0"

  # Uncomment and set bucket/key when using remote state
  # backend "s3" {
  #   bucket = "omen-terraform-state"
  #   key    = "production/terraform.tfstate"
  #   region = "us-east-1"
  # }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ══════════════════════════════════════════════════════════════════════════════
# VPC & Networking
# ══════════════════════════════════════════════════════════════════════════════
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.project}-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true
  enable_vpn_gateway = false

  tags = {
    Environment = var.environment
    Project     = var.project
  }
}

# ══════════════════════════════════════════════════════════════════════════════
# ECR Repository
# ══════════════════════════════════════════════════════════════════════════════
resource "aws_ecr_repository" "omen" {
  name                 = var.project
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Project = var.project
  }
}

# ══════════════════════════════════════════════════════════════════════════════
# Secrets Manager (API keys — populate secret value outside Terraform)
# ══════════════════════════════════════════════════════════════════════════════
resource "aws_secretsmanager_secret" "api_keys" {
  name                    = var.api_keys_secret_name
  recovery_window_in_days  = 7
  tags = { Project = var.project }
}

resource "aws_secretsmanager_secret_version" "api_keys" {
  secret_id     = aws_secretsmanager_secret.api_keys.id
  secret_string  = jsonencode([]) # Replace with actual keys via console or separate process
}

# ══════════════════════════════════════════════════════════════════════════════
# IAM Roles (ECS execution & task)
# ══════════════════════════════════════════════════════════════════════════════
resource "aws_iam_role" "ecs_execution_role" {
  name = "${var.project}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_execution_secrets" {
  name = "secrets"
  role = aws_iam_role.ecs_execution_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [aws_secretsmanager_secret.api_keys.arn]
    }]
  })
}

resource "aws_iam_role" "ecs_task_role" {
  name = "${var.project}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

# ══════════════════════════════════════════════════════════════════════════════
# Security Groups
# ══════════════════════════════════════════════════════════════════════════════
resource "aws_security_group" "alb" {
  name        = "${var.project}-alb"
  description = "ALB for OMEN API"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "${var.project}-alb" }
}

resource "aws_security_group" "ecs_tasks" {
  name        = "${var.project}-ecs-tasks"
  description = "ECS tasks for OMEN API"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "${var.project}-ecs-tasks" }
}

resource "aws_security_group" "efs" {
  name        = "${var.project}-efs"
  description = "EFS mount targets for ledger"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "${var.project}-efs" }
}

# ══════════════════════════════════════════════════════════════════════════════
# CloudWatch Log Group
# ══════════════════════════════════════════════════════════════════════════════
resource "aws_cloudwatch_log_group" "omen_api" {
  name              = "/ecs/${var.project}-api"
  retention_in_days  = 30
  tags = { Project = var.project }
}

# ══════════════════════════════════════════════════════════════════════════════
# ECS Cluster
# ══════════════════════════════════════════════════════════════════════════════
resource "aws_ecs_cluster" "main" {
  name = "${var.project}-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  tags = { Project = var.project }
}

# ══════════════════════════════════════════════════════════════════════════════
# ECS Task Definition
# ══════════════════════════════════════════════════════════════════════════════
locals {
  ecr_image = var.ecr_repository_url != "" ? "${var.ecr_repository_url}:latest" : "${aws_ecr_repository.omen.repository_url}:latest"
}

resource "aws_ecs_task_definition" "omen_api" {
  family                   = "${var.project}-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([{
    name  = "omen-api"
    image = local.ecr_image

    portMappings = [{ containerPort = 8000, protocol = "tcp" }]

    environment = [
      { name = "OMEN_LEDGER_BASE_PATH", value = "/data/ledger" },
      { name = "OMEN_LOG_LEVEL", value = "INFO" },
      { name = "OMEN_LOG_FORMAT", value = "json" }
    ]

    secrets = [
      { name = "OMEN_SECURITY_API_KEYS", valueFrom = aws_secretsmanager_secret.api_keys.arn }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.omen_api.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }

    mountPoints = [{
      sourceVolume  = "ledger-data"
      containerPath = "/data/ledger"
    }]
  }])

  volume {
    name = "ledger-data"
    efs_volume_configuration {
      file_system_id = aws_efs_file_system.ledger.id
      root_directory = "/"
    }
  }
  tags = { Project = var.project }
}

# ══════════════════════════════════════════════════════════════════════════════
# EFS for Ledger Storage
# ══════════════════════════════════════════════════════════════════════════════
resource "aws_efs_file_system" "ledger" {
  creation_token = "${var.project}-ledger"
  encrypted      = true

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }
  tags = { Name = "${var.project}-ledger" }
}

resource "aws_efs_mount_target" "ledger" {
  count           = length(module.vpc.private_subnets)
  file_system_id  = aws_efs_file_system.ledger.id
  subnet_id      = module.vpc.private_subnets[count.index]
  security_groups = [aws_security_group.efs.id]
}

# ══════════════════════════════════════════════════════════════════════════════
# Application Load Balancer & Target Groups
# ══════════════════════════════════════════════════════════════════════════════
resource "aws_lb" "main" {
  name               = "${var.project}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = module.vpc.public_subnets

  enable_deletion_protection = var.environment == "production"

  tags = {
    Environment = var.environment
    Project     = var.project
  }
}

resource "aws_lb_target_group" "blue" {
  name        = "${var.project}-tg-blue"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health/"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold  = 3
  }
  tags = { Name = "${var.project}-tg-blue" }
}

resource "aws_lb_target_group" "green" {
  name        = "${var.project}-tg-green"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health/"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 3
  }
  tags = { Name = "${var.project}-tg-green" }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "forward"
    target_group_arn = aws_lb_target_group.blue.arn
  }
}

resource "aws_lb_listener" "https" {
  count = var.enable_https_listener && var.acm_certificate_arn != "" ? 1 : 0

  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.acm_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.blue.arn
  }
}

# ══════════════════════════════════════════════════════════════════════════════
# ECS Services (Blue-Green)
# ══════════════════════════════════════════════════════════════════════════════
resource "aws_ecs_service" "omen_api_blue" {
  name            = "${var.project}-api-blue"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.omen_api.arn
  desired_count   = var.desired_count_blue
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.blue.arn
    container_name   = "omen-api"
    container_port   = 8000
  }

  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 100
  }

  health_check_grace_period_seconds = 60
  tags = { Project = var.project }
}

resource "aws_ecs_service" "omen_api_green" {
  name            = "${var.project}-api-green"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.omen_api.arn
  desired_count   = var.desired_count_green
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.green.arn
    container_name   = "omen-api"
    container_port   = 8000
  }

  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 100
  }

  health_check_grace_period_seconds = 60
  tags = { Project = var.project }
}

# ══════════════════════════════════════════════════════════════════════════════
# SNS Topic for Alerts
# ══════════════════════════════════════════════════════════════════════════════
resource "aws_sns_topic" "alerts" {
  name = "${var.project}-alerts"
  tags = { Project = var.project }
}

# ══════════════════════════════════════════════════════════════════════════════
# CloudWatch Alarms
# ══════════════════════════════════════════════════════════════════════════════
resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "${var.project}-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period               = 300
  statistic            = "Average"
  threshold            = 80

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.omen_api_blue.name
  }
  alarm_actions = [aws_sns_topic.alerts.arn]
  tags          = { Project = var.project }
}

resource "aws_cloudwatch_metric_alarm" "memory_high" {
  alarm_name          = "${var.project}-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period               = 300
  statistic            = "Average"
  threshold            = 80

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.omen_api_blue.name
  }
  alarm_actions = [aws_sns_topic.alerts.arn]
  tags          = { Project = var.project }
}
