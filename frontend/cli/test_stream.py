#!/usr/bin/env python3
"""
Kleiner Test-Client für den /mcp/stream Endpoint.
Zeigt den Stream schön zusammengesetzt an.
"""

import httpx
import json
import sys

def test_stream(provider: str = "grok", message: str = "Erzähl mir einen kurzen Witz."):
    url = "http://localhost:8321/mcp/stream"

    payload = {
        "params": {
            "provider": provider,
            "messages": [
                {"role": "user", "content": message}
            ],
            "temperature": 0.7
        }
    }

    print(f"🚀 Starte Stream mit Provider: {provider}")
    print("-" * 60)

    full_text = ""

    with httpx.stream("POST", url, json=payload, timeout=60.0) as response:
        if response.status_code != 200:
            print(f"❌ Fehler: {response.status_code}")
            print(response.text)
            return

        for line in response.iter_lines():
            if not line:
                continue

            line = line.decode("utf-8") if isinstance(line, bytes) else line

            if line.startswith("data: "):
                content = line[6:]  # "data: " entfernen

                if content == "[DONE]":
                    print("\n" + "-" * 60)
                    print("✅ Stream beendet.")
                    break
                elif content.startswith("[ERROR]"):
                    print(f"\n❌ Stream-Fehler: {content}")
                    break
                else:
                    # Chunk zum Gesamttext hinzufügen und ausgeben
                    full_text += content
                    # Live-Ausgabe (ohne Zeilenumbruch bei jedem Chunk)
                    print(content, end="", flush=True)

    print("\n\n" + "=" * 60)
    print("Vollständiger Text:")
    print(full_text)
    print("=" * 60)


if __name__ == "__main__":
    # Beispielaufrufe:
    # test_stream("grok", "Erzähl mir einen kurzen, lustigen Witz auf Deutsch.")
    # test_stream("ollama", "Schreibe ein kurzes Gedicht über den Bodensee.")

    provider = sys.argv[1] if len(sys.argv) > 1 else "grok"
    message = sys.argv[2] if len(sys.argv) > 2 else "Erzähl mir einen kurzen Witz auf Deutsch."

    test_stream(provider, message)