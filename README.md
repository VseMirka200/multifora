<p align="center">
  <img src="assets/icon.svg" alt="Иконка Multifora" width="160" height="160">
</p>

<h1 align="center">Multifora</h1>

<p align="center">Пакетные инструменты для работы с файлами в Windows</p>

<p align="center">
  <a href="https://github.com/VseMirka200/multifora/archive/refs/heads/main.zip"><img alt="Скачать" src="https://img.shields.io/badge/-СКАЧАТЬ-555555?style=for-the-badge&logo=github"></a>&nbsp;
  <a href="https://github.com/VseMirka200/multifora/releases"><img alt="Релизы" src="https://img.shields.io/badge/-РЕЛИЗЫ-2468dc?style=for-the-badge"></a>&nbsp;
  <a href="https://github.com/VseMirka200/multifora/issues/new"><img alt="Сообщить об ошибке" src="https://img.shields.io/badge/-ОШИБКА-dc3545?style=for-the-badge&logo=github"></a>
</p>

**Multifora** — настольное приложение для Windows, которое помогает выполнять типовые операции сразу над большим количеством файлов. Интерфейс построен на PyQt6, а большинство операций можно предварительно проверить до применения.

## Возможности

- пакетное переименование по шаблонам с нумерацией, предпросмотром, отменой и повтором;
- конвертация документов и изображений между поддерживаемыми форматами;
- объединение PDF и Word-документов в PDF, а также объединение DOCX-файлов в один DOCX;
- сжатие PDF и изображений с настраиваемым качеством;
- удаление выбранных полей метаданных или всех метаданных из PDF, DOC, DOCX и ODT;
- добавление файлов и папок через диалог, drag-and-drop, аргументы командной строки и контекстное меню Windows;
- поиск, фильтрация, сортировка и изменение порядка файлов в очереди;
- светлая, тёмная и системная темы;
- проверка обновлений через GitHub;
- экспорт изображений в автономный SVG со встроенным растровым содержимым;
- единый набор SVG-иконок для типов файлов и интерфейса.

## Скачать

Готовые сборки, если они опубликованы, находятся в [GitHub Releases](https://github.com/VseMirka200/multifora/releases). Исходный код можно скачать кнопкой **«СКАЧАТЬ»** выше.

## Запуск из исходного кода

Требуются Windows и Python 3.11 или новее.

```powershell
git clone https://github.com/VseMirka200/multifora.git
cd multifora
.\start_multifora.bat
```

Скрипт создаёт `.venv`, устанавливает зависимости из `requirements.txt` и запускает приложение.

Ручной запуск:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe multifora_start.py
```

## Сборка приложения

Из корня репозитория запустите:

```powershell
.\scripts\build_app.bat
```

Скрипт устанавливает PyInstaller, подготавливает значок Windows и создаёт сборку в `dist\Multifora`.

## Дополнительные зависимости

Для некоторых операций нужны внешние программы:

- **Microsoft Word** — для конвертации DOC/DOCX через автоматизацию Word;
- **Ghostscript** — для сжатия PDF. Путь к исполняемому файлу можно указать в настройках приложения.

## Разработка

Запуск тестов:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Перед отправкой изменений ознакомьтесь с [CONTRIBUTING.md](CONTRIBUTING.md). Правила общения описаны в [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), а сообщения об уязвимостях — в [SECURITY.md](SECURITY.md).

## Полезные ссылки

- [Репозиторий](https://github.com/VseMirka200/multifora)
- [Релизы](https://github.com/VseMirka200/multifora/releases)
- [Сообщить об ошибке](https://github.com/VseMirka200/multifora/issues/new)
- [Руководство участника](CONTRIBUTING.md)
- [Политика безопасности](SECURITY.md)
- [Кодекс поведения](CODE_OF_CONDUCT.md)
