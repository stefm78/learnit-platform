# One-time RC715 package upload

This directory is temporary and will be deleted automatically by the import workflow.

Upload the exact outer package supplied for RC715 into this directory using the GitHub web interface on branch `import/rc715-development-baseline`.

Expected package SHA-256:

```text
f5e1bd5b17a9e16a6e14962d6db18632abb954bf71a68935c9186e8b1c190033
```

The filename may vary; the workflow selects the package by SHA-256, locates the nested source archive by its own SHA-256, safely extracts it, rebuilds the artifact, runs the mandatory checks, removes this directory and the one-shot workflows, and commits only the source and forensic evidence.

Do not extract, edit, recompress, or rename files inside the ZIP before upload.
