# Aider Chat-Befehle – Cheat Sheet

> Übersicht aller Befehle aus der bereitgestellten `/help`-Ausgabe. Befehle sind auf Englisch, Erläuterungen auf Deutsch.

## Modi & Chat

| Befehl | Beschreibung |
|---|---|
| `/architect` | In den Architect-/Editor-Modus wechseln, der zwei unterschiedliche Modelle verwendet. |
| `/ask` | Fragen zur Codebasis stellen, ohne Dateien zu bearbeiten. |
| `/chat-mode` | Zu einem anderen Chat-Modus wechseln. |
| `/code` | Änderungen am Code anfordern. |
| `/context` | In den Kontextmodus wechseln, um den Code im Umfeld zu betrachten. |
| `/clear` | Den Chatverlauf löschen. |
| `/multiline-mode` | Den Mehrzeilenmodus umschalten. |

## Dateien & Kontext

| Befehl | Beschreibung |
|---|---|
| `/add` | Dateien zum Chat hinzufügen, damit Aider sie bearbeiten oder eingehend prüfen kann. |
| `/read-only` | Dateien als reine Referenz zum Chat hinzufügen. |
| `/drop` | Dateien aus der Chat-Sitzung entfernen, um Kontextplatz freizugeben. |
| `/ls` | Alle bekannten Dateien auflisten und anzeigen, welche im Chat enthalten sind. |
| `/map` | Die aktuelle Repository-Karte ausgeben. |
| `/map-refresh` | Eine Aktualisierung der Repository-Karte erzwingen. |
| `/copy-context` | Den aktuellen Chat-Kontext als Markdown kopieren. |
| `/paste` | Bild oder Text aus der Zwischenablage in den Chat einfügen. |
| `/tokens` | Die Anzahl der Tokens im aktuellen Chat-Kontext anzeigen. |

## Git & Änderungen

| Befehl | Beschreibung |
|---|---|
| `/commit` | Änderungen am Repository committen, die außerhalb des Chats vorgenommen wurden; Commit-Nachricht optional. |
| `/diff` | Den Änderungs-Diff seit der letzten Nachricht anzeigen. |
| `/git` | Einen Git-Befehl ausführen; die Ausgabe wird nicht in den Chat übernommen. |
| `/undo` | Den letzten Git-Commit rückgängig machen, sofern Aider ihn erstellt hat. |
| `/lint` | Dateien im Chat linten und korrigieren; sind keine Chat-Dateien vorhanden, werden alle geänderten Dateien bearbeitet. |
| `/test` | Einen Shell-Befehl ausführen und dessen Ausgabe bei einem Exit-Code ungleich null zum Chat hinzufügen. |

## Modelle & Denkbudget

| Befehl | Beschreibung |
|---|---|
| `/model` | Das Hauptmodell auf ein anderes LLM umstellen. |
| `/editor-model` | Das Editor-Modell auf ein anderes LLM umstellen. |
| `/weak-model` | Das Weak Model auf ein anderes LLM umstellen. |
| `/models` | Die Liste verfügbarer Modelle durchsuchen. |
| `/reasoning-effort` | Die Intensität des Schlussfolgerns (Reasoning-Effort) festlegen. |
| `/think-tokens` | Das Budget für Thinking-Tokens festlegen. |

## Prompts, Sitzung & Zwischenablage

| Befehl | Beschreibung |
|---|---|
| `/edit` | Alias für `/editor`. |
| `/editor` | Einen Editor öffnen, um einen Prompt zu verfassen. |
| `/copy` | Die letzte Assistentenantwort in die Zwischenablage kopieren. |
| `/load` | Befehle aus einer Datei laden und ausführen. |
| `/save` | Befehle in einer Datei speichern, mit denen sich die Dateien der aktuellen Chat-Sitzung rekonstruieren lassen. |
| `/reset` | Alle Dateien entfernen und den Chatverlauf löschen. |
| `/settings` | Die aktuellen Einstellungen ausgeben. |

## Shell, Web & Hilfe

| Befehl | Beschreibung |
|---|---|
| `/run` | Einen Shell-Befehl ausführen und optional dessen Ausgabe zum Chat hinzufügen. Alias: `!`. |
| `/web` | Eine Webseite abrufen, in Markdown umwandeln und als Nachricht senden. |
| `/help` | Fragen zu Aider stellen. |
| `/report` | Ein Problem melden, indem ein GitHub-Issue geöffnet wird. |
| `/voice` | Spracheingabe aufnehmen und transkribieren. |

## Beenden

| Befehl | Beschreibung |
|---|---|
| `/exit` | Die Anwendung beenden. |
| `/quit` | Die Anwendung beenden. |
