APP_CSS = """
Screen {
    layout: vertical;
}

#body {
    height: 1fr;
}

#sidebar {
    width: 20;
    min-width: 12;
    border-right: solid $primary;
}

#session-actions {
    height: 3;
    width: 100%;
}

#new-session {
    width: 1fr;
}

#delete-session {
    width: 5;
}

#sessions {
    height: 1fr;
}

.session-item {
    height: 1;
}

#main {
    width: 1fr;
}

#transcript {
    height: 1fr;
    padding: 1;
}

#manage-list {
    height: 1fr;
    padding: 1;
}

.message {
    margin-bottom: 1;
    padding: 0 1;
}

.user {
    border-left: heavy $accent;
}

.assistant {
    border-left: heavy $success;
}

.ignored {
    color: $text-muted;
    border-left: heavy gray;
}

.status {
    color: $text-muted;
    padding: 0 1;
}

#token-usage {
    height: 1;
    color: $text-muted;
    padding: 0 1;
}

#prompt {
    height: 3;
}
"""
