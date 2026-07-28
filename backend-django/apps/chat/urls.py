from django.urls import path

from . import views

urlpatterns = [
    path(
        "<uuid:relationship_id>/messages",
        views.messages,
        name="chat-messages",
    ),
    path(
        "<uuid:relationship_id>/messages/send",
        views.send_message,
        name="chat-send",
    ),
    path(
        "<uuid:relationship_id>/read",
        views.mark_read,
        name="chat-mark-read",
    ),
    path(
        "<uuid:relationship_id>/unread",
        views.unread_count,
        name="chat-unread",
    ),
    path(
        "messages/<uuid:message_id>",
        views.delete_message,
        name="chat-delete",
    ),
    path(
        "messages/<uuid:message_id>/reactions",
        views.toggle_reaction,
        name="chat-react",
    ),
]
