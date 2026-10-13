# Windows release process

Set `APP_VERSION` to the unprefixed release number, run Windows tests and `mkdocs build --strict`, then push the matching `v<version>` tag. The Release workflow creates the installer, portable ZIP, SHA-256 files, and changelog in GitHub Releases. Download and smoke-test both deliverables after publication.
