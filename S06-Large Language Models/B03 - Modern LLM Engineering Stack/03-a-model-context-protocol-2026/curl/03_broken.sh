#!/usr/bin/env bash
# The one that teaches the most: an ordinary exception, not a ToolError.
#
# `broken_on_purpose` raises KeyError with a message containing a fake internal
# path. Watch what the model gets, then look at the SERVER's terminal.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
expect 'isError: true, and the text is ONLY:
          "Error executing tool broken_on_purpose"
        The KeyError message — including the internal path — is GONE.

        NOW LOOK AT THE SERVER TERMINAL. The full traceback is there, on stderr.
        The information was not lost; it was deliberately not SENT. That is the
        right default: your exception text might carry a connection string, a
        file path, a stack detail. The SDK will not hand that to a model unless
        you say it is safe by raising ToolError.'
exec ./call.sh broken_on_purpose '{"slug": "latte"}' 34
