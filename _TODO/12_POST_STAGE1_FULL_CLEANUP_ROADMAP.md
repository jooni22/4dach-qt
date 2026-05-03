# Etapy po Stage 1: pełna mapa cleanupu i refaktoru

## Cel dokumentu

Ten plik jest indeksem i krótkim briefingiem do dalszych prac po Stage 1.

To jest kanoniczny punkt startowy dla kolejnych agentów.

Szczegóły każdego etapu są w osobnych plikach:

- [Stage 2](/data/APP/83_4dach_zimnoch/qt/4dach/_TODO/12A_STAGE_2_DRAWING_CANVAS_TEST_FIRST_HARDENING.md)
- [Stage 3](/data/APP/83_4dach_zimnoch/qt/4dach/_TODO/12B_STAGE_3_CANVAS_PURE_HELPERS_EXTRACTION.md)
- [Stage 4](/data/APP/83_4dach_zimnoch/qt/4dach/_TODO/12C_STAGE_4_DRAWING_CANVAS_INTERNAL_SPLIT.md)
- [Stage 5](/data/APP/83_4dach_zimnoch/qt/4dach/_TODO/12D_STAGE_5_LAYOUT_ENGINE_REFACTOR.md)
- [Stage 6](/data/APP/83_4dach_zimnoch/qt/4dach/_TODO/12E_STAGE_6_MAIN_WINDOW_CLEANUP.md)
- [Stage 7](/data/APP/83_4dach_zimnoch/qt/4dach/_TODO/12F_STAGE_7_PROJECT_STATE_CLEANUP.md)
- [Stage 8](/data/APP/83_4dach_zimnoch/qt/4dach/_TODO/12G_STAGE_8_COMPATIBILITY_AUDIT_LOW_ROI.md)

## Aktualny baseline

- Stage 1 jest już wykonany.
- Deduplikacje helperów polygon/projection/boundary są już w kodzie.
- Baseline dla tej roadmapy: `uv run pytest -q` -> `254 passed`.

## Niezmienne kontrakty

- `ui/drawing_canvas.py` pozostaje publicznym entrypointem.
- `mainwindow.py` pozostaje shimem kompatybilności.
- Aliasy `build_*_outline` pozostają dostępne.
- Brak zmian formatu configa i serializacji bez osobnej decyzji migracyjnej.
- Brak zmian publicznych ścieżek importu dla istniejących call-site'ów.

## Zasady kolejności

- Kolejność etapów jest sztywna.
- Najpierw Stage 2.
- Stage 3 dopiero po zielonym Stage 2.
- Stage 4 dopiero po zielonym Stage 2 i 3.
- Stage 5, 6, 7 i 8 są kolejnymi osobnymi etapami, nie równoległymi strumieniami.

## Materiały wspierające

- `_TODO/10_RISKY_REFACTOR_AGENT_BRIEF.md`
- `_TODO/11_SEMANTIC_DUPLICATION_BRIEF.md`
- `docs/review-backlog.md`
- `AGENTS.md`

## Jak używać tego indeksu

Jeżeli przekazujesz pracę kolejnemu agentowi:

1. Otwórz ten plik.
2. Wybierz aktualny stage zgodnie z kolejnością.
3. Skopiuj pełną zawartość odpowiedniego pliku stage-specific.
4. Nie mieszaj zakresów kilku stage'y w jednym przebiegu, chyba że stage wyraźnie tego wymaga.

## Status starego cleanup planu

- `_TODO/_FEATURES/cleanup_plan.md` jest już tylko artefaktem historycznym.
- Nie używać go do ustalania kolejności dalszych prac.
