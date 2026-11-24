import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from docx import Document
from PIL import Image
from pypdf import PdfReader, PdfWriter
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QDialog,
    QFrame,
    QPlainTextEdit,
    QStyle,
    QStyleOptionButton,
    QWidget,
)

from app.ui.operation_progress import OperationProgressDialog
from app.ui.typography import BODY_PX, CAPTION_PX, FONT_FAMILY, SECTION_PX, TITLE_PX
from app.ui.ui_components import setup_standard_action_button
from app.ui.ui_icons import SUPPORT_ICON_SIZE, UI_ICON_SIZE, ui_icon
from app.ui.ui_main import MultiforaMainWindow
from app.workers.operation_worker import OperationWorker
from core.file_models import FileItem
from core.operation_requests import ConversionRequest
from core.operation_result import OperationResult


@pytest.fixture
def window(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("app.core.settings.get_settings_file_path", lambda: str(tmp_path / "settings.json"))
    for name in (
        "apply_shortcut_settings", "ensure_context_menu_registration", "process_startup_queue",
        "check_updates_on_startup", "create_ipc_server", "init_logging",
    ):
        monkeypatch.setattr(MultiforaMainWindow, name, lambda *_args, **_kwargs: None)
    main = MultiforaMainWindow()
    main.show()
    app.processEvents()
    yield main
    main.queue_timer.stop()
    main._queue_paths_refresh_timer.stop()
    main._settings_save_timer.stop()
    if main.file_worker and main.file_worker.isRunning():
        main.file_worker.request_cancel()
        assert main.file_worker.wait(5000)
    main.merge_pages_panel.stop()
    main.deleteLater()


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_all_tabs_use_application_typography(window, theme):
    window.apply_theme_mode(theme)
    fonts = set()
    for index in range(window.operations_tab_bar.count()):
        window.operations_tab_bar.setCurrentIndex(index)
        QApplication.processEvents()
        for widget in window.findChildren(QWidget):
            if widget.isVisible():
                font = widget.font()
                fonts.add((font.family(), font.pixelSize()))
    assert fonts == {(FONT_FAMILY, size) for size in (CAPTION_PX, BODY_PX, SECTION_PX, TITLE_PX)}


@pytest.mark.parametrize("width", [900, 1200])
def test_operation_footer_buttons_stay_in_place(window, width):
    window.resize(width, 650)
    panel = window.operation_result_panel
    positions = []
    for index in range(4):
        window.operations_tab_bar.setCurrentIndex(index)
        QApplication.processEvents()
        active = window.launch_buttons[window.operations_tab_bar.tabData(index)]
        assert panel.launch_stack.currentWidget() is active
        buttons = (*panel.action_buttons, active)
        assert all(button.isVisible() for button in buttons)
        positions.append([(b.mapTo(window, QPoint()), b.size()) for b in buttons])
    assert positions == [positions[0]] * 4


def test_merge_empty_queue_drop_zone_mentions_supported_formats(window):
    merge_index = next(
        index
        for index in range(window.operations_tab_bar.count())
        if window.operations_tab_bar.tabData(index) == "merge"
    )
    window.operations_tab_bar.setCurrentIndex(merge_index)
    QApplication.processEvents()
    assert window.drop_zone_controls.isVisible()
    assert window.drop_zone_hint_label.text() == "Перетащите PDF или DOCX сюда"




def test_merge_empty_queue_drop_zone_centered_in_visible_merge_panel(window):
    merge_index = next(
        index
        for index in range(window.operations_tab_bar.count())
        if window.operations_tab_bar.tabData(index) == "merge"
    )
    window.operations_tab_bar.setCurrentIndex(merge_index)
    QApplication.processEvents()
    surface = window.merge_pages_panel
    center = surface.mapToGlobal(surface.rect().center())
    card = window.drop_zone_controls
    actual = card.mapToGlobal(card.rect().center())
    assert card.width() < surface.width()
    assert (actual - center).manhattanLength() <= 2
    # Внешние документы можно бросать по всей панели, не только в оверлей.
    assert surface.acceptDrops()
    assert window.merge_pages_panel.pages.acceptDrops()
    assert window.merge_pages_panel.pages.viewport().acceptDrops()
    # Проверяем фактическую область отрисовки, а не абстрактную ширину:
    # сначала загружаются иконки, потом Qt считает доступную ширину подписи.
    for theme in ("dark", "light"):
        window.apply_theme_mode(theme)
        QApplication.processEvents()
        for button in (window.btn_add_files, window.btn_add_folder):
            option = QStyleOptionButton()
            button.initStyleOption(option)
            content = button.style().subElementRect(
                QStyle.SubElement.SE_PushButtonContents, option, button
            )
            icon_width = button.icon().actualSize(button.iconSize()).width()
            needed = button.fontMetrics().horizontalAdvance(button.text()) + 5
            if icon_width:
                needed += icon_width + 5
            assert content.width() >= needed
            assert not button.icon().isNull()
            assert card.rect().contains(button.geometry())
        assert not window.btn_add_files.geometry().intersects(window.btn_add_folder.geometry())

def test_empty_queue_controls_centered_in_file_viewport(window):
    assert window.list_files.model().rowCount() == 0
    assert not window.list_files.indexAt(QPoint(5, 5)).isValid()
    for width, height in ((900, 600), (1200, 800)):
        window.resize(width, height)
        QApplication.processEvents()
        viewport = window.list_files.viewport()
        center = viewport.mapToGlobal(viewport.rect().center())
        card = window.drop_zone_controls
        actual = card.mapToGlobal(card.rect().center())
        assert card.width() < viewport.width()
        assert (actual - center).manhattanLength() <= 2


@pytest.mark.parametrize("width", [900, 1200])
def test_operation_panels_share_geometry(window, width):
    window.resize(width, 650)
    window.combo_templates.setCurrentText("Добавить текст")
    window.template_add_text.setFixedHeight(140)
    QTest.qWait(30)
    bounds = []
    heights = []
    fields = (window.combo_templates, window.convert_file_type_combo, window.combo_compress_type)
    field_positions = []
    for index in range(4):
        window.operations_tab_bar.setCurrentIndex(index)
        QApplication.processEvents()
        page = window.operations_stack.currentWidget()
        card = page.findChild(QFrame, "operation_options")
        bounds.append((card.mapTo(window, QPoint()), card.width()))
        heights.append(window.operations_stack.height())
        if index < len(fields):
            field_positions.append(fields[index].mapTo(window, QPoint()))
    assert bounds == [bounds[0]] * 4
    assert all(height < heights[0] for height in heights[1:]), heights
    window.operations_tab_bar.setCurrentIndex(0)
    QApplication.processEvents()
    assert window.template_add_text.height() == 140
    assert window.operations_stack.height() > max(heights[1:])
    assert field_positions == [field_positions[0]] * 3
    for index, content in ((4, window.settings_panel_widget), (5, window.support_page)):
        window.operations_tab_bar.setCurrentIndex(index)
        QApplication.processEvents()
        assert content.mapTo(window, QPoint()) == bounds[0][0]


def test_queue_uses_only_checkmarks_and_respects_filters(window, tmp_path):
    assert window._list_header_layout.count() == 3
    panel = window.operation_result_panel
    assert not panel.isHidden()
    assert all(not button.isHidden() and not button.isEnabled() for button in panel.action_buttons)
    assert not window.drop_zone_controls.isHidden()
    source = tmp_path / "first.txt"
    source.write_bytes(b"a" * 1024)
    other = tmp_path / "second.txt"
    other.write_bytes(b"b" * 2_097_152)
    window.add_files([str(source), str(other)])
    assert window.drop_zone_controls.isHidden()
    QApplication.processEvents()

    table = window.list_files
    name_index = table.model().index(1, table.model().COLUMN_NAME)
    QTest.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, pos=table.visualRect(name_index).center())
    assert not table.selectionModel().selectedIndexes()
    assert window.label_item_size.text() == "Отмечено: 0"
    table.select_paths([str(other)])
    assert "2.00 МБ" in window.label_item_size.text()
    table.clearSelection()
    assert len(window._get_operation_file_items()) == 2
    model = window.list_files.model()
    model.setData(model.index(0, model.COLUMN_CHECK), Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
    window.input_search.setText("second")
    QApplication.processEvents()
    assert window._get_operation_file_items() == []

    window.input_search.setText("unmatched")
    assert window.drop_zone_hint_label.text() == "Ничего не найдено"
    assert not window.btn_reset_queue_filters.isHidden()
    window.btn_reset_queue_filters.click()
    assert len(model.files()) == 2
    assert window.drop_zone_controls.isHidden()


def test_cancelled_result_keeps_queue_and_published_file(window, tmp_path):
    source = tmp_path / "first.docx"
    source.write_bytes(b"source")
    output = tmp_path / "first.pdf"
    output.write_bytes(b"example")
    window.add_files([str(source)])
    window.auto_clear_enabled_checkbox.setChecked(True)
    window.auto_clear_convert_checkbox.setChecked(True)
    window._operations.last_request = ConversionRequest("docx_to_pdf", "PDF", "alongside", "")
    worker = OperationWorker()
    worker.finished.connect(window.on_operation_finished)
    worker.request_cancel()
    worker._emit_finished([FileItem(str(output))])

    assert {item.path for item in window.files} == {str(source), str(output)}
    assert "Операция отменена" in window.operation_result_panel.summary.text()
    assert not window.operation_result_panel.open_result.isHidden()
    assert window.operation_result_panel.result.outcome == "cancelled"


def test_conversion_uses_checked_docx_and_keeps_queue(window, tmp_path):
    sources = [tmp_path / f"{name}.docx" for name in ("first", "second")]
    for source in sources:
        document = Document()
        document.add_paragraph(source.stem)
        document.save(source)
    window.add_files(list(map(str, sources)))
    window.operations_tab_bar.setCurrentIndex(window.operations_stack.indexOf(
        window.operations_stack.findChild(QWidget, "convert_page")
    ))
    window.convert_file_type_combo.setCurrentText("Документы")
    window.from_convert_combo.setCurrentText("DOCX")
    window.to_convert_combo.setCurrentText("PDF")
    mode = window.combo_conversion_output_mode
    mode.setCurrentIndex(mode.findData("alongside"))
    window.auto_clear_enabled_checkbox.setChecked(False)
    window.list_files.select_paths([str(sources[1])])
    assert window.btn_convert.isEnabled()
    window.btn_convert.click()
    assert window.file_worker.wait(5000)
    QApplication.processEvents()

    assert not sources[0].with_suffix(".pdf").exists()
    assert "second" in PdfReader(sources[1].with_suffix(".pdf")).pages[0].extract_text()
    assert len(window.files) == 3
    assert window.from_convert_combo.currentText() == "DOCX"
    assert window.to_convert_combo.currentText() == "PDF"


def test_merge_keyboard_order_matches_output(window, tmp_path):
    sources = [tmp_path / f"{index}.pdf" for index in range(3)]
    for index, source in enumerate(sources):
        with PdfWriter() as writer:
            writer.add_blank_page(width=200 + index * 10, height=300)
            writer.write(source)
    window.add_files(list(map(str, sources)))
    window.operations_tab_bar.setCurrentIndex(window.operations_stack.indexOf(
        window.operations_stack.findChild(QWidget, "merge_page")
    ))
    assert window.list_files.verticalHeader().isHidden()
    window.list_files.setCurrentIndex(window.list_files.model().index(2, 0))
    QTest.keyClick(window.list_files, Qt.Key.Key_Up, Qt.KeyboardModifier.AltModifier)
    model = window.list_files.model()
    assert not window.list_files.isColumnHidden(model.COLUMN_ORDER)
    assert window.list_files.horizontalHeader().visualIndex(model.COLUMN_ORDER) == 1
    assert [model.index(row, model.COLUMN_ORDER).data() for row in range(3)] == [1, 2, 3]
    for _ in range(500):
        if window.btn_merge.isEnabled():
            break
        QApplication.processEvents()
        time.sleep(0.01)
    assert window.btn_merge.isEnabled(), window.merge_pages_panel.hint.text()
    output = tmp_path / "combined.pdf"
    with (
        patch("app.ui.mixins.worker_ops_mixin.choose_merge_pages", return_value=()),
        patch.object(window, "_select_merge_output_path_for_format", return_value=str(output)),
        patch.object(window, "show_russian_message_box", return_value=True),
    ):
        window.btn_merge.click()
    assert window.file_worker.wait(5000)
    QApplication.processEvents()
    assert [int(page.mediabox.width) for page in PdfReader(output).pages] == [200, 220, 210]
    assert window.operation_result_panel.result.outcome == "success"


def test_partial_result_retries_only_explicitly_retryable_errors(window, tmp_path):
    output = tmp_path / "created.pdf"
    output.write_bytes(b"test")
    window._operations.last_request = ConversionRequest("docx_to_pdf", "PDF", "alongside", "")
    window.on_operation_finished(OperationResult(
        new_files=[FileItem(str(output))],
        errors=[
            {"path": "document.docx", "message": "LayoutError"},
            {"path": "locked.docx", "message": "PermissionError", "retryable": True},
        ],
    ))
    panel = window.operation_result_panel
    assert "Обработана часть файлов" in panel.summary.text()
    assert len(panel.retryable) == 1 and panel.retryable[0]["path"] == "locked.docx"


def test_compression_result_reports_measured_sizes(window, tmp_path):
    source = tmp_path / "source.jpg"
    Image.effect_noise((600, 400), 90).save(source, quality=100)
    original_size = source.stat().st_size
    window.add_files([str(source)])
    window.operations_tab_bar.setCurrentIndex(window.operations_stack.indexOf(
        window.operations_stack.findChild(QWidget, "compress_page")
    ))
    with patch.object(window, "show_russian_message_box", return_value=True):
        window.btn_compress.click()
    assert window.file_worker.wait(5000)
    QApplication.processEvents()

    result = window.operation_result_panel.result
    size, = result.compression_sizes
    target, = result.new_files
    assert size.before == original_size
    assert size.after == target.size < original_size
    assert "Экономия" in window.operation_result_panel.summary.text()

def test_ribbon_keeps_parameters_and_queue_accessible(window):
    tabs = window.operations_tab_bar
    tabs.setCurrentIndex(0)
    window.combo_templates.setCurrentText("Добавить текст")
    window.template_add_text.setText("готово_")
    for theme in ("dark", "light"):
        window.apply_theme_mode(theme)
        for width in (900, 1200):
            window.resize(width, 600)
            QApplication.processEvents()
            assert window.template_add_text.isVisible()
            assert window.rename_validation_label.isVisible()
            assert window.rename_status_group.parentWidget() is window.label_total_size.parentWidget()
            assert window.template_add_text.text() == "готово_"
            assert window.btn_apply_rename.isVisible()
            QApplication.processEvents()
            ribbon = window.ribbon_panel
            for field in (window.combo_templates, window.template_add_text, window.btn_apply_rename):
                corners = (field.mapTo(ribbon, point) for point in (field.rect().topLeft(), field.rect().bottomRight()))
                assert all(ribbon.rect().contains(point) for point in corners)
            rule, action = (field.mapTo(ribbon, field.rect().center()) for field in (
                window.combo_templates, window.btn_apply_rename
            ))
            assert abs(rule.y() - action.y()) <= 2
            assert window.queue_panel.width() == window.ribbon_panel.width()
            assert window.queue_panel.height() > window.ribbon_panel.height()

    QTest.mouseDClick(tabs.group.button(0), Qt.MouseButton.LeftButton)
    assert window.ribbon_panel.isHidden()
    tabs.setCurrentIndex(window._settings_tab_index)
    window.hide_settings_panel()
    assert window.ribbon_panel.isHidden()
    QTest.mouseDClick(tabs.group.button(0), Qt.MouseButton.LeftButton)
    assert window.ribbon_panel.isVisible()
    assert window.template_add_text.text() == "готово_"

def test_support_and_settings_return_to_previous_queue(window):
    tabs = window.operations_tab_bar
    tabs.setCurrentIndex(2)
    QTest.mouseClick(tabs.group.button(window._help_tab_index), Qt.MouseButton.LeftButton)
    assert window.support_page.isVisible()
    assert all(button.isVisible() for button in window.support_page.commands.values())
    assert not window.queue_panel.isVisible()
    QTest.keyClick(tabs.group.button(window._help_tab_index), Qt.Key.Key_Left)
    assert window.settings_panel_widget.isVisible()
    QTest.mouseClick(tabs.group.button(2), Qt.MouseButton.LeftButton)
    assert tabs.currentIndex() == 2
    assert window.queue_panel.isVisible()
    assert window.btn_compress.isVisible()


@pytest.mark.parametrize("section", ["_settings_tab_index", "_help_tab_index"])
def test_utility_section_has_no_queue_back_button(window, section):
    window.operations_tab_bar.setCurrentIndex(getattr(window, section))
    QApplication.processEvents()
    assert window.settings_panel_host.isVisible()
    assert all("к очереди" not in button.text().casefold()
               for button in window.settings_panel_host.findChildren(QAbstractButton))


def test_help_opens_readable_operation_log(window, tmp_path):
    log = tmp_path / "operations.txt"
    log.write_text("Обработан файл example.pdf", encoding="utf-8")
    window._log_file_path = str(log)
    window.operations_tab_bar.setCurrentIndex(window._help_tab_index)
    dialogs = []
    with patch.object(QDialog, "exec", new=lambda dialog: dialogs.append(dialog)):
        window.support_page.commands["save"].click()
    dialog, = dialogs
    viewer = dialog.findChild(QPlainTextEdit)
    assert viewer.isReadOnly()
    assert "Обработан файл example.pdf" in viewer.toPlainText()


@pytest.mark.parametrize("trigger", ["escape", "button", "close"])
def test_progress_cancellation_keeps_dialog_until_completion(window, trigger):
    dialog = OperationProgressDialog(window, "dark")
    requests = []
    dialog.cancel_requested.connect(lambda: requests.append(True))
    dialog.show_progress()
    if trigger == "escape":
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
    elif trigger == "button":
        dialog.cancel_button.click()
    else:
        dialog.close()
    assert dialog.isVisible()
    assert requests == [True]
    assert not dialog.cancel_button.isEnabled()
    assert "Отмена" in dialog.status_label.text()
    QTest.keyClick(dialog, Qt.Key.Key_Escape)
    assert requests == [True]
    dialog.reset()
    assert not dialog.isVisible()
    dialog.show_progress()
    assert dialog.cancel_button.isEnabled()
    dialog.reset()
    dialog.deleteLater()


def test_cancel_button_respects_explicit_role(window):
    button = window.progress_dialog.cancel_button
    setup_standard_action_button(button, variant="secondary")
    assert button.property("buttonVariant") == "secondary"
    setup_standard_action_button(button, variant="danger")
    assert button.property("buttonVariant") == "danger"


@pytest.mark.parametrize("busy_kind", ["operation", "metadata"])
def test_launch_buttons_block_and_restore_after_busy_state(window, tmp_path, busy_kind):
    source = tmp_path / "source.jpg"
    Image.new("RGB", (10, 10)).save(source)
    window.add_files([str(source)])
    window.combo_templates.setCurrentText("Добавить текст")
    window.template_add_text.setText("new_")
    window._refresh_launch_button_states()
    buttons = (window.btn_apply_rename, window.btn_convert, window.btn_compress, window.btn_merge)
    before = [button.isEnabled() for button in buttons]
    assert before[0] and before[2]
    context = (
        patch.object(window, "_operation_is_running", return_value=True)
        if busy_kind == "operation" else
        patch.object(window, "_file_metadata_worker", SimpleNamespace(isRunning=lambda: True), create=True)
    )
    with context:
        window._refresh_launch_button_states()
        window.on_file_selection_changed()
        assert all(not button.isEnabled() for button in buttons)
        assert all("Дождитесь" in button.toolTip() for button in buttons)
    QTest.qWait(150)
    assert [button.isEnabled() for button in buttons] == before


def test_merge_preview_and_dispatch_use_same_marked_scope(window, tmp_path):
    sources = []
    for index in range(3):
        source = tmp_path / f"source{index}.pdf"
        with PdfWriter() as writer:
            writer.add_blank_page(width=100 + index, height=100)
            writer.write(source)
        sources.append(str(source))
    other = tmp_path / "other.docx"
    Document().save(other)
    window.add_files([*sources, str(other)])
    window.list_files.select_paths(sources[:2])
    window.operations_tab_bar.setCurrentIndex(window.operations_stack.indexOf(
        window.operations_stack.findChild(QWidget, "merge_page")
    ))
    for _ in range(500):
        if window.btn_merge.isEnabled():
            break
        QApplication.processEvents()
        time.sleep(0.01)
    assert window.btn_merge.isEnabled()
    assert [file.path for file in window.merge_pages_panel.files] == sources[:2]
    with (
        patch.object(window, "_select_merge_output_path_for_format", return_value=str(tmp_path / "out.pdf")),
        patch.object(window, "show_russian_message_box", return_value=True),
        patch.object(window, "_start_operation", return_value=False) as start,
    ):
        window.btn_merge.click()
    assert [file.path for file in start.call_args.args[1]] == sources[:2]
    window.input_search.setText("source2")
    assert window.merge_pages_panel.files == []
    assert not window.btn_merge.isEnabled()


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_main_command_icons_and_log_symbol(window, theme):
    window.apply_theme_mode(theme)
    for button, name in (
        (window.btn_add_files, "add-file"),
        (window.btn_add_folder, "add-folder"),
        (window.support_page.guide, "guide"),
        (window.btn_convert, "convert"),
    ):
        assert button.property("buttonIconName") == name
        assert not button.icon().pixmap(UI_ICON_SIZE).isNull()
    assert window.support_page.icons["save"].pixmap().toImage() == ui_icon(
        "document", theme
    ).pixmap(SUPPORT_ICON_SIZE, window.support_page.icons["save"].devicePixelRatioF()).toImage()


def test_result_detail_actions_have_explicit_icons(window):
    window.operation_result_panel.set_result(OperationResult(
        errors=[{"path": "source.pdf", "message": "locked", "retryable": True}]
    ), can_retry=True)
    seen = []

    def inspect(dialog):
        seen.extend(button.property("buttonIconName") for button in dialog.findChildren(QAbstractButton)
                    if button.property("buttonIconName"))
        assert all(not button.icon().isNull() for button in dialog.findChildren(QAbstractButton)
                   if button.property("buttonIconName"))

    with patch.object(QDialog, "exec", new=inspect):
        window.operation_result_panel.details.click()
    assert set(seen) == {"details", "copy", "retry", "close"}
