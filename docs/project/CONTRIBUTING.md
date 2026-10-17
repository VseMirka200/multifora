# Участие в разработке

Спасибо за интерес к Мультифоре. Принимаются исправления ошибок, тесты, улучшения интерфейса и документации, а также заранее обсуждённые функции.

## Перед началом

- Прочитайте [Кодекс поведения](CODE_OF_CONDUCT.md).
- Не публикуйте уязвимости в issue или Pull Request: используйте [политику безопасности](SECURITY.md).
- Для обычных вопросов, ошибок и предложений используйте [шаблоны обращений](https://github.com/VseMirka200/multifora/issues/new/choose).

## Среда разработки

Проект рассчитан на Windows и Python 3.11 или новее.

```powershell
git clone https://github.com/VseMirka200/multifora.git
cd multifora
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe multifora_start.py
```

Microsoft Word требуется только для части операций с документами. Ghostscript поставляется с готовой Windows-сборкой и нужен для сжатия PDF.

## Как предложить изменение

1. Создайте ветку от актуальной `main`.
2. Ограничьте Pull Request одной понятной задачей.
3. Добавьте или обновите тест для изменённого поведения.
4. Запустите проверки:

   ```powershell
   $env:QT_QPA_PLATFORM = "offscreen"
   .\.venv\Scripts\python.exe -m pytest -q
   .\.venv\Scripts\python.exe -m ruff check .
   ```

5. В Pull Request опишите проблему, решение, способ проверки и известные ограничения. Для заметных изменений интерфейса приложите снимки экрана.

Не добавляйте в коммиты виртуальные окружения, сборки, кэши, журналы, токены, ключи, личные данные или пользовательские документы.

Все изменения в `main` проходят через Pull Request. Windows-сборка с установщиком и portable-версией создаётся автоматически для каждого PR в `main`.

## Лицензия вкладов

Отправляя вклад, вы соглашаетесь распространять его на условиях [лицензии MIT](../../LICENSE).
