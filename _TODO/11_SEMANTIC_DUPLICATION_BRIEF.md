# Semantic Duplication Brief

## Cel

Ten plik dotyczy tylko duplikacji semantycznych.

Nie chodzi o zwykłe copy-paste ani podobny kod, tylko o sytuacje, gdzie:

- to samo zachowanie jest realizowane kilkoma ścieżkami,
- ta sama odpowiedzialność jest rozproszona po kilku miejscach,
- GUI lub stan są odświeżane / liczone / interpretowane wieloma mechanizmami,
- podobny efekt użytkowy powstaje z dwóch różnych warstw logiki.

## Jedna rekomendowana skillka

Załaduj tylko:

- `codebase-cleanup-tech-debt`

Dlaczego ta jedna:

- najlepiej pasuje do inwentaryzacji i priorytetyzacji długu opartego o zachowanie,
- dobrze nadaje się do odróżnienia duplikacji lokalnej od semantycznej,
- wymusza ocenę ryzyka i ROI zamiast czysto estetycznego "sprzątania".

## Zasady dla agenta

Przed ruszeniem czegokolwiek agent powinien:

1. przeczytać `AGENTS.md`
2. przeczytać `docs/review-backlog.md`
3. przeczytać `_TODO/CLEANUP_PLAN.md`
4. sprawdzić `git status`
5. traktować obecny zielony suite jako baseline:
   - `uv run pytest` -> `242 passed, 2 skipped`
6. nie scalać semantycznych ścieżek bez testów charakteryzujących

## Co uznajemy tu za duplikację semantyczną

Przykłady:

- ten sam canvas dostaje tę samą operację dwiema drogami,
- ten sam refresh GUI dzieje się w kilku flowach niezależnie,
- ten sam wynik layoutu jest generowany trzema różnymi pętlami,
- ten sam snap wizualnie wygląda podobnie, ale pochodzi z dwóch konkurujących systemów,
- ten sam stan domenowy jest invalidowany przez wiele osobnych ścieżek mutacji.

## Potwierdzone duplikacje semantyczne

### 1. `ui/workspace.py` — aktywny canvas bywa obsługiwany podwójnie

Status:

- potwierdzone podczas Stage 1A

Opis:

- `primary_canvas` jest zwykle także obecny w `self._plane_tab_canvases`
- stare flow robiło operację najpierw na `primary_canvas`, a potem znowu podczas iteracji po `self._plane_tab_canvases.values()`
- to znaczy, że aktywny canvas otrzymywał tę samą semantyczną akcję dwa razy:
  - `toggle_grid`
  - `set_snap_to_grid_enabled`
  - `set_sheet_visibility`
  - `toggle_module_count`
  - `update`

Ważne:

- to nie zostało "naprawione" na siłę
- zostało świadomie zachowane i objęte testem jako istniejący kontrakt

Wniosek dla agenta:

- to jest kandydat do przyszłego świadomego uproszczenia zachowania, nie tylko refaktoru kodu
- wymaga decyzji produktowo-behawioralnej, nie samego cleanupu

### 2. `ui/main_window.py` — kilka flowów robi ten sam refresh stanu GUI

Status:

- częściowo znormalizowane w Stage 4

Opis:

- przed Stage 4 te flowy osobno wykonywały semantycznie ten sam pakiet działań:
  - invalidacja cache raportu,
  - odświeżenie material combo,
  - odświeżenie canvasu,
  - aktualizacja dirty/saved state
- dotyczyło to m.in.:
  - `_apply_snapshot()`
  - `_load_project_payload()`
  - `_perform_command()`
  - `_gen_report()`
  - `_recalculate()`

Co już zrobiono:

- wydzielono `_invalidate_cached_report()`
- wydzielono `_refresh_ui_after_state_change(...)`

Co nadal jest semantycznie ważne:

- różne flowy dalej chcą "prawie to samo", ale z drobnymi różnicami kolejności i skutków ubocznych
- to jest klasyczna semantyczna duplikacja orchestration flow

Wniosek dla agenta:

- nie chodzi już o copy-paste, tylko o wspólny model odświeżania UI po zmianie stanu
- dalsza redukcja wymaga bardzo ostrożnego pilnowania kolejności działań

### 3. `ui/main_window.py` — wiele guardów i wrapperów dla tego samego celu biznesowego

Status:

- częściowo znormalizowane w Stage 1B

Opis:

- kilka metod realizowało tę samą intencję: "pobierz aktywną połać i pokaż sensowny komunikat, jeśli jej nie ma"
- podobnie dla wariantów:
  - aktywna połać
  - aktywna połać z obrysem
  - aktywna połać z wycinkami
- dodatkowo część CRUD flow była tylko cienkimi wrapperami wokół podobnej sekwencji:
  - pobierz aktywną połać
  - wykonaj operację
  - ustaw aktywną zakładkę

Wniosek dla agenta:

- tu semantycznie powtarza się "policy layer" dla active plane access
- jeśli iść dalej, to nie przez dużą dekompozycję, tylko przez bardziej spójny model guard/orchestration

### 4. `core/project_state.py` — wiele mutatorów robi ten sam cykl invalidacji layoutu

Status:

- częściowo znormalizowane w Stage 1C

Opis:

- wiele publicznych metod mutujących realizowało ten sam semantyczny cykl:
  - znajdź plane
  - zwaliduj geometrię / hole / outline
  - zmutuj stan
  - oznacz layout jako dirty i podbij revision
- dotyczy to rodzin metod wokół:
  - outline
  - holes
  - geometrii całej połaci

Co już zrobiono:

- dodano `_item_by_id(...)`, `_item_index_by_id(...)`
- dodano `_set_plane_geometry(...)`
- uproszczono część ścieżek outline/hole

Co nadal pozostaje semantycznie wspólne:

- nie wszystkie mutatory korzystają z jednego modelu lifecycle zmiany geometrii
- nadal istnieje kilka osobnych wejść do tego samego efektu domenowego: "zmień geometrię i przebuduj layout inputs"

Wniosek dla agenta:

- dalszy krok powinien szukać wspólnego modelu mutacji domenowej, nie tylko mniejszej liczby linijek

### 5. `core/layout_engine.py` — trzy różne pętle generują ten sam typ wyniku

Status:

- częściowo znormalizowane w Stage 3

Opis:

- trzy osobne ścieżki budowały semantycznie to samo:
  - partial-cutout bottom phase
  - partial-cutout top phase
  - standard phase
- każda z nich produkowała podobny outcome:
  - `SheetPlacement`
  - `RejectedSegment`
  - ostrzeżenia dla `zero_sheet_height`

Co już zrobiono:

- wydzielono `_RowGeometry`
- wydzielono helpery:
  - `_row_geometry(...)`
  - `_append_zero_sheet_height_warning(...)`
  - `_make_placement_id(...)`
  - `_append_placement(...)`
  - `_append_rejected_segment(...)`
  - `_record_sheet_outcome(...)`
  - `_extend_segment_coverage_for_top_extra(...)`

Co nadal jest istotne:

- control flow pozostał rozgałęziony
- semantyczna wspólność jest większa niż obecna struktura funkcji

Wniosek dla agenta:

- to nadal hotspot semantycznej duplikacji, ale bardzo ryzykowny
- każda próba dalszego scalenia musi szanować różnice partial vs standard, nie tylko podobieństwo kodu

### 6. `ui/drawing_canvas.py` — kilka systemów snap działa na siebie nawzajem

Status:

- częściowo ustabilizowane przez późniejsze fixy i testy

Opis:

- w praktyce istnieje kilka nakładających się warstw odpowiedzialnych za podobny efekt użytkowy "punkt końcowy snapuje się sensownie":
  - explicit axis snap
  - point snap
  - angular snap
  - inference snap
  - grid snap
- historycznie inference potrafił semantycznie "wygrać" z explicitem, mimo że użytkowo powinno być odwrotnie

Co już zrobiono:

- explicit snap ma priorytet nad inference snap
- w `MODE_DRAW_OUTLINE` point snap nie używa już istniejącej geometrii połaci
- nadal zachowano inferencje po istniejących krawędziach dla `edge_extension`

Wniosek dla agenta:

- to nie jest zwykła duplikacja kodu, tylko konkurujące systemy interpretacji tego samego gestu użytkownika
- to jeden z najlepszych przykładów semantycznej duplikacji w repo

### 7. `ui/drawing_canvas.py` — dwa źródła targetów dla rysowania

Status:

- potwierdzone podczas stabilizacji `MODE_DRAW_OUTLINE`

Opis:

- draw targets mogą pochodzić z:
  - istniejącej geometrii `roof_plane`
  - bieżącego szkicu `user_points`
- to samo pojęcie "target do rysowania" było wykorzystywane równocześnie dla:
  - point snap
  - edge midpoint snap
  - intersection/projection
  - inference lines

Dlaczego to jest semantyczna duplikacja:

- jeden koncept biznesowy został podpięty pod dwa różne światy geometrii
- dla części trybów te światy powinny być wspólne, dla części nie

Wniosek dla agenta:

- dalsze porządki powinny rozdzielić:
  - targety do point snap
  - targety do inferencji
  - targety do hit-test/selection

### 8. `ui/drawing_canvas.py` — render sheetów ma dwa równoległe źródła geometrii wizualnej

Status:

- zmapowane i częściowo osłonięte testami w Stage 5

Opis:

- render placementu bazuje jednocześnie na:
  - prostokącie placementu
  - `coverage_polygons` segmentu
  - dodatkowym rozszerzeniu `partial_cutout_top`
- końcowy efekt wizualny jest jedną rzeczą, ale bierze się z kilku nakładających się reprezentacji

Wniosek dla agenta:

- to obszar podatny na semantyczne rozjechanie renderu i logiki segmentu
- dobry kandydat do osobnego modelu "placement render geometry"

## Wysokoprawdopodobne dodatkowe miejsca do audytu

To nie są jeszcze tak twardo potwierdzone przypadki jak wyżej, ale warto je sprawdzić.

### 9. `ui/main_window.py` — raport i status jako kilka osobnych warstw odświeżania

Pytania do audytu:

- czy status bar, report cache i canvas refresh nie opisują tego samego stanu zbyt wieloma kanałami?
- czy po zmianach projektu nie ma kilku semantycznie równoległych źródeł prawdy o tym, co jest "aktualne"?

### 10. `ui/toolbar.py` — semantyka akcji zależna od indeksów

Pytania do audytu:

- czy nie ma przypadków, gdzie ta sama intencja użytkowa jest trzymana jednocześnie jako nazwana akcja i jako pozycja w `_toolbar_actions`?
- czy indeks i obiekt akcji nie są dwoma reprezentacjami tego samego kontraktu?

### 11. `core/models.py` — kompatybilność legacy jako świadoma podwójna semantyka wejścia/wyjścia

To specjalny przypadek.

Formalnie wygląda jak duplikacja, ale często nią nie jest.

Przykłady:

- aliasy kluczy w `to_dict()` / `from_dict()`
- wiele akceptowanych formatów danych dla tego samego modelu

Wniosek:

- agent ma to traktować jako "podwójną semantykę zgodności", nie automatycznie jako smell do usunięcia

## Najlepsza kolejność audytu semantycznych duplikacji

1. `ui/main_window.py` — orchestration/refresh duplication
2. `core/project_state.py` — mutation lifecycle duplication
3. `core/layout_engine.py` — multi-path outcome generation
4. `ui/drawing_canvas.py` — target ownership i snap semantics
5. `ui/drawing_canvas.py` — render geometry model
6. `ui/toolbar.py`
7. `core/models.py` tylko jeśli agent umie rozróżnić kompatybilność od zbędnej duplikacji

## Co agent ma oddać po takim audycie

Dla każdego znalezionego przypadku agent powinien wypisać:

1. gdzie jest duplikacja semantyczna
2. jakie dwa lub więcej flow realizują ten sam efekt
3. czy to jest:
   - bug,
   - historyczny kontrakt,
   - świadoma kompatybilność,
   - kandydat do refaktoru
4. jaki jest najmniejszy bezpieczny krok
5. jakie testy trzeba mieć przed ruszeniem tego obszaru

## Gotowy prompt dla agenta

```text
Pracuj tylko nad duplikacjami semantycznymi. Nie interesuje mnie zwykły duplicated code, tylko miejsca, gdzie to samo zachowanie, ten sam efekt GUI albo ten sam lifecycle stanu jest realizowany wieloma ścieżkami. Przeczytaj AGENTS.md, docs/review-backlog.md, _TODO/CLEANUP_PLAN.md oraz _TODO/11_SEMANTIC_DUPLICATION_BRIEF.md. Zrób inwentaryzację przypadków, podziel je na potwierdzone i podejrzane, oceń ryzyko, wskaż najmniejszy bezpieczny krok dla każdego i powiedz, które z nich są warte refaktoru teraz, a które wymagają najpierw testów charakteryzujących.
```
