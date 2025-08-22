import base64
import time
from typing import Dict, Any, Optional

import requests

PAYU_OAUTH_URL = "https://secure.snd.payu.com/pl/standard/user/oauth/authorize"
PAYU_ORDERS_URL = "https://secure.snd.payu.com/api/v2_1/orders"


class PayUClient:
    def __init__(self, pos_id: str, client_secret: str, app_base_url: str):
        self.pos_id = pos_id
        self.client_secret = client_secret
        self.app_base_url = app_base_url.rstrip("/")
        self._token: Optional[str] = None
        self._token_exp: float = 0.0

    def _get_access_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_exp - 30:
            return self._token

        auth = base64.b64encode(f"{self.pos_id}:{self.client_secret}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"grant_type": "client_credentials"}
        resp = requests.post(PAYU_OAUTH_URL, headers=headers, data=data, timeout=15)
        resp.raise_for_status()
        body = resp.json()
        self._token = body["access_token"]
        self._token_exp = now + int(body.get("expires_in", 300))
        return self._token

    def create_order(
        self,
        *,
        total_amount_grosze: int,
        description: str,
        customer_ip: str = "127.0.0.1",
        product_name: str = "Order",
        currency: str = "PLN",
    ) -> Dict[str, Any]:
        token = self._get_access_token()
        payload = {
            "notifyUrl": f"{self.app_base_url}/payu/notify",
            "continueUrl": f"{self.app_base_url}/return",
            "customerIp": customer_ip,
            "merchantPosId": self.pos_id,
            "description": description,
            "currencyCode": currency,
            "totalAmount": str(total_amount_grosze),
            "products": [
                {
                    "name": product_name,
                    "unitPrice": str(total_amount_grosze),
                    "quantity": "1",
                }
            ],
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        resp = requests.post(PAYU_ORDERS_URL, json=payload, headers=headers, timeout=20)
        resp.raise_for_status()
        return resp.json()
