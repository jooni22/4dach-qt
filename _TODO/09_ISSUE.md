Po nraysowaniu ksztaltu i wybraniu z ikon tego czerwonego celownika aby okreslic punkt 0, aplikacja sie wyspuje:
"""
stankiem@4dach$ make run Uruchamianie aplikacji... uv run python3 __main__.py Hole 0 partially or fully outside outline — allowed This plugin supports grabbing the mouse only for popup windows This plugin 
supports grabbing the mouse only for popup windows Error calling Python override of QWidget::paintEvent(): Traceback (most recent call last):
  File "/data/APP/83_4dach_zimnoch/qt/4dach/ui/drawing_canvas.py", line 3013, in paintEvent self._draw_origin_marker(painter, mapper)
  File "/data/APP/83_4dach_zimnoch/qt/4dach/ui/drawing_canvas.py", line 3531, in _draw_origin_marker
    painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label_text)
                     ^^^^^^^^^^
UnboundLocalError: cannot access local variable 'label_rect' where it is not associated with a value
QBackingStore::endPaint() called with active painter; did you forget to destroy it or call QPainter::end() on it?
QPainter::begin: A paint device can only be painted by one painter at a time.
QPainter::setCompositionMode: Painter not active
make: *** [Makefile:53: run] Błąd 139
"""
