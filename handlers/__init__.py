from aiogram import Router
from handlers.common import router as common_router
from handlers.quiz import router as quiz_router
from handlers.client_flow import router as client_router
from handlers.admin import router as admin_router

# List of all routing modules to register in dispatcher (excl. referral)
all_routers = [
    common_router,
    quiz_router,
    client_router,
    admin_router
]
