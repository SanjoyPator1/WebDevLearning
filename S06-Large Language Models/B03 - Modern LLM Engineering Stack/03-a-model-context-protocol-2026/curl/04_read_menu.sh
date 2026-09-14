#!/usr/bin/env bash
# The document a model would actually read.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
expect 'contents[0] with `uri`, `mimeType: "text/markdown"` and `text` holding the
        whole menu table.

        Read the table as the model would. The Slug column is there so that a model
        which has read this document can call get_drink or read cafe://drinks/<slug>
        with the exact argument and never guess. The dashes say "not sold in this
        size" explicitly, because a blank cell is easy to misread as unknown.

        ttlMs: 600000 on a resources/read is the highest-value cache hint on this
        server — a document fetch is exactly what an HTTP cache was built for.'
exec ./read.sh cafe://menu 203
