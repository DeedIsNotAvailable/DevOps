output "bucket_name" {
  description = "Bucket to pass to the worker."
  value       = aws_s3_bucket.results.bucket
}

output "queue_url" {
  description = "Queue URL to pass to the worker."
  value       = aws_sqs_queue.jobs.url
}

output "endpoint_url" {
  value = var.endpoint_url
}

output "region" {
  value = var.region
}
