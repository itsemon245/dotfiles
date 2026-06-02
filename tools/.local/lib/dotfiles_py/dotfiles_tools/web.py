"""Web development helper commands."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from . import process
from .cli import ToolError, add_dry_run


def main_vhost(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vhost", description="Create an Apache virtual host.")
    parser.add_argument("domain", nargs="?", help="domain name, such as example.com")
    parser.add_argument("doc_root", nargs="?", help="document root path")
    parser.add_argument("--web-user", default=os.environ.get("VHOST_WEB_USER", "emon"))
    parser.add_argument("--web-group", default=os.environ.get("VHOST_WEB_GROUP", "www-data"))
    add_dry_run(parser)
    args = parser.parse_args(argv)

    if not args.dry_run and os.geteuid() != 0:
        raise ToolError("please run as root or with sudo")

    domain = args.domain or input("Enter the domain name (e.g., example.com): ").strip()
    if not domain:
        raise ToolError("domain is required")
    default_doc_root = f"/var/www/{domain}/"
    doc_root = args.doc_root
    if not doc_root:
        typed = input(f"Enter the document root (default: {default_doc_root}): ").strip()
        doc_root = typed or default_doc_root

    config_path = Path("/etc/apache2/sites-available") / f"{domain}.conf"
    config = f"""<VirtualHost *:80>
    ServerAdmin webmaster@{domain}
    ServerName {domain}
    DocumentRoot {doc_root}

    <Directory {doc_root}>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    ErrorLog ${{APACHE_LOG_DIR}}/{domain}_error.log
    CustomLog ${{APACHE_LOG_DIR}}/{domain}_access.log combined
</VirtualHost>
"""
    commands = [
        ["mkdir", "-p", doc_root],
        ["chown", "-R", f"{args.web_user}:{args.web_group}", doc_root],
        ["chmod", "-R", "755", doc_root],
    ]
    for command in commands:
        process.run(command, check=not args.dry_run, dry_run=args.dry_run)

    if args.dry_run:
        print(f"+ append to /etc/hosts: 127.0.0.1 {domain}")
        print(f"+ write {config_path}")
        print(config.rstrip())
    else:
        with Path("/etc/hosts").open("a", encoding="utf-8") as hosts:
            hosts.write(f"127.0.0.1 {domain}\n")
        config_path.write_text(config, encoding="utf-8")

    process.run(["a2ensite", f"{domain}.conf"], check=not args.dry_run, dry_run=args.dry_run)
    process.run(["systemctl", "reload", "apache2"], check=not args.dry_run, dry_run=args.dry_run)
    print("Virtual host created successfully.")
    print(f"You can access the site at http://{domain}/")
    return 0

