# Stage 1B: MainWindow low-risk cleanup

```markdown
Wykonaj tylko niski-risk cleanup `ui/main_window.py` zgodnie z `_TODO/CLEANUP_PLAN.md`, bez pelnego rozbijania klasy.

Skup sie wylacznie na:
- helperze do bezpiecznego podpinania sygnalow canvasu z `Qt.ConnectionType.UniqueConnection`
- ujednoliceniu guardow aktywnego plane
- ograniczeniu prostych powtorzen w flow CRUD dla roof plane, jesli da sie to zrobic lokalnie i bezpiecznie

Nie rob:
- duzej dekompozycji `MainWindow`
- zmian lifecycle aplikacji
- ruszania `DrawingCanvas` poza niezbednymi call-site'ami
- zmian w architekturze projektu

Wymagania:
- zachowanie GUI ma pozostac bez zmian
- jesli potrzeba, dodaj male testy pomocnicze lub opisz, dlaczego sensowniejsze jest manual QA
- po zmianach uruchom `uv run pytest`

Na koncu podaj:
- co zmieniles
- jakie powtorzenia zostaly usuniete
- jakie testy uruchomiles
- krotka manual QA checklist dla `MainWindow`
```
