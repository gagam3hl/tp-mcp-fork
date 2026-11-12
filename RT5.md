# Branch `rt5`

Stand des Originals [JamsusMaximus/trainingpeaks-mcp](https://github.com/JamsusMaximus/trainingpeaks-mcp)
plus ausgewählte, noch nicht gemergte PRs.
`main` bleibt ein unveränderter Spiegel des Originals.

| PR | Inhalt |
|---|---|
| #182 | `validate_auth` stürzt bei `"token": null` nicht mehr ab (abgelaufenes Cookie, #181) |
| #178 | Kommentare vor/nach der Einheit in `tp_get_workout` |
| #199 | Compliance (Plan-Ist in %, Kalenderfarbe) in `tp_get_workouts`/`tp_get_workout` |
| #189 | `compact: true` für `tp_get_workouts` und `tp_get_metrics` |
| #190 | `timezone` für lokale Zeitstempel in `tp_get_workout`/`tp_analyze_workout` |
| #187 | HF-Zonen gezielt je Sportart, `ZONES_MISSING` statt stillem Schreiben in den allgemeinen Satz |
| #188 | klare Fehlermeldung bei falsch geformten Intervall-Strukturen |
| #191 | `description_mode: "append"` für `tp_update_workout` |
| #168 | neues Werkzeug `tp_complete_workout` (erledigt ohne Gerätedatei) |
| #185 | neues Werkzeug `tp_analyze_power_balance` — **umgebaut**: `workout_ids` statt `file_paths`, Datei aus TrainingPeaks im Speicher statt von der Platte (#194); neue Abhängigkeit `fitparse` |

Eigene Anpassungen: kompakte Zeilen tragen `compliance_color`/`_basis`/`_percent`
(#189 + #199); Tests der PRs an die Kombination angepasst (auch #191 mit #188/#189/#190).

Jeder PR wurde vor dem Merge gelesen (keine neuen Netzwerkziele, Dateizugriffe
oder Ausgaben von Tokens). Neue Stände des Originals: `main` synchronisieren,
in `rt5` mergen, Tests (`pytest`), dann pushen; Nutzer stellen ihren festen
Commit auf den neuen Stand um. Wird ein PR im Original gemergt, fällt er
beim nächsten Merge von `main` von selbst heraus.
