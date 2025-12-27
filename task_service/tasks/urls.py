from django.urls import path
from .views import (
    CreateTaskView,
    ListTasksView,
    TaskDetailView,
    AssignTaskView,
    ChangeStatusView,
    PresignAttachmentView,
    ConfirmAttachmentView,
    TaskLogsView,
)

urlpatterns = [
    path("tasks/", CreateTaskView.as_view(), name="create-task"),              
    path("tasks/list/", ListTasksView.as_view(), name="list-tasks"),           
    path("tasks/<int:pk>/", TaskDetailView.as_view(), name="task-detail"),     

    path("tasks/<int:pk>/assign/", AssignTaskView.as_view(), name="assign-task"),  
    path("tasks/<int:pk>/status/", ChangeStatusView.as_view(), name="change-status"),  

    path("tasks/<int:pk>/attachments/presign/",PresignAttachmentView.as_view(),name="task-attachment-presign"),
    path("tasks/<int:pk>/attachments/confirm/",ConfirmAttachmentView.as_view(),name="task-attachment-confirm"),

    
    path("tasks/<int:pk>/logs/", TaskLogsView.as_view(), name="task-logs"),     
]
