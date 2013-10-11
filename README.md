SublimeLineMessages
===================

A generic sublime text plugin for tools that generate line enumerated content
that could be visible in the status bar or as regions - for example linters or
profilers

Configuration
-------------

Update your configuration to point at your tool executables, like so:

```
{
    "tools": [
        {
            "name": "pylint",
            "command": "/usr/bin/pylint",
            "options": "--msg-template=\"{path}:{line}: [{msg_id}] {msg}\" -r no",
            "parser": "(.*):([1-9]+):(.*)",
            "marker": "plain"
        },
        {
            "name": "pep8",
            "command": "/usr/bin/pep8",
            "options": "",
            "parser": "(.*):.*:([1-9]+):(.*)",
            "marker": "plain"
        }
    ],
    "verbose": true
}
```

Note the user of a parser, which is used to form three important components:

    1. The filename.
    2. The line number containing the message.
    3. The message (lint output).

Usage
-----

When editing python files, use the key-binding (ctrl-alt-l) to invoke the tools.
