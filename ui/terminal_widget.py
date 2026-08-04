#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Reusable VT terminal widget for serial and interactive SSH sessions."""

from collections import defaultdict

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PyQt5.QtWidgets import QApplication, QMenu, QPlainTextEdit

import pyte



ANSI_COLORS = {
    "black": "#17242B",
    "red": "#F06A6A",
    "green": "#72C991",
    "brown": "#D9B65C",
    "blue": "#66A7E8",
    "magenta": "#C58BE2",
    "cyan": "#57C7C3",
    "white": "#D9E5E7",
    "brightblack": "#657B83",
    "brightred": "#FF7B72",
    "brightgreen": "#8BD49C",
    "brightbrown": "#F2CC60",
    "brightblue": "#79B8FF",
    "brightmagenta": "#D2A8FF",
    "brightcyan": "#76E3EA",
    "brightwhite": "#FFFFFF",
}

class TerminalWidget(QPlainTextEdit):
    """A Qt display and keyboard bridge backed by a pyte VT screen."""

    data_ready = pyqtSignal(bytes)
    terminal_resized = pyqtSignal(int, int)
    input_focused = pyqtSignal()

    def __init__(self, parent=None, columns=120, lines=32, history=3000):
        super().__init__(parent)
        self._encoding = "utf-8"
        self._columns = max(20, int(columns))
        self._lines = max(5, int(lines))
        self._history_size = max(100, int(history))
        self._screen = pyte.HistoryScreen(
            self._columns,
            self._lines,
            history=self._history_size,
        )
        self._stream = pyte.Stream(self._screen)
        self._pending_text = []
        self._visual_cursor_position = 0
        self._resize_suspended = False
        self._saved_view_state = None
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(20)
        self._render_timer.timeout.connect(self.flush_pending_output)

        terminal_font = QFont("Consolas", 12)
        terminal_font.setStyleHint(QFont.Monospace)
        terminal_font.setFixedPitch(True)
        self.setFont(terminal_font)
        self.setCursorWidth(2)
        self.setReadOnly(True)
        self.setUndoRedoEnabled(False)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setMaximumBlockCount(self._history_size + self._lines)
        self.document().setDocumentMargin(4)
        self.setStyleSheet(
            "QPlainTextEdit { background: #073746; color: #D9F3F2;"
            " border: 1px solid #2A7180; padding: 8px;"
            " font-family: Consolas; font-size: 18px; }"
        )
        self.setFocusPolicy(Qt.StrongFocus)

    @property
    def columns(self):
        return self._columns

    @property
    def lines(self):
        return self._lines

    def set_encoding(self, encoding):
        self._encoding = str(encoding or "utf-8").lower()

    def feed_bytes(self, payload, encoding=None):
        codec = str(encoding or self._encoding or "utf-8").lower()
        self.feed_text(bytes(payload).decode(codec, errors="replace"))

    def feed_text(self, text):
        if not text:
            return
        self._pending_text.append(str(text))
        if not self._render_timer.isActive():
            self._render_timer.start()

    def flush_pending_output(self):
        if not self._pending_text:
            return
        self._render_timer.stop()
        text = "".join(self._pending_text)
        self._pending_text.clear()
        self._stream.feed(text)
        self._render_screen()

    def clear_terminal(self):
        self._render_timer.stop()
        self._pending_text.clear()
        self._visual_cursor_position = 0
        self._screen.reset()
        self.clear()

    def reset_terminal(self):
        self._render_timer.stop()
        self._pending_text.clear()
        self._screen = pyte.HistoryScreen(
            self._columns,
            self._lines,
            history=self._history_size,
        )
        self._stream = pyte.Stream(self._screen)
        self._visual_cursor_position = 0
        self.clear()

    def send_bytes(self, payload):
        if not self.isReadOnly() and payload:
            self.data_ready.emit(bytes(payload))

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.input_focused.emit()
        self._position_visual_cursor()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if (
            event.button() == Qt.LeftButton
            and not self.textCursor().hasSelection()
        ):
            self._position_visual_cursor()

    def keyPressEvent(self, event):
        if self.isReadOnly():
            super().keyPressEvent(event)
            return

        key = event.key()
        modifiers = event.modifiers()
        if modifiers & Qt.ControlModifier:
            if key == Qt.Key_C:
                if (
                    modifiers & Qt.ShiftModifier
                    or self.textCursor().hasSelection()
                ):
                    self.copy_selection_to_clipboard()
                else:
                    self.data_ready.emit(b"\x03")
                return
            if key == Qt.Key_V:
                self.paste_clipboard()
                return

        if modifiers & Qt.ControlModifier and not modifiers & Qt.AltModifier:
            if Qt.Key_A <= key <= Qt.Key_Z:
                self.data_ready.emit(bytes([key - Qt.Key_A + 1]))
                return

        special_keys = {
            Qt.Key_Return: b"\r",
            Qt.Key_Enter: b"\r",
            Qt.Key_Backspace: b"\x08",
            Qt.Key_Delete: b"\x7f",
            Qt.Key_Tab: b"\t",
            Qt.Key_Escape: b"\x1b",
            Qt.Key_Up: b"\x1b[A",
            Qt.Key_Down: b"\x1b[B",
            Qt.Key_Right: b"\x1b[C",
            Qt.Key_Left: b"\x1b[D",
            Qt.Key_Home: b"\x1b[H",
            Qt.Key_End: b"\x1b[F",
            Qt.Key_PageUp: b"\x1b[5~",
            Qt.Key_PageDown: b"\x1b[6~",
            Qt.Key_Insert: b"\x1b[2~",
        }
        payload = special_keys.get(key)
        if payload is not None:
            self.data_ready.emit(payload)
            return

        text = event.text()
        if text and not modifiers & (Qt.ControlModifier | Qt.AltModifier):
            self.data_ready.emit(text.encode(self._encoding, errors="replace"))

    def contextMenuEvent(self, event):
        selected_text = self.selected_text()
        clipboard_text = QApplication.clipboard().text()
        menu = QMenu(self)
        copy_action = menu.addAction("复制")
        paste_action = menu.addAction("粘贴并发送")
        interrupt_action = menu.addAction("发送 Ctrl+C")
        menu.addSeparator()
        select_all_action = menu.addAction("全选")
        copy_action.setEnabled(bool(selected_text))
        paste_action.setEnabled(
            not self.isReadOnly() and bool(clipboard_text)
        )
        interrupt_action.setEnabled(not self.isReadOnly())

        selected_action = menu.exec_(event.globalPos())
        if selected_action is copy_action:
            QApplication.clipboard().setText(selected_text)
        elif selected_action is paste_action:
            self.paste_clipboard(clipboard_text)
        elif selected_action is interrupt_action:
            self.send_bytes(b"\x03")
        elif selected_action is select_all_action:
            self.selectAll()

    def selected_text(self):
        cursor = self.textCursor()
        if not cursor.hasSelection():
            return ""
        return cursor.selection().toPlainText()

    def copy_selection_to_clipboard(self):
        text = self.selected_text()
        if text:
            QApplication.clipboard().setText(text)

    def paste_clipboard(self, text=None):
        clipboard_text = (
            QApplication.clipboard().text() if text is None else str(text)
        )
        if not self.isReadOnly() and clipboard_text:
            self.data_ready.emit(
                clipboard_text.encode(self._encoding, errors="replace")
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._resize_suspended or self.window().isMinimized():
            return
        self._sync_terminal_size_to_viewport()

    def _sync_terminal_size_to_viewport(self):
        metrics = self.fontMetrics()
        char_width = max(1, metrics.horizontalAdvance("M"))
        line_height = max(1, metrics.lineSpacing())
        viewport = self.viewport().size()
        if viewport.width() <= 0 or viewport.height() <= 0:
            return
        columns = max(20, viewport.width() // char_width)
        lines = max(5, viewport.height() // line_height)
        if columns == self._columns and lines == self._lines:
            return
        pending_text = "".join(self._pending_text)
        self._pending_text.clear()
        self._render_timer.stop()
        if pending_text:
            self._stream.feed(pending_text)
        self._columns = columns
        self._lines = lines
        self._resize_screen_preserving_content(lines, columns)
        self.setMaximumBlockCount(self._history_size + self._lines)
        self._render_screen()
        self.terminal_resized.emit(columns, lines)

    def suspend_for_window_minimize(self):
        """Freeze PTY geometry and remember the current terminal viewport."""
        self.flush_pending_output()
        scrollbar = self.verticalScrollBar()
        self._saved_view_state = (
            scrollbar.value(),
            scrollbar.value() >= scrollbar.maximum() - 2,
        )
        self._resize_suspended = True

    def restore_after_window_minimize(self):
        """Restore geometry, device cursor, and scroll anchor after minimize."""
        self._resize_suspended = False
        QTimer.singleShot(0, self._restore_minimized_view)

    def _restore_minimized_view(self):
        self._sync_terminal_size_to_viewport()
        self._position_visual_cursor()
        state = self._saved_view_state
        if state is None:
            return

        previous_scroll, was_at_bottom = state

        def apply_view_state():
            scrollbar = self.verticalScrollBar()
            if was_at_bottom:
                scrollbar.setValue(scrollbar.maximum())
            else:
                scrollbar.setValue(min(previous_scroll, scrollbar.maximum()))
            self.viewport().update()

        apply_view_state()
        QTimer.singleShot(0, apply_view_state)
        self._saved_view_state = None

    def _resize_screen_preserving_content(self, lines, columns):
        """Resize pyte without losing the cursor line or clipped columns."""
        screen = self._screen
        old_lines = screen.lines
        old_columns = screen.columns
        lines = max(5, int(lines))
        columns = max(20, int(columns))
        if lines == old_lines and columns == old_columns:
            return

        if lines < old_lines:
            last_used_line = screen.cursor.y
            for line_index, line in screen.buffer.items():
                if self._last_used_column(line) >= 0:
                    last_used_line = max(last_used_line, line_index)
            anchor_line = min(old_lines - 1, last_used_line)
            shift = max(0, anchor_line - lines + 1)
            shift = min(shift, old_lines - lines)

            for line_index in range(shift):
                screen.history.top.append(screen.buffer[line_index])

            old_buffer = screen.buffer
            new_buffer = defaultdict(old_buffer.default_factory)
            for new_index in range(lines):
                old_index = new_index + shift
                if old_index in old_buffer:
                    new_buffer[new_index] = old_buffer[old_index]
            screen.buffer = new_buffer
            screen.cursor.y = min(
                lines - 1,
                max(0, screen.cursor.y - shift),
            )

        screen.lines = lines
        screen.columns = columns
        screen.cursor.x = min(screen.cursor.x, columns - 1)
        screen.set_margins()
        screen.dirty.update(range(lines))

    def _render_screen(self):
        scrollbar = self.verticalScrollBar()
        if self._resize_suspended and self._saved_view_state is not None:
            previous_scroll, was_at_bottom = self._saved_view_state
        else:
            was_at_bottom = scrollbar.value() >= scrollbar.maximum() - 2
            previous_scroll = scrollbar.value()
        previous_cursor = self.textCursor()
        previous_selection = self.selected_text()
        selection_start = previous_cursor.selectionStart()
        selection_end = previous_cursor.selectionEnd()
        history_lines = list(self._screen.history.top)
        screen_lines = [
            self._screen.buffer[index] for index in range(self._screen.lines)
        ]
        lines = history_lines + screen_lines
        cursor_line = len(history_lines) + self._screen.cursor.y

        last_line = cursor_line
        for index, line in enumerate(lines):
            if self._last_used_column(line) >= 0:
                last_line = index
        lines = lines[:last_line + 1]

        text_parts = []
        styled_runs = []
        text_position = 0
        cursor_position = 0
        for line_index, line in enumerate(lines):
            screen_y = line_index - len(history_lines)
            is_cursor_line = screen_y == self._screen.cursor.y
            used_column = self._last_used_column(line)
            if is_cursor_line:
                used_column = max(used_column, self._screen.cursor.x)
            width = min(self._screen.columns, max(0, used_column + 1))

            run_key = None
            run_start = 0
            line_parts = []
            line_position = 0
            for column in range(width):
                if is_cursor_line and column == self._screen.cursor.x:
                    cursor_position = text_position + line_position
                cell = line[column]
                if not cell.data:
                    continue
                format_key = self._format_key(cell)
                if format_key != run_key:
                    if run_key is not None and not self._is_default_format(run_key):
                        styled_runs.append(
                            (
                                text_position + run_start,
                                line_position - run_start,
                                run_key,
                            )
                        )
                    run_key = format_key
                    run_start = line_position
                line_parts.append(cell.data)
                line_position += len(cell.data)
            if run_key is not None and not self._is_default_format(run_key):
                styled_runs.append(
                    (
                        text_position + run_start,
                        line_position - run_start,
                        run_key,
                    )
                )
            if is_cursor_line and self._screen.cursor.x >= width:
                cursor_position = text_position + line_position
            line_text = "".join(line_parts)
            text_parts.append(line_text)
            text_position += len(line_text)
            if line_index < len(lines) - 1:
                text_parts.append("\n")
                text_position += 1

        rendered_text = "".join(text_parts)
        document = self.document()
        self.setUpdatesEnabled(False)
        self.setPlainText(rendered_text)
        for start, length, format_key in styled_runs:
            if length <= 0:
                continue
            styled_cursor = QTextCursor(document)
            styled_cursor.setPosition(start)
            styled_cursor.setPosition(
                start + length,
                QTextCursor.KeepAnchor,
            )
            styled_cursor.mergeCharFormat(self._format_for_key(format_key))

        self._visual_cursor_position = min(
            cursor_position,
            document.characterCount() - 1,
        )
        cursor = self.textCursor()
        restored_selection = False
        if previous_selection:
            if (
                selection_end <= len(rendered_text)
                and rendered_text[
                    selection_start:selection_end
                ] == previous_selection
            ):
                restored_start = selection_start
            else:
                restored_start = rendered_text.find(previous_selection)
            if restored_start >= 0:
                cursor.setPosition(restored_start)
                cursor.setPosition(
                    restored_start + len(previous_selection),
                    QTextCursor.KeepAnchor,
                )
                restored_selection = True
        if not restored_selection:
            cursor.setPosition(self._visual_cursor_position)
        self.setTextCursor(cursor)
        self.setCursorWidth(0 if self._screen.cursor.hidden else 2)
        if was_at_bottom:
            scrollbar.setValue(scrollbar.maximum())
        else:
            scrollbar.setValue(min(previous_scroll, scrollbar.maximum()))
        self.setUpdatesEnabled(True)
        self.viewport().update()

    @staticmethod
    def _last_used_column(line):
        return max(
            (
                column for column, cell in line.items()
                if cell.data and cell.data != " "
            ),
            default=-1,
        )

    def _format_for_cell(self, cell):
        return self._format_for_key(self._format_key(cell))

    @staticmethod
    def _format_for_key(format_key):
        (
            foreground_name,
            background_name,
            bold,
            italics,
            underscore,
            strikethrough,
            reverse,
        ) = format_key
        char_format = QTextCharFormat()
        foreground = ANSI_COLORS.get(foreground_name, "#D9F3F2")
        background = ANSI_COLORS.get(background_name, "#073746")
        if reverse:
            foreground, background = background, foreground
        char_format.setForeground(QColor(foreground))
        char_format.setBackground(QColor(background))
        char_format.setFontWeight(
            QFont.Bold if bold else QFont.Normal
        )
        char_format.setFontItalic(bool(italics))
        char_format.setFontUnderline(bool(underscore))
        char_format.setFontStrikeOut(bool(strikethrough))
        return char_format

    @staticmethod
    def _is_default_format(format_key):
        return format_key == (
            "default",
            "default",
            False,
            False,
            False,
            False,
            False,
        )

    @staticmethod
    def _format_key(cell):
        return (
            cell.fg,
            cell.bg,
            cell.bold,
            cell.italics,
            cell.underscore,
            cell.strikethrough,
            cell.reverse,
        )

    def _position_visual_cursor(self):
        if self.document().characterCount() <= 0:
            return
        cursor = self.textCursor()
        cursor.setPosition(
            min(
                self._visual_cursor_position,
                self.document().characterCount() - 1,
            )
        )
        cursor.clearSelection()
        self.setTextCursor(cursor)
