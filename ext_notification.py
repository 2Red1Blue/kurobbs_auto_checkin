
import base64
import hashlib
import hmac
import time

import requests
from loguru import logger
from serverchan_sdk import sc_send

from settings import Settings


class NotificationService:
    """Aggregate notification channels for GitHub Actions."""

    def __init__(self, settings: Settings):
        self.settings = settings

    FAILURE_HINT = (
        "请重新登录网页版库街区 www.kurobbs.com，"
        "从浏览器 F12 → Application → Local Storage 复制 auth_token，"
        "更新仓库的 TOKEN secret（TOKEN_SOURCE 保持 h5）。"
    )

    def send(self, message: str):
        title = "库街区自动签到任务"
        delivered = [
            self._send_bark(title, message),
            self._send_server3(title, message),
        ]
        if not any(delivered):
            logger.debug("No notification channel configured; skipped sending result.")

    def send_failure(self, message: str):
        """签到失败时告警：飞书机器人 + 其它已配置通道。"""
        text = "【库街区签到失败】\n{}\n\n处理方式：{}".format(message, self.FAILURE_HINT)
        delivered = [
            self._send_feishu(text),
            self._send_bark("库街区签到失败", message),
            self._send_server3("库街区签到失败", message),
        ]
        if not any(delivered):
            logger.debug("No notification channel configured; skipped sending failure alert.")

    def _feishu_payload(self, text: str) -> dict:
        """构造飞书自定义机器人消息体；机器人开了「签名校验」时需要 timestamp + sign。"""
        payload = {"msg_type": "text", "content": {"text": text}}
        secret = self.settings.feishu_secret
        if secret:
            timestamp = str(int(time.time()))
            string_to_sign = "{}\n{}".format(timestamp, secret)
            digest = hmac.new(
                string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
            ).digest()
            payload["timestamp"] = timestamp
            payload["sign"] = base64.b64encode(digest).decode("utf-8")
        return payload

    def _send_feishu(self, text: str) -> bool:
        url = self.settings.feishu_webhook
        if not url:
            return False

        payload = self._feishu_payload(text)
        try:
            response = requests.post(url, json=payload, timeout=10)
            data = {}
            try:
                data = response.json()
            except ValueError:
                pass
            code = data.get("code", data.get("StatusCode"))
            if response.status_code == 200 and code == 0:
                logger.debug("Sent Feishu alert.")
                return True
            logger.warning(
                "Feishu webhook rejected the message: status={}, body={}",
                response.status_code,
                str(data)[:200],
            )
        except requests.RequestException as exc:
            logger.warning("Failed to push Feishu alert: {}", exc)
        return False

    def _send_bark(self, title: str, message: str) -> bool:
        if not self.settings.bark_device_key or not self.settings.bark_server_url:
            return False

        url = f"{self.settings.bark_server_url}/{self.settings.bark_device_key}/{title}/{message}"
        try:
            response = requests.get(url, timeout=10)
            logger.debug("Sent Bark notification, status={}", response.status_code)
        except requests.RequestException as exc:
            logger.warning("Failed to push Bark notification: {}", exc)
        return True

    def _send_server3(self, title: str, message: str) -> bool:
        if not self.settings.server3_send_key:
            return False

        try:
            response = sc_send(
                self.settings.server3_send_key,
                title,
                message,
                {"tags": "Github Action|库街区"},
            )
            logger.debug("Sent ServerChan3 notification: {}", response)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to push ServerChan3 notification: {}", exc)
        return True
