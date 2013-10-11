SublimeLineMessages
===================

A generic sublime text plugin for tools that generate line enumerated content
that could be visible in the status bar or as regions - for example linters or
profilers

Configuration
-------------

Update your configuration to point at your pylint executable, like so:

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

Usage
-----

When editing python files, use the key-binding (ctrl-alt-l) to invoke the tools.
