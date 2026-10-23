"""Tests for REST API endpoints."""

import pytest
import json
from unittest.mock import patch
from django.urls import reverse
from rest_framework.test import APIClient

from apps.schemes.models import Scheme
from apps.budgets.models import BudgetRecord
from apps.timeline.models import TimelineEvent


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def scheme(db):
    return Scheme.objects.create(
        name='Pradhan Mantri Awas Yojana',
        abbreviation='PMAY',
        category='housing',
        jurisdiction='central',
        operational_status='active',
    )


@pytest.mark.django_db
class TestSchemeListAPI:
    def test_list_returns_200(self, api_client):
        url = '/api/v1/schemes/'
        resp = api_client.get(url)
        assert resp.status_code == 200

    def test_list_contains_created_scheme(self, api_client, scheme):
        resp = api_client.get('/api/v1/schemes/')
        data = resp.json()
        names = [s['name'] for s in data['results']]
        assert 'Pradhan Mantri Awas Yojana' in names

    def test_search_by_name(self, api_client, scheme):
        resp = api_client.get('/api/v1/schemes/?q=PMAY')
        data = resp.json()
        assert len(data['results']) >= 1

    def test_filter_by_category(self, api_client, scheme):
        resp = api_client.get('/api/v1/schemes/?category=housing')
        data = resp.json()
        assert all(s['category'] == 'housing' for s in data['results'])


@pytest.mark.django_db
class TestSchemeDetailAPI:
    def test_detail_returns_200(self, api_client, scheme):
        resp = api_client.get(f'/api/v1/schemes/{scheme.pk}/')
        assert resp.status_code == 200
        assert resp.json()['name'] == 'Pradhan Mantri Awas Yojana'

    def test_detail_404_for_missing_scheme(self, api_client):
        resp = api_client.get('/api/v1/schemes/99999/')
        assert resp.status_code == 404


@pytest.mark.django_db
class TestSchemeTimelineAPI:
    def test_timeline_returns_200(self, api_client, scheme):
        resp = api_client.get(f'/api/v1/schemes/{scheme.pk}/timeline/')
        assert resp.status_code == 200
        data = resp.json()
        assert 'results' in data

    def test_timeline_ordered_chronologically(self, api_client, scheme):
        from datetime import date
        TimelineEvent.objects.create(
            scheme=scheme, event_type='amendment',
            title='Second event', description='desc', event_date=date(2021, 3, 1),
        )
        TimelineEvent.objects.create(
            scheme=scheme, event_type='launch',
            title='First event', description='desc', event_date=date(2019, 6, 1),
        )
        resp = api_client.get(f'/api/v1/schemes/{scheme.pk}/timeline/')
        results = resp.json()['results']
        assert len(results) == 2
        assert results[0]['event_date'] < results[1]['event_date']


@pytest.mark.django_db
class TestSchemeBudgetAPI:
    def test_budgets_returns_200(self, api_client, scheme):
        resp = api_client.get(f'/api/v1/schemes/{scheme.pk}/budgets/')
        assert resp.status_code == 200

    def test_budget_data_contains_correct_fields(self, api_client, scheme):
        from decimal import Decimal
        BudgetRecord.objects.create(
            scheme=scheme,
            financial_year_start=2023,
            financial_year_end=2024,
            budget_estimate=Decimal('25000.00'),
        )
        resp = api_client.get(f'/api/v1/schemes/{scheme.pk}/budgets/')
        results = resp.json()['results']
        assert len(results) == 1
        assert results[0]['financial_year'] == '2023-24'
        assert float(results[0]['budget_estimate']) == 25000.0


@pytest.mark.django_db
class TestResearchAPI:
    def test_research_validates_short_query(self, api_client):
        resp = api_client.post('/api/v1/research/', {'query': 'ab'}, format='json')
        assert resp.status_code == 400

    @patch('apps.search.orchestrator.ResearchOrchestrator.execute')
    def test_research_returns_job_on_success(self, mock_execute, api_client, db):
        mock_execute.return_value = {'query': 'PM-KISAN', 'scheme_name': 'PM-KISAN'}
        resp = api_client.post('/api/v1/research/', {'query': 'Tell me about PM-KISAN'}, format='json')
        assert resp.status_code == 201
        assert 'query' in resp.json()


@pytest.mark.django_db
class TestFactCheckAPI:
    def test_fact_check_validates_short_claim(self, api_client):
        resp = api_client.post('/api/v1/fact-check/', {'claim': 'short'}, format='json')
        assert resp.status_code == 400

    def test_fact_check_validates_missing_claim(self, api_client):
        resp = api_client.post('/api/v1/fact-check/', {}, format='json')
        assert resp.status_code == 400
