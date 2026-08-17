"""Validate release configuration without printing secret values."""

from __future__ import annotations

import argparse
from datetime import date
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


REQUIRED_DEPLOY_KEYS = {
    "API_DOMAIN",
    "MYSQL_DATABASE",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "MYSQL_ROOT_PASSWORD",
    "REDIS_PASSWORD",
    "DATABASE_URL",
    "REDIS_URL",
    "WECHAT_APP_ID",
    "WECHAT_APP_SECRET",
    "ZHIPU_API_KEY",
    "LEGAL_VERSION",
}
REQUIRED_MINIAPP_KEYS = {
    "VITE_API_BASE_URL",
    "VITE_AUTH_MODE",
    "VITE_LEGAL_VERSION",
    "VITE_OPERATOR_NAME",
    "VITE_AI_PROVIDER_NAME",
}
PLACEHOLDER_PARTS = (
    "example.com",
    "replace-with",
    "change-me",
    "你的",
    "wx0000000000000000",
)


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def is_placeholder(value: str) -> bool:
    lowered = value.lower()
    return not value or any(marker.lower() in lowered for marker in PLACEHOLDER_PARTS)


def missing_keys(values: dict[str, str], required: set[str]) -> list[str]:
    return sorted(key for key in required if not values.get(key))


def main() -> int:
    parser = argparse.ArgumentParser(description="食尽其用正式发布配置检查")
    parser.add_argument("--deploy-env", type=Path, default=Path(".env.deploy"))
    parser.add_argument(
        "--miniapp-env",
        type=Path,
        default=Path("miniapp/.env.production"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("miniapp/src/manifest.json"),
    )
    parser.add_argument(
        "--template",
        action="store_true",
        help="只检查示例文件结构，允许占位符和测试 AppID",
    )
    args = parser.parse_args()

    errors: list[str] = []
    for label, path in (
        ("服务器配置", args.deploy_env),
        ("小程序配置", args.miniapp_env),
        ("小程序清单", args.manifest),
    ):
        if not path.is_file():
            errors.append(f"缺少{label}文件：{path}")

    if errors:
        for error in errors:
            print(f"[失败] {error}")
        return 1

    deploy = read_env(args.deploy_env)
    miniapp = read_env(args.miniapp_env)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))

    for key in missing_keys(deploy, REQUIRED_DEPLOY_KEYS):
        errors.append(f"服务器配置缺少 {key}")
    for key in missing_keys(miniapp, REQUIRED_MINIAPP_KEYS):
        errors.append(f"小程序配置缺少 {key}")

    weixin_settings = manifest.get("mp-weixin", {}).get("setting", {})
    if weixin_settings.get("urlCheck") is not True:
        errors.append("正式小程序必须开启服务器域名校验")
    if manifest.get("uniStatistics", {}).get("enable") is not False:
        errors.append("首发版本必须显式关闭未披露的 uniStatistics")

    legal_version = deploy.get("LEGAL_VERSION", "")
    try:
        date.fromisoformat(legal_version)
    except ValueError:
        errors.append("LEGAL_VERSION 必须是 YYYY-MM-DD 格式的有效日期")
    if miniapp.get("VITE_LEGAL_VERSION") != legal_version:
        errors.append("前后端用户协议与隐私政策版本不一致")

    if not args.template:
        for key in sorted(REQUIRED_DEPLOY_KEYS):
            if is_placeholder(deploy.get(key, "")):
                errors.append(f"服务器配置 {key} 仍是占位值")
        for key in sorted(REQUIRED_MINIAPP_KEYS):
            if is_placeholder(miniapp.get(key, "")):
                errors.append(f"小程序配置 {key} 仍是占位值")

        app_id = deploy.get("WECHAT_APP_ID", "")
        manifest_app_id = manifest.get("mp-weixin", {}).get("appid", "")
        if not re.fullmatch(r"wx[0-9a-fA-F]{16}", app_id):
            errors.append("WECHAT_APP_ID 格式不正确")
        if manifest_app_id != app_id:
            errors.append("manifest.json 的微信 AppID 与服务器配置不一致")
        domain = deploy.get("API_DOMAIN", "")
        if "://" in domain or "/" in domain or "." not in domain:
            errors.append("API_DOMAIN 应填写不带协议和路径的完整域名")

        database_url = deploy.get("DATABASE_URL", "")
        if not database_url.startswith("mysql+pymysql://"):
            errors.append("DATABASE_URL 必须使用 MySQL PyMySQL 连接地址")
        redis_url = deploy.get("REDIS_URL", "")
        if not redis_url.startswith(("redis://", "rediss://")):
            errors.append("REDIS_URL 格式不正确")

        api_url = miniapp.get("VITE_API_BASE_URL", "")
        parsed_api_url = urlparse(api_url)
        if parsed_api_url.scheme != "https" or parsed_api_url.hostname != domain:
            errors.append("小程序 API 地址必须使用 HTTPS 且域名与 API_DOMAIN 一致")
        if miniapp.get("VITE_AUTH_MODE") != "wechat":
            errors.append("正式小程序必须使用微信登录模式")
        if miniapp.get("VITE_DEV_LOGIN_KEY") or miniapp.get("VITE_DEV_OPENID"):
            errors.append("正式小程序配置不能包含开发登录信息")


    if errors:
        for error in errors:
            print(f"[失败] {error}")
        print(f"共发现 {len(errors)} 个发布阻断项。")
        return 1

    message = "模板结构检查通过。" if args.template else "正式发布配置检查通过。"
    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
