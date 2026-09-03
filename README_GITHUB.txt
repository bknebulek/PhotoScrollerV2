PHOTO SCROLLER V2 — AUTOMATYCZNE BUDOWANIE .EXE PRZEZ GITHUB ACTIONS
===================================================================

Ta paczka jest gotowa do wrzucenia do repozytorium GitHub.
GitHub uruchomi komputer z Windowsem i zbuduje prawdziwy plik:

    PhotoScrollerV2.exe

Nie musisz instalować Pythona ani PyInstallera na swoim komputerze.

INSTRUKCJA — NAJPROSTSZA METODA
--------------------------------

1. Wejdź na github.com i zaloguj się.

2. Kliknij znak "+" u góry strony -> "New repository".

3. Nazwij repozytorium np.:

       PhotoScrollerV2

   Repozytorium może być PUBLIC lub PRIVATE.

4. Utwórz repozytorium przyciskiem "Create repository".

5. Rozpakuj pobrany plik PhotoScrollerV2_GitHub.zip na swoim komputerze.

6. W GitHubie wybierz:

       Add file -> Upload files

7. Prześlij CAŁĄ zawartość rozpakowanego folderu.

   WAŻNE:
   Musi zostać zachowany również folder:

       .github/workflows/build-windows.yml

   Jeżeli Windows nie pokazuje folderu .github, w Eksploratorze włącz
   wyświetlanie ukrytych elementów albo przeciągnij cały rozpakowany folder
   do pola przesyłania na GitHubie.

8. Kliknij "Commit changes".

9. Otwórz zakładkę:

       Actions

   Powinien automatycznie wystartować workflow:

       Build Windows EXE

10. Kliknij zakończone uruchomienie workflow.

11. Na dole strony znajdziesz sekcję "Artifacts".
    Kliknij:

       PhotoScrollerV2-Windows

12. GitHub pobierze ZIP. Rozpakuj go — w środku będzie:

       PhotoScrollerV2.exe

RĘCZNE URUCHOMIENIE KOMPILACJI
------------------------------
Jeżeli chcesz zbudować EXE ponownie bez zmiany kodu:

1. Actions
2. Build Windows EXE
3. Run workflow
4. Run workflow

Po zakończeniu pobierz artefakt "PhotoScrollerV2-Windows".

WAŻNA INFORMACJA O WINDOWS SMARTSCREEN
--------------------------------------
Plik EXE nie jest podpisany płatnym certyfikatem code-signing.
Windows może więc przy pierwszym uruchomieniu wyświetlić ostrzeżenie
SmartScreen typu "Windows protected your PC" / "Nieznany wydawca".

To nie oznacza automatycznie, że program jest zainfekowany — wynika to
z braku podpisu cyfrowego i reputacji nowego pliku wykonywalnego.

CO JEST W PACZCE
----------------
photo_scroller_v2.py              - kod programu
requirements.txt                  - wymagane biblioteki
.github/workflows/build-windows.yml - automatyczna kompilacja na Windows
build_windows.bat                 - alternatywne budowanie lokalne
uruchom_python.bat                - uruchomienie wersji Python
README_GITHUB.txt                 - ta instrukcja

FUNKCJE PHOTO SCROLLER V2
-------------------------
- zdjęcia przesuwają się od prawej do lewej
- pokaz działa w pętli
- ramka wokół zdjęcia
- pochylenie zdjęcia o 6 stopni w lewo
- drag & drop
- regulacja prędkości
- regulacja wielkości zdjęć
- regulacja odstępu
- wybór tła
- zapamiętywanie zdjęć i ustawień
- tryb prezentacji / pełny ekran
- wybór monitora

SKRÓTY
------
F11   - tryb prezentacji
ESC   - wyjście z prezentacji
SPACE - Start/Pauza
Ctrl+O - dodaj zdjęcia
Delete - usuń zaznaczone zdjęcia
