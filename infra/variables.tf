variable "endpoint_url" {
  description = "Floci endpoint accessible from the Terraform container."
  type        = string
  default     = "http://floci:4566"
}

variable "region" {
  description = "Region shared by Terraform and the application."
  type        = string
  default     = "us-east-1"
}

variable "bucket_name" {
  description = "Bucket holding scraper results."
  type        = string
  default     = "quotes-results-lab2"
}

variable "queue_name" {
  description = "Queue holding scraping jobs."
  type        = string
  default     = "quotes-jobs-lab2"
}
