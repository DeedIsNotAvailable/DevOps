import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from worker import process_message


class AcknowledgementTests(unittest.TestCase):
    def setUp(self):
        self.message = {"Body": json.dumps({"job_id": "test-job"}), "ReceiptHandle": "receipt-1"}
        self.quotes = [{"text": "Тест", "author": "Автор", "tags": []}]
        self.sqs, self.s3 = Mock(), Mock()

    @patch("worker.scrape_quotes")
    def test_success_uploads_before_deleting_message(self, scrape):
        scrape.return_value = self.quotes
        events = []
        self.s3.put_object.side_effect = lambda **kwargs: events.append("upload")
        self.sqs.delete_message.side_effect = lambda **kwargs: events.append("delete")
        process_message(self.message, self.sqs, self.s3, "bucket", "queue")
        self.assertEqual(events, ["upload", "delete"])
        self.sqs.delete_message.assert_called_once_with(QueueUrl="queue", ReceiptHandle="receipt-1")
        uploaded = self.s3.put_object.call_args.kwargs
        self.assertEqual(uploaded["Key"], "results/test-job.json")
        self.assertEqual(json.loads(uploaded["Body"]), self.quotes)

    @patch("worker.scrape_quotes")
    def test_s3_failure_keeps_message(self, scrape):
        scrape.return_value = self.quotes
        self.s3.put_object.side_effect = RuntimeError("S3 unavailable")
        with self.assertRaisesRegex(RuntimeError, "S3 unavailable"):
            process_message(self.message, self.sqs, self.s3, "bucket", "queue")
        self.sqs.delete_message.assert_not_called()

    @patch("worker.scrape_quotes", side_effect=RuntimeError("Browser failed"))
    def test_scraper_failure_keeps_message(self, scrape):
        with self.assertRaisesRegex(RuntimeError, "Browser failed"):
            process_message(self.message, self.sqs, self.s3, "bucket", "queue")
        self.s3.put_object.assert_not_called()
        self.sqs.delete_message.assert_not_called()

    @patch("worker.scrape_quotes")
    def test_invalid_job_is_not_acknowledged(self, scrape):
        self.message["Body"] = "{}"
        with self.assertRaisesRegex(ValueError, "Missing job_id"):
            process_message(self.message, self.sqs, self.s3, "bucket", "queue")
        scrape.assert_not_called()
        self.sqs.delete_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()
