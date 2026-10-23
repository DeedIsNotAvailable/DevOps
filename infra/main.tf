resource "aws_s3_bucket" "results" {
  bucket        = var.bucket_name
  force_destroy = true
}

resource "aws_sqs_queue" "jobs" {
  name                       = var.queue_name
  visibility_timeout_seconds = 300
  receive_wait_time_seconds  = 10
  message_retention_seconds  = 86400
}
