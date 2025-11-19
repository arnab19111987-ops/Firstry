import os

from fastapi import FastAPI, Header, HTTPException, Request

from .licensing import verify
from .schemas import VerifyRequest, VerifyResponse
from .webhooks import verify_lemon_signature, verify_stripe_signature

app = FastAPI(title="FirstTry Licensing", version="0.1.0")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/v1/license/verify", response_model=VerifyResponse)
def license_verify(body: VerifyRequest):
    ok, reason, feats = verify(body.product, body.key)
    return VerifyResponse(valid=ok, reason=reason, features=feats)


@app.post("/v1/webhook/stripe")
async def stripe_webhook(
    request: Request, stripe_signature: str | None = Header(default=None)
):
    payload = await request.body()
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    try:
        verify_stripe_signature(payload, stripe_signature, secret)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"received": True, "provider": "stripe"}


@app.post("/v1/webhook/lemonsqueezy")
async def lemonsqueezy_webhook(
    request: Request, x_signature: str | None = Header(default=None)
):
    payload = await request.body()
    secret = os.getenv("LEMON_SQUEEZY_WEBHOOK_SECRET", "")
    try:
        verify_lemon_signature(payload, x_signature, secret)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"received": True, "provider": "lemonsqueezy"}
