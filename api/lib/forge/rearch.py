
def name_port(name):

    words = name.upper().split('-', 1)

    if len(words) == 1:
        words.append(words[0[1]])

    return int(f"{ord(words[0][0])}{ord(words[1][0])}")

def service(fields, values, forge):

    # Calculate the port

    if not fields["craft"].value:
        return

    port = name_port(fields["craft"].value)

    if "api" in fields["microservices"].value:
        fields.extend([
            {
                "name": "api",
                "default": "api"
            },
            {
                "name": "api_port",
                "default": 10000 + port
            },
            {
                "name": "api_debug_port",
                "default": 10000 + port - 32
            }
        ])
    else:
        for field in ["api", "api_port", "api_debug_port"]:
            if field in values:
                del values[field]

    if "daemon" in fields["microservices"].value:
        fields.extend([
            {
                "name": "daemon",
                "default": "daemon"
            },
            {
                "name": "daemon_debug_port",
                "default": 20000 + port - 32
            }
        ])
    else:
        for field in ["daemon", "daemon_port", "daemon_debug_port"]:
            if field in values:
                del values[field]

    if "gui" in fields["microservices"].value:
        fields.extend([
            {
                "name": "gui",
                "default": "gui"
            },
            {
                "name": "gui_port",
                "default": port
            }
        ])
    else:
        for field in ["gui", "gui_port"]:
            if field in values:
                del values[field]

    if "cron" in fields["microservices"].value:
        fields.extend([
            {
                "name": "cron",
                "default": "cron"
            },
            {
                "name": "cron_debug_port",
                "default": 30000 + port - 32
            }
        ])
    else:
        for field in ["cron", "cron_debug_port"]:
            if field in values:
                del values[field]
