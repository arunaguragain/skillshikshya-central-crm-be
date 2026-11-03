from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.lead.views import (
    LearningModeViewSet, InstitutionViewSet,
    ProvinceViewSet, CityViewSet,
    LeadSourceViewSet, CampaignViewSet, LeadStatusViewSet,
    LeadPriorityViewSet, LeadTagViewSet, LeadTypeViewSet, LeadViewSet,
    LeadCourseInterestViewSet, EnrollmentViewSet, PaymentViewSet,
    GlobalCallViewSet,
    LeadCallViewSet, LeadActivityViewSet, FollowUpViewSet, LeadDocumentViewSet,
    NotificationViewSet,
    GlobalFollowUpViewSet, GlobalEnrollmentViewSet, GlobalPaymentViewSet,
)

router = DefaultRouter()
router.register(r'learning-modes', LearningModeViewSet)
router.register(r'institutions', InstitutionViewSet)
router.register(r'provinces', ProvinceViewSet)
router.register(r'cities', CityViewSet)
router.register(r'lead-sources', LeadSourceViewSet)
router.register(r'campaigns', CampaignViewSet)
router.register(r'lead-statuses', LeadStatusViewSet)
router.register(r'lead-priorities', LeadPriorityViewSet)
router.register(r'lead-tags', LeadTagViewSet)
router.register(r'lead-types', LeadTypeViewSet)
router.register(r'notifications', NotificationViewSet)
router.register(r'leads', LeadViewSet)
router.register(r'followups', GlobalFollowUpViewSet)
router.register(r'enrollments', GlobalEnrollmentViewSet)
router.register(r'payments', GlobalPaymentViewSet)
router.register(r'calls', GlobalCallViewSet)

lead_router = DefaultRouter()
lead_router.register(r'calls', LeadCallViewSet, basename='lead-call')
lead_router.register(r'activities', LeadActivityViewSet, basename='lead-activity')
lead_router.register(r'followups', FollowUpViewSet, basename='lead-followup')
lead_router.register(r'documents', LeadDocumentViewSet, basename='lead-document')
lead_router.register(r'course-interests', LeadCourseInterestViewSet, basename='lead-course-interest')
lead_router.register(r'enrollments', EnrollmentViewSet, basename='lead-enrollment')

enrollment_router = DefaultRouter()
enrollment_router.register(r'payments', PaymentViewSet, basename='enrollment-payment')

urlpatterns = [
    path('', include(router.urls)),
    path('leads/<int:lead_pk>/', include(lead_router.urls)),
    path('leads/<int:lead_pk>/enrollments/<int:enrollment_pk>/', include(enrollment_router.urls)),
]
