#!/usr/bin/env python3
"""
chat_panel.py - Chat Panel Komponente (Chatbot + Message Input Block)
"""

import gradio as gr


def create_chat_panel() -> tuple[gr.Chatbot, gr.Textbox, gr.Button]:
    """Erzeugt die Chat-Spalte (links) mit"""
    with gr.Column(scale=3, elem_classes=["chat-column"]):
        chatbot = gr.Chatbot(
            label="Agent Conversation",
            height=800,
            show_label=True,
            avatar_images=(
                None,
                "https://api.dicebear.com/7.x/bottts/svg?seed=grok"
            ),
            elem_classes=["panel", "chat-panel"]
        )

        with gr.Row():
            msg = gr.Textbox(
                placeholder="Type your message here...",
                scale=8,
                container=False
            )
            send_btn = gr.Button("Send", variant="primary", scale=1)

    return chatbot, msg, send_btn