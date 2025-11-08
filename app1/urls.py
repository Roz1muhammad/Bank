from django.urls import path
from .views import jsonrpc_view

urlpatterns = [
    path('api/', jsonrpc_view, name='json_rpc_api'),
]
