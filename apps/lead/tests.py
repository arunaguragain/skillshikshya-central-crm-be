from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.course.models import Course
from apps.lead.models import Lead

User = get_user_model()


class PrimaryCourseNestedTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@test.com', name='Admin', password='pass', is_staff=True,
        )
        self.client.force_authenticate(self.admin)
        self.course = Course.objects.create(name='Python Advanced', full_amount=30000)
        self.lead = Lead.objects.create(
            full_name='Test Lead', phone='9800000055', primary_course=self.course,
        )

    def test_detail_returns_nested_primary_course(self):
        response = self.client.get(f'/api/leads/{self.lead.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pc = response.data['primary_course']
        self.assertEqual(pc, {'id': self.course.id, 'name': 'Python Advanced', 'price': '30000.00'})
        self.assertNotIn('primary_course_name', response.data)

    def test_null_primary_course(self):
        lead = Lead.objects.create(full_name='No Course', phone='9800000056')
        response = self.client.get(f'/api/leads/{lead.id}/')
        self.assertIsNone(response.data['primary_course'])

    def test_patch_accepts_nested_object(self):
        other = Course.objects.create(name='Flutter', full_amount=25000)
        response = self.client.patch(
            f'/api/leads/{self.lead.id}/',
            {'primary_course': {'id': other.id}}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['primary_course']['id'], other.id)

    def test_patch_still_accepts_bare_int(self):
        bare = Course.objects.create(name='DevOps', full_amount=None)
        response = self.client.patch(
            f'/api/leads/{self.lead.id}/',
            {'primary_course': bare.id}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['primary_course'], {
            'id': bare.id, 'name': 'DevOps', 'price': None,
        })

    def test_patch_invalid_course_rejected(self):
        response = self.client.patch(
            f'/api/leads/{self.lead.id}/',
            {'primary_course': 99999}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class LeadSourceDeletionTests(APITestCase):
    def setUp(self):
        from apps.lead.models import LeadSource
        self.admin = User.objects.create_user(
            email='admin@test.com', name='Admin', password='pass', is_staff=True,
        )
        self.client.force_authenticate(self.admin)
        self.protected = LeadSource.objects.create(
            name='Protected Source', is_protected=True,
        )
        self.used = LeadSource.objects.create(name='Used Source')
        Lead.objects.create(full_name='Someone', phone='1', source=self.used)
        self.free = LeadSource.objects.create(name='Free Source')

    def test_protected_source_cannot_be_deleted(self):
        response = self.client.delete(f'/api/lead-sources/{self.protected.id}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('protected', response.data['detail'])
        self.assertTrue(
            __import__('apps.lead.models', fromlist=['LeadSource'])
            .LeadSource.objects.filter(pk=self.protected.id).exists()
        )

    def test_used_source_cannot_be_deleted(self):
        response = self.client.delete(f'/api/lead-sources/{self.used.id}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('used in leads', response.data['detail'])

    def test_unused_unprotected_source_deletes(self):
        response = self.client.delete(f'/api/lead-sources/{self.free.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_is_protected_toggle_via_patch(self):
        response = self.client.patch(
            f'/api/lead-sources/{self.free.id}/',
            {'is_protected': True}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_protected'])
        # now deletion must be blocked
        blocked = self.client.delete(f'/api/lead-sources/{self.free.id}/')
        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST)

    def test_model_level_delete_raises_protected_error(self):
        from django.db import transaction
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            with transaction.atomic():
                self.protected.delete()
        with self.assertRaises(ProtectedError):
            with transaction.atomic():
                self.used.delete()


class GlobalCallListTests(APITestCase):
    def setUp(self):
        from datetime import timedelta
        from apps.branch.models import Branch
        from django.utils import timezone as tz
        from apps.lead.models import LeadCall

        self.admin = User.objects.create_user(
            email='admin@test.com', name='Admin', password='pass', is_staff=True,
        )
        self.counselor = User.objects.create_user(
            email='c9@test.com', name='Counselor Nine', password='pass',
            is_staff=True,
        )
        self.client.force_authenticate(self.admin)
        self.branch = Branch.objects.create(name='Biratnagar', code='BRT')
        self.lead = Lead.objects.create(full_name='Call Person', phone='9811111111')
        from apps.student.models import Student
        self.student = Student.objects.create(
            full_name='Call Person', phone='9811111111', lead=self.lead,
        )
        now = tz.now()
        self.recent_call = LeadCall.objects.create(
            lead=self.lead, call_timestamp=now, direction='outbound',
            caller='Counselor Nine', phone_number='9811111111',
            duration_seconds=270, outcome='interested',
            created_by=self.counselor, branch=self.branch,
        )
        self.old_call = LeadCall.objects.create(
            lead=self.lead, call_timestamp=now - timedelta(days=10),
            direction='inbound', caller='Someone Else',
            phone_number='9822222222', duration_seconds=60,
            created_by=self.admin, branch=self.branch,
        )

    def test_list_returns_all_calls_newest_first(self):
        response = self.client.get('/api/calls/')
        self.assertEqual(response.status_code, 200)
        ids = [r['id'] for r in response.data['results']]
        self.assertEqual(ids, [self.recent_call.id, self.old_call.id])
        row = response.data['results'][0]
        self.assertEqual(row['lead_name'], 'Call Person')
        self.assertTrue(row['lead_reference_number'].startswith('LD-'))

    def test_filter_direction(self):
        response = self.client.get('/api/calls/?direction=inbound')
        self.assertEqual([r['id'] for r in response.data['results']], [self.old_call.id])

    def test_filter_created_by_user(self):
        response = self.client.get(f'/api/calls/?created_by={self.counselor.id}')
        self.assertEqual(
            [r['id'] for r in response.data['results']], [self.recent_call.id],
        )

    def test_filter_by_student(self):
        response = self.client.get(f'/api/calls/?student={self.student.id}')
        self.assertEqual(response.data['count'], 2)

    def test_filter_date_range(self):
        from django.utils import timezone as tz
        today = tz.now().date().isoformat()
        response = self.client.get(f'/api/calls/?call_timestamp__gte={today}')
        self.assertEqual(
            [r['id'] for r in response.data['results']], [self.recent_call.id],
        )

    def test_search(self):
        response = self.client.get('/api/calls/?search=Counselor Nine')
        self.assertEqual(response.data['count'], 1)
        search_lead = self.client.get('/api/calls/?search=Call Person')
        self.assertEqual(search_lead.data['count'], 2)

    def test_summary_totals_average_and_connect_rate(self):
        from django.utils import timezone as tz
        from apps.lead.models import LeadCall

        LeadCall.objects.create(
            lead=self.lead, call_timestamp=tz.now(), direction='outbound',
            caller='Zero Caller', phone_number='9800000000',
            duration_seconds=0, branch=self.branch,
        )
        LeadCall.objects.create(
            lead=self.lead, call_timestamp=tz.now(), direction='outbound',
            caller='One Second Caller', phone_number='9800000003',
            duration_seconds=1, branch=self.branch,
        )
        response = self.client.get('/api/calls/summary/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_calls'], 4)
        self.assertEqual(response.data['inbound'], 1)
        self.assertEqual(response.data['outbound'], 3)
        self.assertEqual(response.data['total_seconds'], 331)
        self.assertEqual(response.data['total_formatted'], '05:31')
        self.assertEqual(response.data['avg_seconds'], 83)
        self.assertIsInstance(response.data['avg_seconds'], int)
        self.assertEqual(response.data['connected_calls'], 3)
        self.assertEqual(response.data['connect_rate'], 0.75)

    def test_summary_by_user_top_ten_and_unknown_creator(self):
        from django.utils import timezone as tz
        from apps.lead.models import LeadCall

        now = tz.now()
        for index in range(9):
            user = User.objects.create_user(
                email=f'caller{index}@test.com', name=f'Caller {index}',
                password='pass',
            )
            LeadCall.objects.create(
                lead=self.lead, call_timestamp=now, direction='outbound',
                caller=f'Caller {index}', phone_number=f'980001{index:04d}',
                duration_seconds=10, created_by=user, branch=self.branch,
            )

        LeadCall.objects.create(
            lead=self.lead, call_timestamp=now, direction='outbound',
            caller='Counselor Nine', phone_number='9800020001',
            duration_seconds=10, created_by=self.counselor, branch=self.branch,
        )
        for index in range(2):
            LeadCall.objects.create(
                lead=self.lead, call_timestamp=now, direction='outbound',
                caller='Unknown Caller', phone_number=f'980003{index:04d}',
                duration_seconds=10, created_by=None, branch=self.branch,
            )

        response = self.client.get('/api/calls/summary/')
        by_user = response.data['by_user']

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(by_user), 10)
        call_counts = [row['calls'] for row in by_user]
        self.assertEqual(call_counts, sorted(call_counts, reverse=True))

        unknown = next(row for row in by_user if row['user_id'] is None)
        self.assertEqual(unknown['name'], 'Unknown')
        self.assertEqual(unknown['calls'], 2)

        counselor_index = next(
            index for index, row in enumerate(by_user)
            if row['user_id'] == self.counselor.id
        )
        admin_index = next(
            index for index, row in enumerate(by_user)
            if row['user_id'] == self.admin.id
        )
        self.assertEqual(by_user[counselor_index]['calls'], 2)
        self.assertEqual(by_user[admin_index]['calls'], 1)
        self.assertLess(counselor_index, admin_index)

    def test_summary_uses_kathmandu_date(self):
        from datetime import datetime, timezone
        from apps.lead.models import LeadCall

        LeadCall.objects.create(
            lead=self.lead,
            call_timestamp=datetime(2026, 10, 28, 20, 0, tzinfo=timezone.utc),
            direction='outbound', caller='Late Caller',
            phone_number='9800000001', duration_seconds=30,
            created_by=self.counselor, branch=self.branch,
        )
        response = self.client.get('/api/calls/summary/')

        day = next(
            row for row in response.data['by_day']
            if row['date'].isoformat() == '2026-10-29'
        )
        self.assertEqual(day['calls'], 1)
        self.assertEqual(day['seconds'], 30)

    def test_summary_empty_result_returns_zeros(self):
        response = self.client.get('/api/calls/summary/?caller=NoMatchingCaller')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_calls'], 0)
        self.assertEqual(response.data['inbound'], 0)
        self.assertEqual(response.data['outbound'], 0)
        self.assertEqual(response.data['total_seconds'], 0)
        self.assertEqual(response.data['total_formatted'], '00:00')
        self.assertEqual(response.data['avg_seconds'], 0)
        self.assertEqual(response.data['connected_calls'], 0)
        self.assertEqual(response.data['connect_rate'], 0)
        self.assertEqual(response.data['by_day'], [])
        self.assertEqual(response.data['by_user'], [])

    def test_summary_respects_direction_filter(self):
        response = self.client.get('/api/calls/summary/?direction=inbound')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_calls'], 1)
        self.assertEqual(response.data['inbound'], 1)
        self.assertEqual(response.data['outbound'], 0)
        self.assertEqual(response.data['total_seconds'], 60)

    def test_summary_query_count_is_fixed(self):
        from django.utils import timezone as tz
        from apps.lead.models import LeadCall

        LeadCall.objects.create(
            lead=self.lead, call_timestamp=tz.now(), direction='outbound',
            caller='Third Caller', phone_number='9800000002',
            duration_seconds=15, created_by=self.counselor, branch=self.branch,
        )
        with self.assertNumQueries(3):
            three_call_response = self.client.get('/api/calls/summary/')
        self.assertEqual(three_call_response.data['total_calls'], 3)

        LeadCall.objects.bulk_create([
            LeadCall(
                lead=self.lead, call_timestamp=tz.now(), direction='outbound',
                caller=f'Bulk Caller {index}', phone_number=f'980000{index:04d}',
                duration_seconds=index, created_by=self.counselor,
                branch=self.branch,
            )
            for index in range(27)
        ])
        with self.assertNumQueries(3):
            thirty_call_response = self.client.get('/api/calls/summary/')
        self.assertEqual(thirty_call_response.data['total_calls'], 30)

    def test_branch_scoping_for_non_staff(self):
        from apps.branch.models import Branch
        from apps.lead.models import LeadCall
        other_branch = Branch.objects.create(name='Dharan', code='DHR')
        other_admin = User.objects.create_user(
            email='br@test.com', name='BR User', password='x',
            branch=other_branch,
        )
        LeadCall.objects.filter(id=self.recent_call.id).update(branch=None)
        self.client.force_authenticate(other_admin)
        response = self.client.get('/api/calls/')
        self.assertNotIn(self.recent_call.id, [r['id'] for r in response.data['results']])
