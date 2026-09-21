"""通知模块单元测试."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from jobpilot.notify import EmailAlertSender, compose_alert_message, send_notification


class TestEmailAlertSender:
    def test_not_configured_without_params(self):
        sender = EmailAlertSender()
        assert sender.is_configured is False

    def test_not_configured_partial(self):
        sender = EmailAlertSender(smtp_host="smtp.test.com", username="user")
        assert sender.is_configured is False

    def test_configured_with_all_params(self):
        sender = EmailAlertSender(
            smtp_host="smtp.test.com",
            smtp_port=587,
            username="user@test.com",
            password="pass",
            recipients=["to@test.com"],
        )
        assert sender.is_configured is True

    def test_send_alert_skips_when_not_configured(self):
        sender = EmailAlertSender()
        result = sender.send_alert("test", "message")
        assert result is False

    def test_send_alert_returns_false_on_error(self):
        sender = EmailAlertSender(
            smtp_host="invalid.host",
            smtp_port=587,
            username="user@test.com",
            password="pass",
            recipients=["to@test.com"],
        )
        result = sender.send_alert("test", "message")
        assert result is False


class TestSendNotification:
    def test_returns_false_without_url(self):
        result = send_notification("test message")
        assert result is False

    @patch("apprise.Apprise")
    def test_returns_false_on_invalid_url(self, mock_apprise_cls):
        mock_ap = MagicMock()
        mock_ap.add.return_value = False
        mock_apprise_cls.return_value = mock_ap
        result = send_notification("test", notify_url="invalid://url")
        assert result is False

    @patch("apprise.Apprise")
    def test_returns_true_on_success(self, mock_apprise_cls):
        mock_ap = MagicMock()
        mock_ap.add.return_value = True
        mock_ap.notify.return_value = True
        mock_apprise_cls.return_value = mock_ap
        result = send_notification("test", notify_url="json://example.com")
        assert result is True


class TestComposeAlertMessage:
    def test_basic_message(self):
        alerts = [
            {"company": "Stripe", "title": "Backend Engineer", "overall": 85},
            {"company": "Airbnb", "title": "Full Stack", "overall": 78},
        ]
        msg = compose_alert_message(alerts, threshold=75)
        assert "Stripe" in msg
        assert "Airbnb" in msg
        assert "85" in msg
        assert "75" in msg

    def test_with_url(self):
        alerts = [
            {"company": "Stripe", "title": "Engineer", "overall": 90, "url": "https://example.com"},
        ]
        msg = compose_alert_message(alerts, threshold=75)
        assert "https://example.com" in msg

    def test_empty_alerts(self):
        msg = compose_alert_message([], threshold=75)
        assert "0" in msg
