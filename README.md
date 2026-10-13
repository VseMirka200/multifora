<p align="center">
  <img src="assets/icon.svg" alt="Логотип Мультифоры" width="144" height="144">
</p>

<h1 align="center">Мультифора</h1>

<p align="center">
  Пакетная обработка файлов для Windows — локально, быстро и без облачных сервисов.
</p>

<p align="center">
  <a href="https://github.com/VseMirka200/multifora/releases/latest"><img src="https://img.shields.io/github/v/release/VseMirka200/multifora?display_name=tag&sort=semver" alt="Последний выпуск"></a>
  <a href="https://github.com/VseMirka200/multifora/actions/workflows/ci.yml"><img src="https://github.com/VseMirka200/multifora/actions/workflows/ci.yml/badge.svg" alt="Проверки"></a>
  <img src="https://img.shields.io/badge/platform-Windows-0078D4" alt="Платформа: Windows">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB" alt="Python 3.11+">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-2ea44f" alt="Лицензия MIT"></a>
</p>

<p align="center">
  <a href="https://github.com/VseMirka200/multifora/releases/latest"><strong>Скачать</strong></a> ·
  <a href="https://vsemirka200.github.io/multifora/">Документация</a> ·
  <a href="https://vsemirka200.github.io/multifora/en/">English</a> ·
  <a href="https://github.com/VseMirka200/multifora/issues/new/choose">Сообщить об ошибке</a>
</p>

## Что умеет Мультифора

| Задача | Возможности |
| --- | --- |
| Переименование | Шаблоны, нумерация, даты, EXIF, размеры изображений, замена текста и регулярные выражения. |
| Конвертация | Документы и изображения; выбор источника, результата и папки сохранения. |
| Объединение | PDF с PDF или DOCX с DOCX — в порядке очереди. |
| Сжатие | Изображения и PDF с настройкой качества и безопасным сохранением результата. |
| Очередь | Перетаскивание, поиск, фильтрация, сортировка, ручной порядок и добавление из Проводника. |

Все операции выполняются на вашем компьютере. Приложение не отправляет рабочие файлы в облако.

## Установка

### Рекомендуемый способ

1. Откройте [последний выпуск](https://github.com/VseMirka200/multifora/releases/latest).
2. Скачайте `Multifora-Setup-<версия>.exe`.
3. Запустите установщик и откройте Мультифору через меню «Пуск».

### Portable-версия

Скачайте ZIP-архив из выпуска, полностью распакуйте его в постоянную папку и запустите `Multifora.exe`. Не запускайте EXE прямо из архива: рядом с ним расположены необходимые компоненты.

В каждом выпуске опубликованы SHA-256 суммы. Для ручной проверки загрузки используйте:

```powershell
Get-FileHash .\Multifora-Setup-<версия>.exe -Algorithm SHA256
```

## Быстрый старт

1. Добавьте файлы или папку — кнопкой, перетаскиванием или из контекстного меню Windows.
2. Проверьте очередь и при необходимости измените порядок файлов.
3. Выберите операцию: **Переименование**, **Конвертация**, **Объединение** или **Сжатие**.
4. Настройте параметры и изучите предварительный результат.
5. Запустите операцию и откройте созданные файлы для проверки.

> Перед заменой исходников сделайте резервную копию. Это особенно важно для пакетного переименования, конвертации и сжатия с перезаписью.

## Форматы и требования

- **Документы:** DOC, DOCX, PDF, ODT, RTF, TXT, HTML, Markdown, EPUB, FB2, XPS и MOBI.
- **Изображения:** JPG/JPEG, PNG, WEBP, BMP, TIFF, GIF, ICO, TGA, AVIF, HEIC/HEIF, SVG, PSD и другие форматы.
- **Система:** Windows 10/11, 64-bit. Для запуска из исходного кода нужен Python 3.11+.
- **Microsoft Word:** требуется для части операций с офисными документами, где необходимо сохранить сложное оформление.

Полный список входных и выходных форматов, особенности преобразований и инструкции по устранению неполадок есть в [документации](https://vsemirka200.github.io/multifora/conversion/).

## Разработка

```powershell
git clone https://github.com/VseMirka200/multifora.git
cd multifora
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe multifora_start.py
```

Проверки:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m ruff check .
```

Документация собирается отдельно:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-docs.txt
.\.venv\Scripts\mkdocs.exe build --strict
```

## Поддержка и участие

- [Документация для пользователей](https://vsemirka200.github.io/multifora/)
- [Руководство для участников](docs/CONTRIBUTING.md)
- [Политика безопасности](docs/SECURITY.md)
- [Правила защиты репозитория и релизов](docs/REPOSITORY_SECURITY.md)
- [Кодекс поведения](docs/CODE_OF_CONDUCT.md)
- [Сообщить об ошибке или предложить улучшение](https://github.com/VseMirka200/multifora/issues/new/choose)
- [Конфиденциально сообщить об уязвимости](https://github.com/VseMirka200/multifora/security/advisories/new)

## Лицензия

Мультифора распространяется по [лицензии MIT](LICENSE).
