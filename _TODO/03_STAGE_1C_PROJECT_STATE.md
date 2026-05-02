# Stage 1C: ProjectState local dedup

```markdown
Wykonaj tylko lokalny cleanup `core/project_state.py` zgodnie z `_TODO/CLEANUP_PLAN.md`.

Cel:
- zredukowac lokalne duplikacje
- wyciagnac helpery lookupow
- ujednolicic wzorzec `lookup -> validate -> mutate -> mark dirty`
- nie zmieniac serializacji ani kontraktu danych

Wymagania:
- jesli refaktor dotyka zachowania, najpierw dodaj lub uzupelnij testy
- nie przenos logiki do UI
- nie upraszczaj kompatybilnosci danych z `core/models.py`
- po zakonczeniu uruchom `uv run pytest`

Na koncu podaj:
- co zmieniles
- ktore duplikacje zostaly faktycznie usuniete
- jakie testy dodales lub uruchomiles
- jakie ryzyka pozostaly przed refaktorem `layout_engine`
```
