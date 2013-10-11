SublimePylint
=============

A (very) simple sublime-text (3) plugin that runs "pylint", the python linter.


Configuration
-------------

Update your configuration to point at your pylint executable, like so:

```
  {
      "pylint_command": "/work/anaconda/bin/pylint"
  }
```

Usage
-----

When editing python files, use the key-binding (ctrl-alt-l) to invoke the linter, 
which will mark all errors.
