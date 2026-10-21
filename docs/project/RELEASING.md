# Выпуск Windows-версии

1. Обновите `APP_VERSION` в `app/core/app_identity.py` до новой версии без префикса `v`.
2. Откройте и слейте Pull Request в `main`.
3. Workflow [Release](../../.github/workflows/release.yml) после слияния повторно выполнит линт и тесты, соберёт установщик, portable ZIP, контрольные суммы и создаст GitHub Release с тегом `v<версия>`.
4. Скачайте опубликованные файлы, проверьте SHA-256 и запуск обоих вариантов.

Если тег этой версии уже существует, публикация остановится: перед следующим релизом увеличьте `APP_VERSION` в PR.

В релиз входят `Multifora-Setup-<версия>.exe` и его `.sha256`, portable ZIP и его `.sha256`, а также `CHANGELOG.md`. Для тихой установки используйте `Multifora-Setup-<версия>.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART`; Windows может запросить подтверждение UAC. Не изменяйте артефакты после проверки.
