"""JARVIS command-line client (Phase 10).

A thin CLI over the JARVIS API client library. Useful for quick
verification, scripting, and as a reference integration example.

Examples:
    JARVIS_API_URL=http://127.0.0.1:8000 python3 scripts/jarvis-cli.py login --username alice --password secret
    JARVIS_API_URL=http://127.0.0.1:8000 JARVIS_ACCESS_TOKEN=<your-token> python3 scripts/jarvis-cli.py health
    JARVIS_API_URL=http://127.0.0.1:8000 python3 scripts/jarvis-cli.py devices list
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from typing import Any, NoReturn

from jarvis.client import (
    JarvisAuthenticationError,
    JarvisClient,
    JarvisClientError,
)


def _die(message: str, code: int = 1) -> NoReturn:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(code)


def _fmt(obj: Any) -> str:
    if isinstance(obj, (dict, list)):
        return json.dumps(obj, indent=2, sort_keys=True)
    return str(obj)


def build_client() -> JarvisClient:
    return JarvisClient()


def cmd_login(client: JarvisClient, args: argparse.Namespace) -> int:
    try:
        data = client.login(username=args.username, password=args.password)
    except JarvisAuthenticationError as exc:
        _die(str(exc))
    except JarvisClientError as exc:
        _die(str(exc))
    print(_fmt(data))
    return 0


def cmd_me(client: JarvisClient, args: argparse.Namespace) -> int:
    try:
        print(_fmt(client.me()))
    except JarvisAuthenticationError as exc:
        _die(str(exc))
    except JarvisClientError as exc:
        _die(str(exc))
    return 0


def cmd_health(client: JarvisClient, args: argparse.Namespace) -> int:
    try:
        print(_fmt(client.health()))
    except JarvisClientError as exc:
        _die(str(exc))
    return 0


def cmd_ready(client: JarvisClient, args: argparse.Namespace) -> int:
    try:
        print(_fmt(client.ready()))
    except JarvisClientError as exc:
        _die(str(exc))
    return 0


def cmd_stt(client: JarvisClient, args: argparse.Namespace) -> int:
    audio = args.audio
    if os_path_exists(audio):
        with open(audio, "rb") as fh:
            audio_b64 = base64.b64encode(fh.read()).decode("ascii")
    else:
        audio_b64 = audio
    try:
        print(_fmt(client.speech_to_text(audio_b64=audio_b64, language=args.language)))
    except JarvisClientError as exc:
        _die(str(exc))
    return 0


def cmd_tts(client: JarvisClient, args: argparse.Namespace) -> int:
    try:
        print(
            _fmt(
                client.text_to_speech(
                    text=args.text, voice=args.voice, language=args.language
                )
            )
        )
    except JarvisClientError as exc:
        _die(str(exc))
    return 0


def cmd_describe(client: JarvisClient, args: argparse.Namespace) -> int:
    image = args.image
    if os_path_exists(image):
        with open(image, "rb") as fh:
            image_b64 = base64.b64encode(fh.read()).decode("ascii")
    else:
        image_b64 = image
    try:
        print(_fmt(client.describe_image(image_b64=image_b64, prompt=args.prompt)))
    except JarvisClientError as exc:
        _die(str(exc))
    return 0


def cmd_analyze(client: JarvisClient, args: argparse.Namespace) -> int:
    image = args.image
    if os_path_exists(image):
        with open(image, "rb") as fh:
            image_b64 = base64.b64encode(fh.read()).decode("ascii")
    else:
        image_b64 = image
    questions = [q.strip() for q in args.questions.split(",") if q.strip()]
    try:
        print(_fmt(client.analyze_image(image_b64=image_b64, questions=questions)))
    except JarvisClientError as exc:
        _die(str(exc))
    return 0


def cmd_devices(client: JarvisClient, args: argparse.Namespace) -> int:
    try:
        print(_fmt(client.list_devices()))
    except JarvisClientError as exc:
        _die(str(exc))
    return 0


def cmd_device_state(client: JarvisClient, args: argparse.Namespace) -> int:
    try:
        print(_fmt(client.get_device_state(args.device_id)))
    except JarvisClientError as exc:
        _die(str(exc))
    return 0


def cmd_set_device_state(client: JarvisClient, args: argparse.Namespace) -> int:
    state = {}
    for item in args.state:
        if "=" not in item:
            _die(f"Invalid state item '{item}': expected KEY=VALUE")
        k, v = item.split("=", 1)
        state[k] = v
    try:
        print(_fmt(client.set_device_state(args.device_id, state)))
    except JarvisClientError as exc:
        _die(str(exc))
    return 0


def os_path_exists(path: str) -> bool:
    import os

    return os.path.exists(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="JARVIS API command-line client (Phase 10)"
    )
    parser.add_argument(
        "--url",
        default=None,
        help="JARVIS API base URL (default: JARVIS_API_URL env or http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Bearer access token (default: JARVIS_ACCESS_TOKEN env)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_login = sub.add_parser("login", help="Authenticate and obtain a bearer token")
    p_login.add_argument("--username", required=True)
    p_login.add_argument("--password", required=True)
    p_login.set_defaults(func=cmd_login)

    p_me = sub.add_parser("me", help="Get current user profile")
    p_me.set_defaults(func=cmd_me)

    p_health = sub.add_parser("health", help="Liveness probe")
    p_health.set_defaults(func=cmd_health)

    p_ready = sub.add_parser("ready", help="Readiness probe")
    p_ready.set_defaults(func=cmd_ready)

    p_stt = sub.add_parser("stt", help="Speech-to-text")
    p_stt.add_argument("audio", help="Audio file path or base64 data")
    p_stt.add_argument("--language", default=None)
    p_stt.set_defaults(func=cmd_stt)

    p_tts = sub.add_parser("tts", help="Text-to-speech")
    p_tts.add_argument("text", help="Text to synthesize")
    p_tts.add_argument("--voice", default=None)
    p_tts.add_argument("--language", default=None)
    p_tts.set_defaults(func=cmd_tts)

    p_describe = sub.add_parser("describe", help="Describe an image")
    p_describe.add_argument("image", help="Image file path or base64 data")
    p_describe.add_argument("--prompt", default=None)
    p_describe.set_defaults(func=cmd_describe)

    p_analyze = sub.add_parser("analyze", help="Analyze an image with questions")
    p_analyze.add_argument("image", help="Image file path or base64 data")
    p_analyze.add_argument(
        "--questions", required=True, help="Comma-separated questions"
    )
    p_analyze.set_defaults(func=cmd_analyze)

    p_devices = sub.add_parser("devices", help="List smart environment devices")
    p_devices.set_defaults(func=cmd_devices)

    p_dstate = sub.add_parser("device-state", help="Get device state")
    p_dstate.add_argument("device_id")
    p_dstate.set_defaults(func=cmd_device_state)

    p_dset = sub.add_parser("set-device-state", help="Set device state (KEY=VALUE ...)")
    p_dset.add_argument("device_id")
    p_dset.add_argument("state", nargs="+", help="KEY=VALUE pairs")
    p_dset.set_defaults(func=cmd_set_device_state)

    args = parser.parse_args(argv)

    if args.url:
        import os as _os

        _os.environ["JARVIS_API_URL"] = args.url
    client = JarvisClient(
        base_url=args.url,
        access_token=args.token,
    )
    try:
        result = args.func(client, args)
        return result if isinstance(result, int) else 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
