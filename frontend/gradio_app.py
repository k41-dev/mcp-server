#!/usr/bin/env python3
"""
gradio_app.py - MCP Agent Web UI (Entry Point)

Diese Datei ist bewusst sehr dünn gehalten.
Die komplette UI-Logik befindet sich in layout.py.
"""

from layout import create_ui


if __name__ == "__main__":
    demo = create_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )