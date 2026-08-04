from PyQt5.QtWidgets import QSplitter, QSplitterHandle

from ui.splitter import ModernSplitter, ModernSplitterHandle


def test_modern_splitter_types_are_extracted_as_reusable_widgets():
    assert issubclass(ModernSplitter, QSplitter)
    assert issubclass(ModernSplitterHandle, QSplitterHandle)
