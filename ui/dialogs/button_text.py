from __future__ import annotations

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QAbstractButton, QDialogButtonBox, QMessageBox, QWidget

_DIALOG_BUTTON_TEXTS = {
    QDialogButtonBox.StandardButton.Ok: "OK",
    QDialogButtonBox.StandardButton.Cancel: "Anuluj",
    QDialogButtonBox.StandardButton.Save: "Zapisz",
    QDialogButtonBox.StandardButton.Discard: "Odrzuć",
    QDialogButtonBox.StandardButton.Yes: "Tak",
    QDialogButtonBox.StandardButton.No: "Nie",
}

_MESSAGE_BUTTON_TEXTS = {
    QMessageBox.StandardButton.Ok: "OK",
    QMessageBox.StandardButton.Cancel: "Anuluj",
    QMessageBox.StandardButton.Save: "Zapisz",
    QMessageBox.StandardButton.Discard: "Odrzuć",
    QMessageBox.StandardButton.Yes: "Tak",
    QMessageBox.StandardButton.No: "Nie",
}


def localize_button_box(button_box: QDialogButtonBox) -> None:
    for standard_button, text in _DIALOG_BUTTON_TEXTS.items():
        button = button_box.button(standard_button)
        if button is not None:
            button.setText(text)
            button.setIcon(QIcon())


def localize_message_box(message_box: QMessageBox) -> None:
    for button in message_box.buttons():
        standard_button = message_box.standardButton(button)
        text = _MESSAGE_BUTTON_TEXTS.get(standard_button)
        if text is not None:
            button.setText(text)
        if standard_button != QMessageBox.StandardButton.NoButton:
            button.setIcon(_message_button_icon(message_box, standard_button))


def show_message_box(
    parent: QWidget | None,
    icon: QMessageBox.Icon,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
) -> QMessageBox.StandardButton:
    message_box = QMessageBox(parent)
    message_box.setWindowTitle(title)
    message_box.setText(text)
    message_box.setIcon(icon)
    message_box.setStandardButtons(buttons)
    if default_button != QMessageBox.StandardButton.NoButton:
        message_box.setDefaultButton(default_button)
    localize_message_box(message_box)
    return QMessageBox.StandardButton(message_box.exec())


def show_information(parent: QWidget | None, title: str, text: str) -> QMessageBox.StandardButton:
    return show_message_box(parent, QMessageBox.Icon.Information, title, text)


def show_warning(parent: QWidget | None, title: str, text: str) -> QMessageBox.StandardButton:
    return show_message_box(parent, QMessageBox.Icon.Warning, title, text)


def show_critical(parent: QWidget | None, title: str, text: str) -> QMessageBox.StandardButton:
    return show_message_box(parent, QMessageBox.Icon.Critical, title, text)


def show_question(
    parent: QWidget | None,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton,
    default_button: QMessageBox.StandardButton,
) -> QMessageBox.StandardButton:
    return show_message_box(parent, QMessageBox.Icon.Question, title, text, buttons, default_button)


def _message_button_icon(
    message_box: QMessageBox,
    standard_button: QMessageBox.StandardButton,
) -> QIcon:
    style = message_box.style()
    icon_map = {
        QMessageBox.StandardButton.Ok: style.StandardPixmap.SP_DialogApplyButton,
        QMessageBox.StandardButton.Save: style.StandardPixmap.SP_DialogSaveButton,
        QMessageBox.StandardButton.Cancel: style.StandardPixmap.SP_DialogCancelButton,
        QMessageBox.StandardButton.Discard: style.StandardPixmap.SP_TrashIcon,
        QMessageBox.StandardButton.Yes: style.StandardPixmap.SP_DialogApplyButton,
        QMessageBox.StandardButton.No: style.StandardPixmap.SP_DialogCancelButton,
    }
    pixmap = icon_map.get(standard_button)
    if pixmap is None:
        return QIcon()
    return style.standardIcon(pixmap)


def button_text(button: QAbstractButton, text: str) -> QAbstractButton:
    button.setText(text)
    return button
