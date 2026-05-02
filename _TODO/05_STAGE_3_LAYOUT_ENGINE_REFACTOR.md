# Stage 3: Layout engine refactor

```markdown
Wykonaj tylko etap refaktoru `core/layout_engine.py` zgodnie z `_TODO/CLEANUP_PLAN.md`.

Cel:
- usunac semantyczne duplikacje w `generate_layout()`
- wyciagnac wspolny helper dla budowania `SheetPlacement`, `RejectedSegment` i pokrewnej logiki
- zachowac dokladnie dotychczasowe zachowanie funkcjonalne

Wymagania:
- najpierw upewnij sie, ze testy charakteryzujace istnieja i przechodza
- nie zmieniaj publicznego kontraktu `LayoutResult`, jesli nie jest to konieczne
- nie przeprojektowuj calego algorytmu
- po zmianach uruchom `uv run pytest`

Na koncu podaj:
- jakie semantyczne duplikacje zostaly usuniete
- ktore petle lub sekcje zostaly uproszczone
- jakie testy uruchomiles
- jakie ryzyka nadal pozostaly
```
