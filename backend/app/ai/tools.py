RUN_COMMAND_TOOL = {
    "type": "function",
    "function": {
        "name": "run_command",
        "description": "Выполнить одну команду в терминале устройства",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Текст команды"},
            },
            "required": ["command"],
        },
    },
}
