# Выпуск Windows-версии

1. Обновите `APP_VERSION` в `app/core/app_identity.py` до версии без префикса `v`.
2. Запустите Windows-тесты и `mkdocs build --strict`.
3. Создайте и отправьте тег `v<версия>`.
4. Workflow **Release** соберёт installer, portable ZIP, контрольные суммы и GitHub Release.

В релиз публикуются `Multifora-Setup-<версия>.exe` и `.sha256`, portable ZIP и `.sha256`, а также `CHANGELOG.md`. После публикации скачайте оба варианта, проверьте SHA-256 и запуск. Не изменяйте проверенные артефакты вручную.
