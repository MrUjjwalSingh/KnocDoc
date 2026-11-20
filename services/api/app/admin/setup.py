"""SQLAdmin configuration with authentication and model views."""
from __future__ import annotations

from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.config import get_settings
from app.models.analytics import AnalyticsEvent
from app.models.doctor import Doctor
from app.models.language import DoctorLanguage, Language
from app.models.provider import Provider
from app.models.review import Review
from app.models.search_request import SearchRequest
from app.models.service import Service
from app.models.specialty import Specialty


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        settings = get_settings()

        if username == settings.admin_username and password == settings.admin_password:
            request.session.update({"token": "authenticated"})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        return token == "authenticated"


class ProviderAdmin(ModelView, model=Provider):
    column_list = [
        Provider.name,
        Provider.type,
        Provider.city,
        Provider.verification_status,
        Provider.is_dummy,
        Provider.walk_in_available,
        Provider.updated_at,
    ]
    column_searchable_list = [Provider.name, Provider.city, Provider.address]
    column_filters = [Provider.verification_status, Provider.is_dummy, Provider.type]
    column_sortable_list = [Provider.name, Provider.verification_status, Provider.updated_at]
    name = "Provider"
    name_plural = "Providers"
    icon = "fa-solid fa-hospital"


class DoctorAdmin(ModelView, model=Doctor):
    column_list = [Doctor.full_name, Doctor.provider_id, Doctor.specialty_id, Doctor.is_dummy]
    column_searchable_list = [Doctor.full_name]
    column_filters = [Doctor.is_dummy]
    name = "Doctor"
    name_plural = "Doctors"
    icon = "fa-solid fa-user-doctor"


class SpecialtyAdmin(ModelView, model=Specialty):
    column_list = [Specialty.slug, Specialty.name]
    column_searchable_list = [Specialty.slug, Specialty.name]
    name = "Specialty"
    name_plural = "Specialties"
    icon = "fa-solid fa-stethoscope"


class LanguageAdmin(ModelView, model=Language):
    column_list = [Language.code, Language.name]
    column_searchable_list = [Language.code, Language.name]
    name = "Language"
    name_plural = "Languages"
    icon = "fa-solid fa-language"


class ServiceAdmin(ModelView, model=Service):
    column_list = [
        Service.name,
        Service.provider_id,
        Service.price_min,
        Service.price_max,
        Service.currency,
        Service.last_verified_at,
    ]
    column_searchable_list = [Service.name]
    name = "Service"
    name_plural = "Services"
    icon = "fa-solid fa-briefcase-medical"


class ReviewAdmin(ModelView, model=Review):
    column_list = [
        Review.provider_id,
        Review.rating,
        Review.status,
        Review.actual_amount_paid,
        Review.comment,
        Review.created_at,
    ]
    column_filters = [Review.status, Review.rating]
    column_sortable_list = [Review.rating, Review.created_at, Review.status]
    name = "Review"
    name_plural = "Reviews (Moderation)"
    icon = "fa-solid fa-star"


class AnalyticsEventAdmin(ModelView, model=AnalyticsEvent):
    column_list = [
        AnalyticsEvent.event_name,
        AnalyticsEvent.session_id,
        AnalyticsEvent.created_at,
    ]
    column_filters = [AnalyticsEvent.event_name]
    can_create = False
    can_edit = False
    can_delete = False
    name = "Analytics Event"
    name_plural = "Analytics Events"
    icon = "fa-solid fa-chart-line"


def setup_admin(admin: Admin) -> None:
    admin.add_view(ProviderAdmin)
    admin.add_view(DoctorAdmin)
    admin.add_view(SpecialtyAdmin)
    admin.add_view(LanguageAdmin)
    admin.add_view(ServiceAdmin)
    admin.add_view(ReviewAdmin)
    admin.add_view(AnalyticsEventAdmin)

