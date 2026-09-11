<p align="center">
  <img src="assets/icon.svg" alt="Иконка приложения Мультифора" width="160" height="160">
</p>

<h1 align="center">Мультифора</h1>

<p align="center">Пакетная работа с файлами в Windows</p>

<p align="center">
  <a href="https://github.com/VseMirka200/multifora/actions/workflows/ci.yml"><img alt="Тесты" src="https://github.com/VseMirka200/multifora/actions/workflows/ci.yml/badge.svg"></a>
</p>

<p align="center">
  <a href="https://github.com/VseMirka200/multifora/releases/latest"><img alt="Скачать" src="https://img.shields.io/badge/СКАЧАТЬ-ПОСЛЕДНЮЮ_ВЕРСИЮ-1f883d?style=for-the-badge"></a>
  <a href="https://github.com/VseMirka200/multifora"><img alt="Исходный код" src="https://img.shields.io/badge/ИСХОДНЫЙ_КОД-GITHUB-6f42c1?style=for-the-badge"></a>
  <a href="https://github.com/VseMirka200/multifora/releases"><img alt="Релизы" src="https://img.shields.io/badge/РЕЛИЗЫ-ОТКРЫТЬ-0969da?style=for-the-badge"></a>
  <a href="https://github.com/VseMirka200/multifora/issues"><img alt="Задачи" src="https://img.shields.io/badge/ЗАДАЧИ-ОТКРЫТЬ-57606a?style=for-the-badge"></a>
  <a href="https://github.com/VseMirka200/multifora/issues/new"><img alt="Сообщить об ошибке" src="https://img.shields.io/badge/СООБЩИТЬ_ОБ_ОШИБКЕ-СОЗДАТЬ-d1242f?style=for-the-badge"></a>
</p>

Мультифора — приложение для Windows, предназначенное для одновременной работы с большим количеством файлов. Оно объединяет основные операции с документами и изображениями в одном интерфейсе на PyQt и позволяет предварительно просматривать изменения перед их применением.

## Возможности

- Пакетное переименование файлов с шаблонами, нумерацией, предварительным просмотром, отменой и повтором действий.
- Замена по регулярным выражениям, преобразование регистра и проверка конфликтов имён до запуска.
- Пользовательские шаблоны с токенами имени, номера, дат файла, EXIF и размеров изображения.
- Конвертация документов и изображений между поддерживаемыми форматами.
- Объединение PDF и документов Word в один PDF, а также объединение файлов DOCX в один документ DOCX.
- Сжатие PDF и изображений с настраиваемым качеством.
- Удаление отдельных полей или всех метаданных из файлов PDF, DOC, DOCX и ODT.
- Добавление файлов и папок через диалог выбора, перетаскивание, аргументы командной строки или контекстное меню Windows.
- Поиск, фильтрация, сортировка и изменение порядка файлов в очереди.
- Светлая, тёмная и системная темы оформления.
- Проверка обновлений через GitHub Releases.
- Профили параметров для всех операций.

## Шаблоны переименования

В пользовательском шаблоне доступны токены `{name}`, `{ext}`, `{num}`, `{date}`, `{created}`, `{modified}`, `{exif_date}`, `{width}` и `{height}`. Например:

```text
{exif_date}_{num:04d,start=1,step=1}_{name}
```

Для сложной замены выберите шаблон **«Регулярное выражение»**. Поддерживаются группы захвата (`\1`) и поиск без учёта регистра. Перед запуском приложение проверяет запрещённые Windows-имена, совпадающие целевые имена и уже существующие файлы.

## Скачивание

Скачайте последнюю готовую сборку со страницы [GitHub Releases](https://github.com/VseMirka200/multifora/releases/latest), распакуйте архив и запустите `Multifora.exe`.

Приложение предназначено для Windows. Для операций, использующих автоматизацию Word, включая преобразование DOC или DOCX в PDF, требуется Microsoft Word. Для сжатия PDF необходим [Ghostscript](https://ghostscript.com/releases/gsdnld.html); путь к его исполняемому файлу также можно указать в настройках приложения.

## Запуск из исходного кода

Потребуются Windows и Python 3.11 или новее.

```powershell
git clone https://github.com/VseMirka200/multifora.git
cd multifora
.\start_multifora.bat
```

Скрипт запуска создаёт `.venv`, устанавливает пакеты из `requirements.txt` и запускает приложение. Для ручной настройки окружения выполните:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe multifora_start.py
```

## Сборка приложения для Windows

Запустите скрипт сборки из корня репозитория:

```powershell
.\scripts\build_app.bat
```

Скрипт установит PyInstaller и сохранит готовое приложение в папку `dist\Multifora`.

## Разработка

Для запуска всех тестов используйте:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

GitHub Actions запускает тесты на Windows для каждого push и Pull Request. При отправке тега вида `v1.2.3` release workflow собирает ZIP-архив приложения, вычисляет SHA-256 и создаёт changelog из коммитов после предыдущего тега.

Перед отправкой изменений прочитайте [руководство для участников](CONTRIBUTING.md). Участие в проекте регулируется [Кодексом поведения](CODE_OF_CONDUCT.md). Информацию об уязвимостях необходимо передавать в соответствии с [Политикой безопасности](SECURITY.md).

## Ссылки проекта

- [Последний релиз](https://github.com/VseMirka200/multifora/releases/latest)
- [Трекер задач](https://github.com/VseMirka200/multifora/issues)
- [Руководство для участников](CONTRIBUTING.md)
- [Политика безопасности](SECURITY.md)
- [Кодекс поведения](CODE_OF_CONDUCT.md)
