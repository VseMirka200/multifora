# Интеграция движков ArtCraft

Multifora подключает ArtCraft через официальные CLI, а не через запуск графических окон:

| Операция Multifora | CLI ArtCraft | Команда |
|---|---|---|
| Конвертация документов DOCX, ODT, RTF, TXT, HTML, Markdown в DOCX, ODT, RTF, TXT, HTML, Markdown или PDF | WordCraft CLI | `wordcraft-cli convert INPUT OUTPUT` |
| Конвертация изображений между форматами PhotoCraft | PhotoCraft CLI | `photocraft-cli convert INPUT OUTPUT` |
| Объединение PDF | PdfCraft CLI | `pdfcraft-cli combine INPUT... --out OUTPUT` |

## Установка CLI для Windows

На момент интеграции GitHub Releases ArtCraft публикуют Windows MSI/portable для графических приложений, но отдельные Windows CLI-архивы для всех трёх инструментов отсутствуют. Поэтому Multifora не может безопасно притворяться, что эти команды уже входят в установщик.

Соберите официальные CLI из исходников соответствующих проектов с Rust 1.95 или новее:

- PdfCraft: `cargo build --release -p pdfcraft-cli`
- PhotoCraft: `cargo build --release -p photocraft-cli`
- WordCraft: `cargo build --release -p wordcraft-cli`

Команды запускаются в корне соответствующего репозитория ArtCraft. Скопируйте полученные исполняемые файлы в каталог Multifora:

```text
bin/
  artcraft/
    pdfcraft-cli.exe
    photocraft-cli.exe
    wordcraft-cli.exe
```

Также можно хранить бинарные файлы в другом месте и задать переменные окружения:

- `MULTIFORA_PDFCRAFT_CLI`
- `MULTIFORA_PHOTOCRAFT_CLI`
- `MULTIFORA_WORDCRAFT_CLI`

Приоритет имеет явно заданный путь. Далее проверяется `bin/artcraft` рядом с приложением и затем `PATH`.

## Важные ограничения текущего этапа

- EPUB и часть редких документных преобразований пока остаются на прежнем пути: WordCraft не заявляет их поддержку.
- PDF → изображения и PDF → ODT пока используют отдельные существующие обработчики.
- Сжатие PDF и изображений ещё не переведено на ArtCraft.
- PhotoCraft в README заявляет форматы, которые отличаются от текущего реестра Multifora; реестр будет сужаться только после проверки тестов и реальных round-trip образцов.
- Пока CLI не входят в сборку, существующие обработчики остаются резервными. PhotoCraft используется только для проверяемого подмножества форматов; остальные операции сохраняют прежний обработчик. Ошибки запущенного CLI не скрываются резервным обработчиком.

Старые зависимости пока намеренно не удаляются: несколько оставшихся операций ещё используют их. Удалять их до миграции этих операций означало бы сломать функции программы.
