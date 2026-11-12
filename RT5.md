# Branch `rt5`

Stand des Originals [JamsusMaximus/trainingpeaks-mcp](https://github.com/JamsusMaximus/trainingpeaks-mcp)
plus ausgewählte, noch nicht gemergte PRs — für [gagam3hl/TrainingPeaks-MCP](https://github.com/gagam3hl/TrainingPeaks-MCP).
`main` bleibt ein unveränderter Spiegel des Originals.

| PR | Inhalt |
|---|---|
| #182 | `validate_auth` stürzt bei `"token": null` nicht mehr ab (abgelaufenes Cookie, #181) |
| #178 | Kommentare vor/nach der Einheit in `tp_get_workout` |
| #199 | Compliance (Plan-Ist in %, Kalenderfarbe) in `tp_get_workouts`/`tp_get_workout` |
| #189 | `compact: true` für `tp_get_workouts` und `tp_get_metrics` |
| #190 | `timezone` für lokale Zeitstempel in `tp_get_workout`/`tp_analyze_workout` |

Eigene Anpassungen: kompakte Zeilen tragen `compliance_color`/`_basis`/`_percent`
(#189 + #199); Tests der PRs an die Kombination angepasst.

Jeder PR wurde vor dem Merge gelesen (keine neuen Netzwerkziele, Dateizugriffe
oder Ausgaben von Tokens). Neue Stände des Originals: `main` synchronisieren,
in `rt5` mergen, Tests (`pytest`), dann im Haupt-Repo den Commit in
`app/requirements.txt` umstellen. Wird ein PR im Original gemergt, fällt er
beim nächsten Merge von `main` von selbst heraus.
