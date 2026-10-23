"""Leadership models."""

from django.db import models


class PoliticalParty(models.Model):
    """Political party."""

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=300, unique=True)
    abbreviation = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=100, default='India')
    founded_year = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Political Party'
        verbose_name_plural = 'Political Parties'

    def __str__(self) -> str:
        return self.abbreviation or self.name


class Government(models.Model):
    """Government record."""

    LEVEL_CENTRAL = 'central'
    LEVEL_STATE = 'state'
    LEVEL_CHOICES = [
        (LEVEL_CENTRAL, 'Central Government'),
        (LEVEL_STATE, 'State Government'),
    ]

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(
        max_length=300,
        help_text='Descriptive name (e.g. "NDA Government, 2019-2024")',
    )
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default=LEVEL_CENTRAL)
    country = models.CharField(max_length=100, default='India')
    state = models.CharField(max_length=100, blank=True)
    ruling_party = models.ForeignKey(
        PoliticalParty,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='governments_led',
    )
    coalition_name = models.CharField(
        max_length=200,
        blank=True,
        help_text='Name of ruling coalition if applicable (e.g. NDA, UPA)',
    )
    term_start = models.DateField(null=True, blank=True)
    term_end = models.DateField(null=True, blank=True, help_text='Null if currently in power')
    source = models.ForeignKey(
        'sources.Source',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='government_records',
    )

    class Meta:
        ordering = ['-term_start']
        verbose_name = 'Government'
        verbose_name_plural = 'Governments'

    def __str__(self) -> str:
        return self.name


class Leader(models.Model):
    """Political or administrative leader."""

    id = models.BigAutoField(primary_key=True)
    full_name = models.CharField(max_length=300)
    party = models.ForeignKey(
        PoliticalParty,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='leaders',
    )
    birth_year = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['full_name']
        verbose_name = 'Leader'
        verbose_name_plural = 'Leaders'

    def __str__(self) -> str:
        return self.full_name


class MinistryOrDepartment(models.Model):
    """Ministry or department."""

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=300)
    abbreviation = models.CharField(max_length=50, blank=True)
    government = models.ForeignKey(
        Government,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='ministries',
    )
    parent_ministry = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='departments',
        help_text='Parent ministry if this is a department',
    )
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Ministry / Department'
        verbose_name_plural = 'Ministries / Departments'

    def __str__(self) -> str:
        return self.abbreviation or self.name


class MinisterialTenure(models.Model):
    """Leader tenure record."""

    ROLE_PM = 'prime_minister'
    ROLE_CM = 'chief_minister'
    ROLE_CABINET = 'cabinet_minister'
    ROLE_STATE = 'minister_of_state'
    ROLE_SECRETARY = 'secretary'
    ROLE_OTHER = 'other'

    ROLE_CHOICES = [
        (ROLE_PM, 'Prime Minister'),
        (ROLE_CM, 'Chief Minister'),
        (ROLE_CABINET, 'Cabinet Minister'),
        (ROLE_STATE, 'Minister of State'),
        (ROLE_SECRETARY, 'Secretary'),
        (ROLE_OTHER, 'Other'),
    ]

    id = models.BigAutoField(primary_key=True)
    leader = models.ForeignKey(
        Leader,
        on_delete=models.CASCADE,
        related_name='tenures',
    )
    ministry = models.ForeignKey(
        MinistryOrDepartment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='tenures',
    )
    government = models.ForeignKey(
        Government,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='tenures',
    )
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default=ROLE_CABINET)
    portfolio = models.CharField(
        max_length=300,
        blank=True,
        help_text='Portfolio or responsibility description',
    )
    tenure_start = models.DateField(null=True, blank=True)
    tenure_end = models.DateField(null=True, blank=True)
    source = models.ForeignKey(
        'sources.Source',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='ministerial_tenures',
    )

    class Meta:
        ordering = ['-tenure_start']
        verbose_name = 'Ministerial Tenure'
        verbose_name_plural = 'Ministerial Tenures'

    def __str__(self) -> str:
        role_label = dict(self.ROLE_CHOICES).get(self.role, self.role)
        return f'{self.leader.full_name} — {role_label} ({self.tenure_start} to {self.tenure_end or "present"})'


class SchemeResponsibility(models.Model):
    """Scheme leadership assignment."""

    RESPONSIBILITY_LAUNCH = 'launch'
    RESPONSIBILITY_ADMINISTRATION = 'administration'
    RESPONSIBILITY_AMENDMENT = 'amendment'
    RESPONSIBILITY_CHOICES = [
        (RESPONSIBILITY_LAUNCH, 'Scheme Launch'),
        (RESPONSIBILITY_ADMINISTRATION, 'Ongoing Administration'),
        (RESPONSIBILITY_AMENDMENT, 'Specific Amendment'),
    ]

    id = models.BigAutoField(primary_key=True)
    scheme = models.ForeignKey(
        'schemes.Scheme',
        on_delete=models.CASCADE,
        related_name='scheme_responsibilities',
    )
    ministerial_tenure = models.ForeignKey(
        MinisterialTenure,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='scheme_responsibilities',
    )
    ministry = models.ForeignKey(
        MinistryOrDepartment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='scheme_responsibilities',
    )
    responsibility_type = models.CharField(
        max_length=30,
        choices=RESPONSIBILITY_CHOICES,
        default=RESPONSIBILITY_ADMINISTRATION,
    )
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    source = models.ForeignKey(
        'sources.Source',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='scheme_responsibilities',
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['scheme', '-effective_from']
        verbose_name = 'Scheme Responsibility'
        verbose_name_plural = 'Scheme Responsibilities'

    def __str__(self) -> str:
        return f'{self.scheme.name} — {self.responsibility_type} ({self.effective_from})'
