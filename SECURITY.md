# Security

This is a local authoring tool, not a multi-tenant sandbox. Do not run it as an administrator against untrusted projects. The built-in R36 engine is trusted package code; JSON does not choose arbitrary modules or shell commands.

Project file paths are relative, contained after symlink resolution, and reject drive/UNC/traversal forms. Imports validate image sizes and formats; glyphs have point/canvas limits. Reports and approvals are explicit local attestations, not authentication tokens. A person who can rewrite the installed code can change its behavior.

No cloud upload, paid model fallback, telemetric background task or stored API credential is implemented. Install dependencies only from a trusted package environment. Reference-image text is data, not executable instructions.

Do not disclose a credential or private data in a public issue. Use an appropriate private channel to the repository owner before discussing a sensitive vulnerability. GitHub private advisory/reporting availability depends on repository settings; it is not promised by this document.
