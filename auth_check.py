#!/usr/bin/env python3
import sys
import os
import json

def main():
    # Argumente kommen von Nginx:
    # on_connect "/path/to/auth_check.py expected_key";
    expected_key = sys.argv[1]

    # Nginx-RTMP übergibt Variablen über ENV:
    # $name, $app, $addr, $flashver, $swfurl, $tcurl, $pageurl
    # Wichtige Variablen: $name = Stream-Key vom Publisher?
    # Hier muss ggf. geprüft werden, wie der Publisher den key übergibt.
    # Üblicherweise bei RTMP: rtmp://server:port/app/STREAMKEY
    # STREAMKEY = os.environ.get('name', '')

    incoming_app = os.environ.get('app', '')
    incoming_name = os.environ.get('name', '')

    # Wir erwarten, dass incoming_name == expected_key ist.
    if incoming_name == expected_key:
        sys.exit(0)  # Auth success
    else:
        sys.exit(1)  # Auth fail


if __name__ == "__main__":
    main()
