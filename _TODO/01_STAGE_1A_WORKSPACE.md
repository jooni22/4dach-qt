# Stage 1A: Workspace dedup

```markdown
Wykonaj tylko etap `1A` z `_TODO/CLEANUP_PLAN.md`.

Zakres:
- plik `ui/workspace.py`
- usun powtarzalny fan-out po wszystkich canvasach
- wyciagnij prywatny helper lub iterator do wspolnego stosowania operacji na canvasach
- nie zmieniaj zachowania publicznego
- nie rozszerzaj zakresu poza ten plik, chyba ze drobna zmiana pomocnicza jest absolutnie konieczna

Wymagania:
- zachowaj zgodnosc z istniejacym stylem kodu
- nie rob wiekszego redesignu
- jesli sa odpowiednie testy, uruchom je; w przeciwnym razie uruchom `uv run pytest`
- jesli zmieniasz zachowanie lub kontrakt, zatrzymaj sie i zglos to zamiast zgadywac

Na koncu podaj:
- co zmieniles
- jakie duplikacje zostaly usuniete
- jakie testy uruchomiles
- czy widzisz naturalny kolejny maly etap
```
