# Stage 6: `ui/main_window.py` jako osobny cleanup po canvasie

## Planowanie wymagane

TAK.

Na początku pracy agent ma spisać jeden jawny kontrakt "post-state-change refresh" i dopiero potem mapować, które flowy `MainWindow` mogą z niego korzystać bez zmiany ownershipu sygnałów.

## Cel

Uporządkować `ui/main_window.py` po domknięciu canvasa, bez rozbijania odpowiedzialności bootstrapu i routingu komend.

## Zakres

Najpierw ustalić jeden jawny kontrakt "post-state-change refresh" dla:

- cache raportu
- refreshu canvasa
- statusu
- odświeżenia materiałów

Potem wydzielać tylko helper modules dla:

- dialog flows
- refresh/report flows

## Poza zakresem

- bootstrap zostaje w `MainWindow`
- command routing zostaje w `MainWindow`
- ownership sygnałów zostaje w `MainWindow`
- nie przenosić zarządzania canvas signal lifecycle poza obecny model

## Testy automatyczne

Najpierw gate lokalny:

```bash
uv run pytest tests/test_mainwindow_ui_contract.py tests/test_workspace.py tests/test_drawing_canvas.py -q
```

Potem pełny suite:

```bash
uv run pytest -q
```

## Jak testować manualnie

1. Uruchomić aplikację:

```bash
uv run python3 __main__.py
```

2. Otworzyć projekt, zmienić geometrię, przeliczyć layout i sprawdzić, że canvas, status i materiały odświeżają się w poprawnej kolejności.
3. Wygenerować raport, potem zmienić stan projektu i sprawdzić, że cache raportu jest invalidowany wtedy, kiedy powinien.
4. Przejść przez kluczowe dialogi: tworzenie/edycja połaci, wycinki, materiały, zapis/otwieranie projektu.
5. Sprawdzić, że po przełączeniach zakładek i po odświeżeniu workspace sygnały canvasa nadal są aktywne.

## Warunek zakończenia

- istnieje jawny kontrakt refresh po zmianie stanu
- dialog flows i refresh/report flows są czytelniej wydzielone
- bootstrap, command routing i ownership sygnałów nie zostały naruszone

## Next stage

`Stage 7 -> _TODO/12F_STAGE_7_PROJECT_STATE_CLEANUP.md`
