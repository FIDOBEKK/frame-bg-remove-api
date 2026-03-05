import os
import json
import base64
import uuid
import urllib.request
import urllib.error


def _headers(args):
    return args.get("__ow_headers") or {}


def _json(status, payload):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }


def _verify_token(args):
    expected = os.getenv("BG_API_TOKEN", "")
    if not expected:
        return False, "Server misconfigured: BG_API_TOKEN missing"

    headers = _headers(args)
    auth = headers.get("authorization") or headers.get("Authorization") or ""
    x_token = headers.get("x-api-token") or headers.get("X-API-Token") or ""

    bearer = ""
    if isinstance(auth, str) and auth.lower().startswith("bearer "):
        bearer = auth.split(" ", 1)[1].strip()

    provided = bearer or x_token or args.get("token", "")
    if provided != expected:
        return False, "Unauthorized"

    return True, ""


def _parse_image(args):
    image_b64 = args.get("image_base64", "")

    if not image_b64 and "__ow_body" in args:
        body = args.get("__ow_body")
        if isinstance(body, str):
            try:
                payload = json.loads(body)
                image_b64 = payload.get("image_base64", "")
            except Exception:
                pass

    if not image_b64:
        raise ValueError("Missing image_base64")

    if image_b64.startswith("data:") and "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]

    try:
        return base64.b64decode(image_b64)
    except Exception as exc:
        raise ValueError(f"Invalid base64 image: {exc}")


def _multipart_body(image_bytes, boundary):
    crlf = "\r\n"
    lines = [
        f"--{boundary}",
        'Content-Disposition: form-data; name="image_file"; filename="upload.jpg"',
        "Content-Type: image/jpeg",
        "",
    ]
    head = crlf.join(lines).encode("utf-8") + crlf.encode("utf-8")
    tail = (crlf + f"--{boundary}--" + crlf).encode("utf-8")
    return head + image_bytes + tail


def _call_remove_bg(image_bytes):
    api_key = os.getenv("REMOVE_BG_API_KEY", "")
    if not api_key:
        raise RuntimeError("Server misconfigured: REMOVE_BG_API_KEY missing")

    boundary = f"----do-fn-{uuid.uuid4().hex}"
    body = _multipart_body(image_bytes, boundary)

    req = urllib.request.Request(
        "https://api.remove.bg/v1.0/removebg",
        data=body,
        method="POST",
        headers={
            "X-Api-Key": api_key,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "image/png",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"remove.bg HTTP {exc.code}: {detail}")
    except Exception as exc:
        raise RuntimeError(f"remove.bg request failed: {exc}")


def main(args):
    ok, msg = _verify_token(args)
    if not ok:
        return _json(401, {"ok": False, "error": msg})

    try:
        image = _parse_image(args)
        max_bytes = int(os.getenv("BG_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
        if len(image) > max_bytes:
            return _json(413, {"ok": False, "error": f"Image too large (max {max_bytes} bytes)"})

        out_png = _call_remove_bg(image)

        return _json(200, {
            "ok": True,
            "mime": "image/png",
            "image_base64": base64.b64encode(out_png).decode("utf-8"),
        })
    except ValueError as exc:
        return _json(400, {"ok": False, "error": str(exc)})
    except Exception as exc:
        return _json(500, {"ok": False, "error": str(exc)})
