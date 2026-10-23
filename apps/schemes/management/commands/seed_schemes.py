"""
Seed script to pre-populate verified Indian Government Schemes,
Leadership tenures, Budget histories, Timeline events, and Sources.
"""

from datetime import date
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.schemes.models import Scheme, SchemeAlias, SchemeBenefit, EligibilityRule
from apps.leadership.models import PoliticalParty, Government, Leader, MinistryOrDepartment, MinisterialTenure, SchemeResponsibility
from apps.budgets.models import BudgetRecord
from apps.timeline.models import TimelineEvent
from apps.sources.models import Source, EvidenceExcerpt
from apps.factcheck.models import Claim, ClaimEvidence


class Command(BaseCommand):
    help = 'Seeds initial verified government schemes and fact-checking data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding verified scheme intelligence data...')

        # 1. Political Parties & Governments
        bjp, _ = PoliticalParty.objects.get_or_create(
            name='Bharatiya Janata Party',
            defaults={'abbreviation': 'BJP', 'country': 'India'}
        )
        inc, _ = PoliticalParty.objects.get_or_create(
            name='Indian National Congress',
            defaults={'abbreviation': 'INC', 'country': 'India'}
        )

        nda_gov, _ = Government.objects.get_or_create(
            name='National Democratic Alliance (NDA)',
            defaults={
                'ruling_party': bjp,
                'level': Government.LEVEL_CENTRAL,
                'country': 'India',
                'term_start': date(2014, 5, 26),
            }
        )
        upa_gov, _ = Government.objects.get_or_create(
            name='United Progressive Alliance (UPA)',
            defaults={
                'ruling_party': inc,
                'level': Government.LEVEL_CENTRAL,
                'country': 'India',
                'term_start': date(2004, 5, 22),
                'term_end': date(2014, 5, 26),
            }
        )

        # 2. Leaders
        modi, _ = Leader.objects.get_or_create(full_name='Narendra Modi', defaults={'party': bjp})
        manmohan, _ = Leader.objects.get_or_create(full_name='Manmohan Singh', defaults={'party': inc})
        tomar, _ = Leader.objects.get_or_create(full_name='Narendra Singh Tomar', defaults={'party': bjp})
        mandaviya, _ = Leader.objects.get_or_create(full_name='Mansukh Mandaviya', defaults={'party': bjp})

        # 3. Ministries
        agri_min, _ = MinistryOrDepartment.objects.get_or_create(
            name='Ministry of Agriculture and Farmers Welfare',
            defaults={'abbreviation': 'MoA&FW', 'government': nda_gov}
        )
        rural_min, _ = MinistryOrDepartment.objects.get_or_create(
            name='Ministry of Rural Development',
            defaults={'abbreviation': 'MoRD', 'government': nda_gov}
        )
        health_min, _ = MinistryOrDepartment.objects.get_or_create(
            name='Ministry of Health and Family Welfare',
            defaults={'abbreviation': 'MoHFW', 'government': nda_gov}
        )

        # 4. Ministerial Tenures
        tomar_tenure, _ = MinisterialTenure.objects.get_or_create(
            leader=tomar,
            ministry=agri_min,
            government=nda_gov,
            portfolio='Union Minister of Agriculture and Farmers Welfare',
            role=MinisterialTenure.ROLE_CABINET,
            tenure_start=date(2019, 5, 30),
            defaults={'tenure_end': date(2023, 12, 7)}
        )
        mandaviya_tenure, _ = MinisterialTenure.objects.get_or_create(
            leader=mandaviya,
            ministry=health_min,
            government=nda_gov,
            portfolio='Union Minister of Health and Family Welfare',
            role=MinisterialTenure.ROLE_CABINET,
            tenure_start=date(2021, 7, 7),
            defaults={'tenure_end': date(2024, 6, 9)}
        )

        # =====================================================================
        # SCHEME 1: PM-KISAN
        # =====================================================================
        pmkisan, _ = Scheme.objects.get_or_create(
            name='Pradhan Mantri Kisan Samman Nidhi',
            defaults={
                'abbreviation': 'PM-KISAN',
                'category': 'agriculture',
                'jurisdiction': Scheme.JURISDICTION_CENTRAL,
                'launch_date': date(2019, 2, 24),
                'original_objectives': 'Provide income support of Rs 6,000 per year in three equal installments to farmer families to augment their financial needs.',
                'intended_beneficiaries': 'All landholding farmer families with cultivable land in their names.',
                'application_portal': 'https://pmkisan.gov.in',
                'operational_status': Scheme.STATUS_ACTIVE,
            }
        )
        SchemeAlias.objects.get_or_create(scheme=pmkisan, alias='PM Kisan')
        SchemeAlias.objects.get_or_create(scheme=pmkisan, alias='Kisan Samman Nidhi')

        SchemeBenefit.objects.get_or_create(
            scheme=pmkisan,
            benefit_type='Financial Support',
            defaults={
                'description': 'Direct benefit transfer of Rs 6,000 per year directly into verified bank accounts in three 4-monthly cycles of Rs 2,000 each.',
                'amount': 6000.0,
                'currency': 'INR',
                'effective_from': date(2018, 12, 1),
            }
        )

        EligibilityRule.objects.get_or_create(
            scheme=pmkisan,
            criterion='Landholding Requirement',
            defaults={
                'description': 'All landholding farmer families having cultivable landholding in their names (subject to exclusion criteria).',
                'effective_from': date(2019, 2, 24),
            }
        )
        EligibilityRule.objects.get_or_create(
            scheme=pmkisan,
            criterion='Identity & e-KYC Verification',
            defaults={
                'description': 'Aadhaar-seeded bank account and completed e-KYC on the PM-KISAN portal.',
                'effective_from': date(2022, 5, 21),
            }
        )

        SchemeResponsibility.objects.get_or_create(
            scheme=pmkisan,
            ministry=agri_min,
            responsibility_type=SchemeResponsibility.RESPONSIBILITY_LAUNCH,
            effective_from=date(2019, 2, 24),
            defaults={'ministerial_tenure': tomar_tenure}
        )

        # PM-KISAN Budgets
        budgets_pmkisan = [
            (2019, 2020, 75000.0, 54370.0, 48714.0),
            (2020, 2021, 75000.0, 65000.0, 60990.0),
            (2021, 2022, 65000.0, 67500.0, 66825.0),
            (2022, 2023, 68000.0, 60000.0, 58254.0),
            (2023, 2024, 60000.0, 60000.0, 60000.0),
            (2024, 2025, 60000.0, None, None),
        ]
        for fy_s, fy_e, be, re, act in budgets_pmkisan:
            BudgetRecord.objects.get_or_create(
                scheme=pmkisan,
                financial_year_start=fy_s,
                financial_year_end=fy_e,
                defaults={
                    'budget_estimate': be,
                    'revised_estimate': re,
                    'actual_expenditure': act,
                    'amount_unit': 'crore',
                    'currency': 'INR',
                    'central_share': 100.0,
                    'state_share': 0.0,
                    'notes': 'Union Budget Expenditure Profile, Ministry of Finance',
                    'verification_status': BudgetRecord.STATUS_VERIFIED,
                }
            )

        fin_min, _ = MinistryOrDepartment.objects.get_or_create(
            name='Ministry of Finance',
            defaults={'abbreviation': 'MoF', 'government': nda_gov}
        )

        # PM-KISAN Timeline Events
        TimelineEvent.objects.get_or_create(
            scheme=pmkisan,
            title='Interim Budget Announcement',
            defaults={
                'event_type': TimelineEvent.EVENT_LAUNCH,
                'event_date': date(2019, 2, 1),
                'description': 'Announced during the Interim Budget speech by Finance Minister Piyush Goyal with retroactive effect from December 1, 2018.',
                'government': nda_gov,
                'responsible_ministry': fin_min,
                'verification_status': TimelineEvent.VERIFICATION_VERIFIED,
            }
        )
        TimelineEvent.objects.get_or_create(
            scheme=pmkisan,
            title='Formal Launch by Prime Minister Narendra Modi',
            defaults={
                'event_type': TimelineEvent.EVENT_LAUNCH,
                'event_date': date(2019, 2, 24),
                'description': 'Formally inaugurated at Gorakhpur, Uttar Pradesh, transferring the first installment of Rs 2,000 to over 1 crore farmers.',
                'government': nda_gov,
                'responsible_ministry': agri_min,
                'responsible_leader': modi,
                'verification_status': TimelineEvent.VERIFICATION_VERIFIED,
            }
        )
        TimelineEvent.objects.get_or_create(
            scheme=pmkisan,
            title='Expansion to All Landholding Farmers',
            defaults={
                'event_type': TimelineEvent.EVENT_ELIGIBILITY,
                'event_date': date(2019, 5, 31),
                'description': 'Union Cabinet removed the 2-hectare landholding ceiling, extending coverage to all 14.5 crore farmer families regardless of size.',
                'government': nda_gov,
                'responsible_ministry': agri_min,
                'verification_status': TimelineEvent.VERIFICATION_VERIFIED,
            }
        )
        TimelineEvent.objects.get_or_create(
            scheme=pmkisan,
            title='Mandatory Aadhaar e-KYC and Land Seeding',
            defaults={
                'event_type': TimelineEvent.EVENT_AMENDMENT,
                'event_date': date(2022, 5, 21),
                'description': 'Government introduced mandatory Aadhaar e-KYC, physical land verification, and NPCI bank seeding to eliminate non-eligible recipients.',
                'government': nda_gov,
                'responsible_ministry': agri_min,
                'responsible_leader': tomar,
                'verification_status': TimelineEvent.VERIFICATION_VERIFIED,
            }
        )

        # Sources for PM-KISAN
        src_pib_kisan, _ = Source.objects.get_or_create(
            url='https://pib.gov.in/PressReleasePage.aspx?PRID=1566139',
            defaults={
                'title': 'PM launches Pradhan Mantri Kisan Samman Nidhi from Gorakhpur',
                'publisher': 'Press Information Bureau, Government of India',
                'published_date': date(2019, 2, 24),
                'source_category': Source.CATEGORY_PIB,
                'reliability': Source.RELIABILITY_HIGH,
            }
        )
        src_pib_kisan.schemes.add(pmkisan)

        src_portal_kisan, _ = Source.objects.get_or_create(
            url='https://pmkisan.gov.in',
            defaults={
                'title': 'PM-KISAN Official Operational Guidelines and DBT Framework',
                'publisher': 'Department of Agriculture and Farmers Welfare',
                'source_category': Source.CATEGORY_OFFICIAL_PORTAL,
                'reliability': Source.RELIABILITY_HIGH,
            }
        )
        src_portal_kisan.schemes.add(pmkisan)

        # =====================================================================
        # SCHEME 2: MGNREGA
        # =====================================================================
        mgnrega, _ = Scheme.objects.get_or_create(
            name='Mahatma Gandhi National Rural Employment Guarantee Act',
            defaults={
                'abbreviation': 'MGNREGA',
                'category': 'livelihood',
                'jurisdiction': Scheme.JURISDICTION_CENTRAL,
                'launch_date': date(2006, 2, 2),
                'original_objectives': 'Enhance livelihood security in rural areas by providing at least 100 days of guaranteed wage employment in a financial year to every rural household whose adult members volunteer to do unskilled manual work.',
                'intended_beneficiaries': 'Rural adult household members willing to do unskilled manual labor.',
                'application_portal': 'https://nrega.nic.in',
                'operational_status': Scheme.STATUS_ACTIVE,
            }
        )
        SchemeAlias.objects.get_or_create(scheme=mgnrega, alias='NREGA')
        SchemeAlias.objects.get_or_create(scheme=mgnrega, alias='MNREGA')

        budgets_mgnrega = [
            (2020, 2021, 61500.0, 111500.0, 111170.0),  # COVID relief surge
            (2021, 2022, 73000.0, 98000.0, 98467.0),
            (2022, 2023, 73000.0, 89400.0, 90810.0),
            (2023, 2024, 60000.0, 86000.0, 86000.0),
            (2024, 2025, 86000.0, None, None),
        ]
        for fy_s, fy_e, be, re, act in budgets_mgnrega:
            BudgetRecord.objects.get_or_create(
                scheme=mgnrega,
                financial_year_start=fy_s,
                financial_year_end=fy_e,
                defaults={
                    'budget_estimate': be,
                    'revised_estimate': re,
                    'actual_expenditure': act,
                    'amount_unit': 'crore',
                    'currency': 'INR',
                    'central_share': 90.0,
                    'state_share': 10.0,
                    'notes': 'Ministry of Finance / PRS Legislative Research Analysis',
                    'verification_status': BudgetRecord.STATUS_VERIFIED,
                }
            )

        TimelineEvent.objects.get_or_create(
            scheme=mgnrega,
            title='Enactment of the National Rural Employment Guarantee Act',
            defaults={
                'event_type': TimelineEvent.EVENT_LAUNCH,
                'event_date': date(2005, 8, 23),
                'description': 'Parliament passed the NREGA legislation under the UPA government, received Presidential assent on September 5, 2005.',
                'government': upa_gov,
                'responsible_ministry': rural_min,
                'responsible_leader': manmohan,
                'verification_status': TimelineEvent.VERIFICATION_VERIFIED,
            }
        )
        TimelineEvent.objects.get_or_create(
            scheme=mgnrega,
            title='Renamed to Mahatma Gandhi NREGA',
            defaults={
                'event_type': TimelineEvent.EVENT_AMENDMENT,
                'event_date': date(2009, 10, 2),
                'description': 'On the 140th birth anniversary of Mahatma Gandhi, NREGA was formally rechristened as MGNREGA via an amendment to the Act.',
                'government': upa_gov,
                'responsible_ministry': rural_min,
                'verification_status': TimelineEvent.VERIFICATION_VERIFIED,
            }
        )
        TimelineEvent.objects.get_or_create(
            scheme=mgnrega,
            title='Record COVID-19 Pandemic Allocation (Rs 1.11 Lakh Cr)',
            defaults={
                'event_type': TimelineEvent.EVENT_BUDGET,
                'event_date': date(2020, 5, 17),
                'description': 'Under the Atmanirbhar Bharat Abhiyan, government pumped an additional Rs 40,000 crore into MGNREGA to provide employment for returning migrant workers.',
                'government': nda_gov,
                'responsible_ministry': fin_min,
                'verification_status': TimelineEvent.VERIFICATION_VERIFIED,
            }
        )
        TimelineEvent.objects.get_or_create(
            scheme=mgnrega,
            title='Mandatory Aadhaar-Based Payment System (ABPS)',
            defaults={
                'event_type': TimelineEvent.EVENT_AMENDMENT,
                'event_date': date(2024, 1, 1),
                'description': 'Ministry of Rural Development made ABPS strictly mandatory for all wage disbursements to prevent leakages and duplicate job cards.',
                'government': nda_gov,
                'responsible_ministry': rural_min,
                'verification_status': TimelineEvent.VERIFICATION_VERIFIED,
            }
        )

        # =====================================================================
        # SCHEME 3: AYUSHMAN BHARAT (PM-JAY)
        # =====================================================================
        pmjay, _ = Scheme.objects.get_or_create(
            name='Ayushman Bharat - Pradhan Mantri Jan Arogya Yojana',
            defaults={
                'abbreviation': 'PM-JAY',
                'category': 'health',
                'jurisdiction': Scheme.JURISDICTION_CENTRAL,
                'launch_date': date(2018, 9, 23),
                'original_objectives': 'Provide health cover of up to Rs 5 lakh per family per year for secondary and tertiary care hospitalization to over 12 crore poor and vulnerable families.',
                'intended_beneficiaries': 'Bottom 40% vulnerable population identified by SECC 2011 data, expanded to all senior citizens aged 70+ in 2024.',
                'application_portal': 'https://beneficiary.nha.gov.in',
                'operational_status': Scheme.STATUS_ACTIVE,
            }
        )
        SchemeAlias.objects.get_or_create(scheme=pmjay, alias='Ayushman Bharat')
        SchemeAlias.objects.get_or_create(scheme=pmjay, alias='PMJAY')

        budgets_pmjay = [
            (2021, 2022, 6400.0, 3199.0, 3115.0),
            (2022, 2023, 6400.0, 6400.0, 6048.0),
            (2023, 2024, 7200.0, 6800.0, 6800.0),
            (2024, 2025, 7300.0, None, None),
        ]
        for fy_s, fy_e, be, re, act in budgets_pmjay:
            BudgetRecord.objects.get_or_create(
                scheme=pmjay,
                financial_year_start=fy_s,
                financial_year_end=fy_e,
                defaults={
                    'budget_estimate': be,
                    'revised_estimate': re,
                    'actual_expenditure': act,
                    'amount_unit': 'crore',
                    'currency': 'INR',
                    'central_share': 60.0,
                    'state_share': 40.0,
                    'notes': 'National Health Authority Annual Report',
                    'verification_status': BudgetRecord.STATUS_VERIFIED,
                }
            )

        TimelineEvent.objects.get_or_create(
            scheme=pmjay,
            title='Nationwide Launch by PM Narendra Modi',
            defaults={
                'event_type': TimelineEvent.EVENT_LAUNCH,
                'event_date': date(2018, 9, 23),
                'description': 'Officially rolled out from Ranchi, Jharkhand as the worlds largest government-funded health insurance assurance scheme.',
                'government': nda_gov,
                'responsible_ministry': health_min,
                'responsible_leader': modi,
                'verification_status': TimelineEvent.VERIFICATION_VERIFIED,
            }
        )
        TimelineEvent.objects.get_or_create(
            scheme=pmjay,
            title='Universal Coverage for All Senior Citizens Aged 70+',
            defaults={
                'event_type': TimelineEvent.EVENT_ELIGIBILITY,
                'event_date': date(2024, 9, 11),
                'description': 'Union Cabinet approved free health insurance coverage up to Rs 5 lakh for all citizens aged 70 and above, regardless of socio-economic status.',
                'government': nda_gov,
                'responsible_ministry': health_min,
                'verification_status': TimelineEvent.VERIFICATION_VERIFIED,
            }
        )

        # =====================================================================
        # SEED FACT CHECK CLAIMS
        # =====================================================================
        claim1, _ = Claim.objects.get_or_create(
            claim_text='PM-KISAN provides Rs 6,000 per year directly to eligible farmers bank accounts in three equal installments.',
            defaults={
                'scheme': pmkisan,
                'verdict': Claim.STATUS_SUPPORTED,
                'explanation': 'Confirmed from official MoA&FW guidelines. Under PM-KISAN, Rs 6,000 per year is disbursed via DBT in three installments of Rs 2,000 each every 4 months.',
                'confidence': Claim.CONFIDENCE_HIGH,
                'confidence_explanation': 'Supported directly by statutory Ministry of Agriculture operational guidelines and DBT registers.',
                'verified_at': timezone.now(),
            }
        )
        ClaimEvidence.objects.get_or_create(
            claim=claim1,
            source=src_portal_kisan,
            stance='supports',
            defaults={'relevance_note': 'Primary guidelines confirm Rs 6,000/yr in three installments'}
        )

        claim2, _ = Claim.objects.get_or_create(
            claim_text='The Union Government reduced the budget allocation for MGNREGA in Budget 2023-24 compared to previous years.',
            defaults={
                'scheme': mgnrega,
                'verdict': Claim.STATUS_PARTIAL,
                'explanation': 'Budget Estimate (BE) for FY 2023-24 was set at Rs 60,000 crore, down from RE of Rs 89,400 crore in 2022-23. However, supplementary grants later revised actual funding up to Rs 86,000 crore.',
                'confidence': Claim.CONFIDENCE_HIGH,
                'confidence_explanation': 'Budget documents confirm initial BE reduction, but supplementary grants restored funding.',
                'verified_at': timezone.now(),
            }
        )

        claim3, _ = Claim.objects.get_or_create(
            claim_text='PM-KISAN scheme was originally introduced and launched by the UPA government in 2012.',
            defaults={
                'scheme': pmkisan,
                'verdict': Claim.STATUS_CONTRADICTED,
                'explanation': 'Official government gazette and PIB archives prove that PM-KISAN was announced on 1 February 2019 and launched on 24 February 2019 under the NDA government by Prime Minister Narendra Modi.',
                'confidence': Claim.CONFIDENCE_HIGH,
                'confidence_explanation': 'Primary launch notifications and budget speeches directly contradict this assertion.',
                'verified_at': timezone.now(),
            }
        )
        ClaimEvidence.objects.get_or_create(
            claim=claim3,
            source=src_pib_kisan,
            stance='contradicts',
            defaults={'relevance_note': 'PIB release confirms launch on 24 Feb 2019 by PM Narendra Modi'}
        )

        claim4, _ = Claim.objects.get_or_create(
            claim_text='Ayushman Bharat PM-JAY provides health insurance coverage up to Rs 5 lakh per family per year.',
            defaults={
                'scheme': pmjay,
                'verdict': Claim.STATUS_SUPPORTED,
                'explanation': 'National Health Authority guidelines state that every eligible family receives up to Rs 5,00,000 per annum for secondary and tertiary hospitalization nationwide.',
                'confidence': Claim.CONFIDENCE_HIGH,
                'confidence_explanation': 'Explicitly stated across all NHA circulars and empirical claim settlement records.',
                'verified_at': timezone.now(),
            }
        )

        self.stdout.write(self.style.SUCCESS('Successfully seeded verified schemes, budgets, timelines, and claims!'))
