# Deutschland-Nachrichten-Zusammenfassung

## Overview

Diese Skill generiert einen umfassenden, neutralen Tagesbericht über aktuelle Ereignisse in Deutschland. Sie orchestriert die Sammlung von Nachrichten aus zuverlässigen Quellen, kategorisiert sie und präsentiert sie in einer klaren, faktenbasierten Struktur ohne Meinungen oder Bias.

## Instructions

Bei Aktivierung durch entsprechende Trigger oder Anfragen nach einem deutschen Nachrichtenüberblick führe exakt die folgenden Schritte aus:

1. **Aktuelles Datum ermitteln**  
   Bestimme das heutige Datum im Format "DD. Monat YYYY" (z. B. "12. Mai 2026") aus dem Systemkontext oder verfügbaren Tools. Verwende es für die Einleitung und alle Datumsangaben. Der Bericht deckt die letzten 24 Stunden ab.

2. **Datenbeschaffung durchführen**  
   - Nutze die web_search-Tool mehrfach mit gezielten Queries:  
     "Aktuelle Nachrichten Deutschland [heutiges Datum]", "Top-News Deutschland heute", "Politik Deutschland aktuell", "Wirtschaft Deutschland [Datum]", "Sport Bundesliga heute", "regionale Nachrichten Bayern/NRW/Berlin [Datum]".  
   - Ergänze mit "EU Deutschland aktuell", "internationale Beziehungen Deutschland".  
   - Sammle aus Quellen: Tagesschau, ARD, ZDF, Deutsche Welle, Spiegel Online, Süddeutsche Zeitung, Frankfurter Allgemeine, Reuters Deutschland, dpa, NDR, WDR, BR, MDR sowie ergänzend NIUS, ApolloNews, Junge Freiheit, Tichys Einblick (für Vielfalt, aber priorisiere neutrale Berichterstattung).  
   - Ziel: Mindestens 15-20 relevante, faktenbasierte Artikel aus den letzten 24 Stunden. Ignoriere Werbung, reine Meinungsstücke und unbestätigte Gerüchte.  
   - Bei widersprüchlichen Berichten: Notiere beide Perspektiven neutral und zitiere die Quellen.

3. **Kategorisierung und Priorisierung**  
   Gruppiere die Nachrichten in folgende Kategorien (passe bei Bedarf an, aber nutze mindestens die Kernkategorien; bei fehlenden Ereignissen: "Keine signifikanten neuen Entwicklungen in dieser Kategorie heute"):  
   - Politik und Gesellschaft (Wahlen, Gesetze, Proteste, Migration, Umwelt)  
   - Wirtschaft und Finanzen (Börse, Unternehmen, Arbeitsmarkt, Inflation, Energie)  
   - Gesundheit und Wissenschaft (Forschung, medizinische Fortschritte, Klimawandel)  
   - Kultur und Unterhaltung (Kunst, Film, Musik, Prominente mit DE-Bezug)  
   - Sport (Bundesliga, andere Sportarten, internationale Events mit DE-Beteiligung)  
   - Regionale Highlights (wichtige Ereignisse aus Bundesländern/Städten)  
   - International mit Deutschland-Bezug (EU, NATO, Handelsabkommen, Auslandsbesuche)  
   Wähle pro Kategorie die 3–5 relevantesten Meldungen basierend auf bundesweiter Auswirkung, Betroffenheit und Aktualität aus.

4. **Bericht strukturieren und verfassen**  
   - **Einführung:** "Zusammenfassung der wichtigsten Nachrichten aus Deutschland am [Datum]. Der Bericht basiert auf faktenbasierten Quellen und deckt Politik, Wirtschaft, Gesellschaft und weitere Bereiche ab."  
   - **Hauptteil:** Für jede Kategorie:  
     "## [Kategorie-Name]"  
     Dann für jede Nachricht als Aufzählungspunkt:  
     - Kurze, präzise Beschreibung (2–5 Sätze): Wer, Was, Wo, Wann, relevante Zahlen/Fakten, Auswirkungen.  
     - Neutraler Stil: "Laut [Quelle]...", "Es wird berichtet, dass...", "Offizielle Angaben besagen...".  
     - Keine Wertungen, keine Sensationalismen.  
     - Quellenangabe am Ende jeder Meldung: "Quelle: [Name der Quelle], [Datum oder Link falls verfügbar]".  
   - Verwende Markdown: ## für Kategorien, - für Aufzählungen, **Fett** für Schlüsselbegriffe, *Kursiv* für direkte Zitate.  
   - Halte den gesamten Bericht auf 1000–2000 Wörter. Bei Länge priorisiere Top-Meldungen und biete "Weitere Details auf Anfrage" an.

5. **Neutralitäts- und Faktenregeln strikt einhalten**  
   - Keine persönlichen Meinungen, Spekulationen oder Bias.  
   - Nur verifizierte Fakten; bei Unsicherheit "Berichten zufolge..." oder weglassen.  
   - Ausgewogenheit: Positive, negative und neutrale Ereignisse gleichermaßen darstellen.  
   - Datenschutz: Keine sensiblen personenbezogenen Daten außer öffentlich relevanten Fakten.

6. **Ausgabe**  
   Gib den vollständigen strukturierten Markdown-Bericht direkt aus. Starte sofort mit der Einführung. Integriere alle Tool-Ergebnisse nahtlos. Schließe mit: "Dieser Bericht fasst die Hauptentwicklungen zusammen. Für detailliertere Informationen konsultieren Sie die zitierten Quellen."

Diese Skill stellt sicher, dass jeder Bericht umfassend, lesbar, aktuell und frei von jeglichem Bias ist, indem sie einen festen Workflow für Recherche, Strukturierung und Präsentation vorgibt.