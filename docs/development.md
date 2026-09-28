# Разработка

[К оглавлению](README.md)

## Окружение

Проект рассчитан на Windows и Python 3.11 или новее.

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe multifora_start.py
```

## Структура

- `multifora_start.py` — точка входа и маршрутизация в единственный экземпляр.
- `app/ui` — окно, компоненты, стили и UI-mixin-классы.
- `app/core` — настройки, форматы, шаблоны и IPC.
- `core/workers` — фоновые файловые операции.
- `tests` — тесты `unittest`.
- `docs` — документация.

## Тесты

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.venv\Scripts\python.exe -m unittest discover -s tests
```

## Сборка

Официальный выпуск собирается GitHub Actions при публикации тега `v*`. Workflow запускает тесты, собирает приложение с PyInstaller, создаёт установщик Inno Setup и публикует:

- Windows x64 ZIP и его SHA-256;
- `Multifora-Setup-<версия>.exe` и его SHA-256;
- список изменений.

Перед созданием тега обновите `APP_VERSION` в `app/core/app_identity.py`. Версия тега без префикса `v` должна точно совпадать с `APP_VERSION`, например `v0.10.0` и `0.10.0`. Несовпадение останавливает сборку релиза.

Встроенное обновление работает только при наличии установщика и его контрольной суммы среди файлов GitHub Release. Установщик использует постоянный `AppId`, поэтому новая версия обновляет существующую установку в той же папке.

При изменении поведения обновляйте соответствующий документ и добавляйте тест. Дополнительные требования описаны в [CONTRIBUTING.md](CONTRIBUTING.md).
