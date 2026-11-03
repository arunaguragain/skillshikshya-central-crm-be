from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.callminutes.utils import format_duration, parse_duration_to_seconds
from apps.course.models import Course
from apps.lead.models import (
    LearningMode, Institution, Province, City, LeadSource, Campaign, LeadStatus, LeadPriority,
    LeadTag, LeadType, Lead, LeadCourseInterest, Enrollment, Payment,
    LeadCall, LeadActivity, FollowUp, LeadDocument, Notification,
)


class PrimaryCourseField(serializers.Field):
    """Nested {id, name, price} on read; accepts an int pk or {id} on write."""

    def to_representation(self, value):
        if value is None:
            return None
        return {
            'id': value.id,
            'name': value.name,
            'price': str(value.full_amount) if value.full_amount is not None else None,
        }

    def to_internal_value(self, data):
        course_id = data.get('id') if isinstance(data, dict) else data
        try:
            return Course.objects.get(pk=course_id)
        except (Course.DoesNotExist, TypeError, ValueError):
            raise ValidationError(f'Invalid pk "{course_id}" - course does not exist.')


class LeadSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadSource
        fields = '__all__'


class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = '__all__'


class LeadStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadStatus
        fields = '__all__'


class LeadPrioritySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadPriority
        fields = '__all__'


class LeadTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadTag
        fields = '__all__'


class LeadTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadType
        fields = '__all__'


class LearningModeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningMode
        fields = '__all__'


class InstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institution
        fields = '__all__'


class ProvinceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Province
        fields = '__all__'


class CitySerializer(serializers.ModelSerializer):
    province_name = serializers.CharField(source='province.name', read_only=True)

    class Meta:
        model = City
        fields = '__all__'


class LeadCourseInterestSerializer(serializers.ModelSerializer):
    course_name = serializers.SerializerMethodField()

    class Meta:
        model = LeadCourseInterest
        fields = '__all__'
        read_only_fields = ['lead', 'created_at', 'course_name']

    def get_course_name(self, obj):
        return obj.course.name if obj.course else obj.course_name


class EnrollmentSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', read_only=True)
    lead_name = serializers.CharField(source='lead.full_name', read_only=True)
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    batch_name = serializers.CharField(source='batch.name', read_only=True)
    total_paid = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    remaining_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_full_paid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Enrollment
        fields = '__all__'
        read_only_fields = [
            'lead', 'created_by', 'updated_by', 'created_at', 'updated_at',
            'total_paid', 'remaining_amount', 'is_full_paid',
        ]


class PaymentSerializer(serializers.ModelSerializer):
    received_by_name = serializers.CharField(source='received_by.name', read_only=True)

    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['enrollment', 'received_by', 'created_at']


class LeadMinSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = ['id', 'reference_number', 'full_name', 'phone', 'status', 'priority', 'lead_type', 'lead_score']


class LeadListSerializer(serializers.ModelSerializer):
    status_name = serializers.CharField(source='status.name', read_only=True)
    lead_type_name = serializers.CharField(source='lead_type.name', read_only=True)
    priority_name = serializers.CharField(source='priority.name', read_only=True)
    priority_color = serializers.CharField(source='priority.color', read_only=True)
    status_color = serializers.CharField(source='status.color', read_only=True)
    source_name = serializers.CharField(source='source.name', read_only=True)
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    assigned_counselor_name = serializers.CharField(source='assigned_counselor.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    primary_course = PrimaryCourseField(required=False, allow_null=True)
    province_name = serializers.CharField(source='province.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.name', read_only=True)

    class Meta:
        model = Lead
        fields = '__all__'


class LeadSerializer(serializers.ModelSerializer):
    status_name = serializers.CharField(source='status.name', read_only=True)
    lead_type_name = serializers.CharField(source='lead_type.name', read_only=True)
    priority_name = serializers.CharField(source='priority.name', read_only=True)
    priority_color = serializers.CharField(source='priority.color', read_only=True)
    status_color = serializers.CharField(source='status.color', read_only=True)
    source_name = serializers.CharField(source='source.name', read_only=True)
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    assigned_counselor_name = serializers.CharField(source='assigned_counselor.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    primary_course = PrimaryCourseField(required=False, allow_null=True)
    province_name = serializers.CharField(source='province.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.name', read_only=True)

    call_count = serializers.SerializerMethodField()
    next_followup = serializers.SerializerMethodField()
    enrollment_summary = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = '__all__'
        read_only_fields = [
            'reference_number', 'created_at', 'updated_at', 'created_by', 'updated_by',
            'is_converted', 'converted_at', 'is_deleted', 'deleted_at', 'deleted_by',
            'lead_score',
        ]

    def get_call_count(self, obj):
        return obj.calls.count()

    def get_next_followup(self, obj):
        followup = obj.followups.filter(status='pending').order_by('scheduled_at').first()
        if followup:
            return {
                'id': followup.id,
                'scheduled_at': followup.scheduled_at,
                'purpose': followup.purpose,
                'assigned_to': followup.assigned_to_id,
                'assigned_to_name': followup.assigned_to.name if followup.assigned_to else None,
            }
        return None

    def get_enrollment_summary(self, obj):
        enrollment = obj.enrollments.order_by('-enrollment_date').first()
        if enrollment:
            return {
                'is_enrolled': True,
                'latest_status': enrollment.status,
                'course': enrollment.course.name,
                'batch': enrollment.batch.coursebatch_id if enrollment.batch else None,
            }
        return {'is_enrolled': False, 'latest_status': None, 'course': None, 'batch': None}


class LeadCallSerializer(serializers.ModelSerializer):
    caller_name = serializers.CharField(source='caller', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    duration_input = serializers.CharField(write_only=True, required=False)
    duration_formatted = serializers.SerializerMethodField()

    class Meta:
        model = LeadCall
        fields = '__all__'
        read_only_fields = ['lead', 'created_by', 'created_at']

    def get_duration_formatted(self, obj):
        return format_duration(obj.duration_seconds)

    def to_internal_value(self, data):
        if 'duration_input' in data and data.get('duration_input'):
            try:
                data['duration_seconds'] = parse_duration_to_seconds(
                    data['duration_input'],
                )
            except DjangoValidationError as exc:
                raise serializers.ValidationError({
                    'duration_input': exc.messages[0] if exc.messages else str(exc),
                })
        return super().to_internal_value(data)

    def create(self, validated_data):
        validated_data.pop('duration_input', None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # duration_seconds and caller are locked after creation so the
        # call-minutes ledger cannot be gamed.
        validated_data.pop('duration_seconds', None)
        validated_data.pop('duration_input', None)
        validated_data.pop('caller', None)
        return super().update(instance, validated_data)


class GlobalCallSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source='lead.full_name', read_only=True)
    lead_reference_number = serializers.CharField(
        source='lead.reference_number', read_only=True,
    )
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    duration_formatted = serializers.SerializerMethodField()

    class Meta:
        model = LeadCall
        fields = [
            'id', 'lead', 'lead_name', 'lead_reference_number',
            'call_timestamp', 'direction', 'caller', 'phone_number',
            'duration_seconds', 'duration_formatted', 'outcome', 'notes', 'recording_url',
            'next_followup_at', 'next_action',
            'branch', 'created_by', 'created_by_name', 'created_at',
        ]
        read_only_fields = fields

    def get_duration_formatted(self, obj):
        return format_duration(obj.duration_seconds)


class LeadActivitySerializer(serializers.ModelSerializer):
    performed_by_name = serializers.CharField(source='performed_by.name', read_only=True)

    class Meta:
        model = LeadActivity
        fields = '__all__'
        read_only_fields = ['lead', 'created_at']


class FollowUpSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source='assigned_to.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.name', read_only=True)

    class Meta:
        model = FollowUp
        fields = '__all__'
        read_only_fields = ['lead', 'created_by', 'updated_by', 'created_at', 'updated_at', 'reminder_sent']


class LeadDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.name', read_only=True)

    class Meta:
        model = LeadDocument
        fields = '__all__'
        read_only_fields = ['lead', 'uploaded_by', 'uploaded_at']


class GlobalFollowUpSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source='lead.full_name', read_only=True)
    lead_phone = serializers.CharField(source='lead.phone', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = FollowUp
        fields = [
            'id', 'lead', 'lead_name', 'lead_phone',
            'assigned_to', 'assigned_to_name',
            'scheduled_at', 'purpose', 'status',
            'branch', 'branch_name',
        ]
        read_only_fields = fields


class GlobalEnrollmentSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source='lead.full_name', read_only=True)
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    course_name = serializers.CharField(source='course.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    batch_name = serializers.CharField(source='batch.name', read_only=True)
    total_paid = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    remaining_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_full_paid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            'id', 'lead', 'lead_name',
            'student', 'student_name',
            'course', 'course_name',
            'batch', 'batch_name', 'status', 'enrollment_date',
            'listed_fee', 'agreed_amount',
            'total_paid', 'remaining_amount', 'is_full_paid',
            'branch', 'branch_name',
            'created_at',
        ]
        read_only_fields = fields


class GlobalPaymentSerializer(serializers.ModelSerializer):
    lead = serializers.IntegerField(source='enrollment.lead_id', read_only=True)
    lead_name = serializers.CharField(source='enrollment.lead.full_name', read_only=True)
    course_name = serializers.CharField(source='enrollment.course.name', read_only=True)
    received_by_name = serializers.CharField(source='received_by.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'enrollment',
            'lead', 'lead_name',
            'course_name',
            'amount', 'payment_date',
            'payment_method', 'transaction_reference',
            'status',
            'received_by', 'received_by_name',
            'branch', 'branch_name',
        ]
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['recipient', 'created_at']
