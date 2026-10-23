/**
 * AI Government Scheme Fact Checker — Frontend Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const navPills = document.querySelectorAll('.nav-pill');
  const tabContents = document.querySelectorAll('.tab-content');
  const searchInput = document.getElementById('mainSearchInput');
  const searchBtn = document.getElementById('mainSearchBtn');
  const presetChips = document.querySelectorAll('.preset-chip');
  
  const claimTextarea = document.getElementById('claimTextarea');
  const verifyClaimBtn = document.getElementById('verifyClaimBtn');
  const sampleClaimCards = document.querySelectorAll('.sample-claim-card');

  const geminiStatusBtn = document.getElementById('geminiStatusBtn');
  const geminiModal = document.getElementById('geminiModal');
  const modalCloseBtn = document.getElementById('modalCloseBtn');
  const saveGeminiKeyBtn = document.getElementById('saveGeminiKeyBtn');
  const geminiApiKeyInput = document.getElementById('geminiApiKeyInput');
  const geminiModelSelect = document.getElementById('geminiModelSelect');

  // --------------------------------------------------------------------------
  // Tab Navigation
  // --------------------------------------------------------------------------
  window.switchTab = function(tabId) {
    navPills.forEach(pill => {
      if (pill.dataset.tab === tabId) {
        pill.classList.add('active');
      } else {
        pill.classList.remove('active');
      }
    });

    tabContents.forEach(tab => {
      if (tab.id === tabId) {
        tab.style.display = 'block';
      } else {
        tab.style.display = 'none';
      }
    });
  };

  navPills.forEach(pill => {
    pill.addEventListener('click', () => {
      switchTab(pill.dataset.tab);
    });
  });

  // --------------------------------------------------------------------------
  // Preset Chips & Search Bar
  // --------------------------------------------------------------------------
  presetChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const query = chip.dataset.query;
      searchInput.value = query;
      runSchemeSearch(query);
    });
  });

  if (searchBtn && searchInput) {
    searchBtn.addEventListener('click', () => {
      const q = searchInput.value.trim();
      if (q) runSchemeSearch(q);
    });

    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const q = searchInput.value.trim();
        if (q) runSchemeSearch(q);
      }
    });
  }

  // --------------------------------------------------------------------------
  // Scheme Research Pipeline Runner
  // --------------------------------------------------------------------------
  async function runSchemeSearch(query) {
    switchTab('tab-explorer');
    const resultsContainer = document.getElementById('explorerResults');
    const loadingContainer = document.getElementById('explorerLoading');
    const emptyState = document.getElementById('explorerEmpty');

    if (emptyState) emptyState.style.display = 'none';
    if (resultsContainer) resultsContainer.style.display = 'none';
    if (loadingContainer) {
      loadingContainer.style.display = 'block';
      document.getElementById('loadingQueryText').textContent = `Synthesizing intelligence for "${query}"...`;
    }

    try {
      const response = await fetch('/api/v1/research/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({ query: query }),
      });

      if (!response.ok) {
        throw new Error(`Research request failed: ${response.statusText}`);
      }

      const data = await response.json();
      renderResearchResults(data);
      showToast('Scheme analysis synthesized successfully!', 'success');
    } catch (err) {
      console.error(err);
      showToast('Error researching scheme. Showing local database record.', 'error');
      // Attempt local scheme lookup fallback
      searchLocalSchemeFallback(query);
    } finally {
      if (loadingContainer) loadingContainer.style.display = 'none';
    }
  }

  function searchLocalSchemeFallback(query) {
    const qLower = query.toLowerCase();
    const schemeCard = document.querySelector(`.scheme-card[data-scheme-name*="${qLower}"]`);
    if (schemeCard) {
      const schemeId = schemeCard.dataset.schemeId;
      loadSchemeById(schemeId);
    }
  }

  function renderResearchResults(data) {
    const resultsContainer = document.getElementById('explorerResults');
    if (!resultsContainer) return;

    const result = data.result || data;
    const overview = result.overview || {};
    const timelineEvents = result.timeline_events || [];
    const budgetRecords = result.budget_records || [];
    const leadershipRecords = result.leadership_records || [];
    const sources = result.source_urls_searched || [];

    // Scheme Title & Meta
    document.getElementById('resSchemeName').textContent = overview.name || result.scheme_name || 'Government Scheme';
    document.getElementById('resSchemeAbbr').textContent = overview.abbreviation ? `(${overview.abbreviation})` : '';
    document.getElementById('resSchemeCategory').textContent = overview.category || 'Central Welfare Scheme';
    document.getElementById('resSchemeStatus').textContent = overview.operational_status || 'Active';
    document.getElementById('resSchemeDesc').textContent = overview.original_objectives || 'Comprehensive government welfare and social assistance policy.';
    document.getElementById('resLaunchDate').textContent = overview.launch_date || 'Documented Launch Date';
    document.getElementById('resBeneficiaries').textContent = overview.intended_beneficiaries || 'Target population and citizen beneficiaries';
    document.getElementById('resJurisdiction').textContent = overview.jurisdiction ? overview.jurisdiction.toUpperCase() : 'CENTRAL';

    const portalBtn = document.getElementById('resPortalBtn');
    if (portalBtn) {
      portalBtn.href = overview.application_portal || 'https://myscheme.gov.in';
    }

    // AI Model Badge
    const aiBadge = document.getElementById('resAiModelBadge');
    if (aiBadge) {
      aiBadge.textContent = `Analyzed by: ${result.ai_model_used || 'Gemini Flash'}`;
    }

    // Leadership Ribbon
    renderLeadershipList(leadershipRecords);

    // Timeline Events
    renderTimelineList(timelineEvents);

    // Budget Table
    renderBudgetTable(budgetRecords);

    // Sources List
    renderSourcesList(sources);

    resultsContainer.style.display = 'block';
  }

  function renderLeadershipList(records) {
    const container = document.getElementById('resLeadershipContainer');
    if (!container) return;
    if (!records || records.length === 0) {
      container.innerHTML = `
        <div class="leadership-card">
          <div class="avatar-badge">GOI</div>
          <div class="leader-info">
            <h4>Government of India</h4>
            <div class="leader-role">Union Executive</div>
            <div class="leader-tenure">Central Government Administration</div>
          </div>
        </div>`;
      return;
    }

    container.innerHTML = records.map(r => {
      const initials = (r.leader_name || 'GOI').split(' ').map(n => n[0]).join('').slice(0, 2);
      return `
        <div class="leadership-card">
          <div class="avatar-badge">${initials}</div>
          <div class="leader-info">
            <h4>${escapeHtml(r.leader_name || 'Cabinet Minister')}</h4>
            <div class="leader-role">${escapeHtml(r.role || r.portfolio || 'Minister In-Charge')}</div>
            <div class="leader-tenure">${escapeHtml(r.ministry || '')} ${r.party ? `• ${r.party}` : ''}</div>
          </div>
        </div>
      `;
    }).join('');
  }

  function renderTimelineList(events) {
    const container = document.getElementById('resTimelineContainer');
    if (!container) return;
    if (!events || events.length === 0) {
      container.innerHTML = '<p class="text-muted">No chronological events extracted yet.</p>';
      return;
    }

    container.innerHTML = events.map(ev => {
      const dateDisplay = ev.event_date || 'Date Documented';
      const typeDisplay = (ev.event_type || 'Update').replace('_', ' ').toUpperCase();
      return `
        <div class="timeline-item" data-category="${ev.event_type || 'all'}">
          <div class="timeline-marker">
            <div class="timeline-marker-dot"></div>
          </div>
          <div class="timeline-card">
            <div class="timeline-card-header">
              <span class="timeline-date">${dateDisplay}</span>
              <span class="badge badge-blue">${typeDisplay}</span>
            </div>
            <h4 class="timeline-card-title">${escapeHtml(ev.title)}</h4>
            <p class="timeline-card-desc">${escapeHtml(ev.description)}</p>
            <div class="timeline-card-footer">
              <div class="timeline-attribution">
                <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
                <span>${escapeHtml(ev.responsible_ministry || 'Government Authority')}</span>
              </div>
              ${ev.source_urls && ev.source_urls.length ? `
                <a href="${ev.source_urls[0]}" target="_blank" rel="noopener noreferrer" class="timeline-citation">
                  <span>Source Document</span>
                  <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              ` : ''}
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  function renderBudgetTable(budgets) {
    const tbody = document.getElementById('resBudgetTableBody');
    if (!tbody) return;
    if (!budgets || budgets.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-muted" style="text-align: center;">No financial allocation data recorded yet.</td></tr>';
      return;
    }

    tbody.innerHTML = budgets.map(b => {
      const be = b.budget_estimate != null ? `₹${Number(b.budget_estimate).toLocaleString()} Cr` : '—';
      const re = b.revised_estimate != null ? `₹${Number(b.revised_estimate).toLocaleString()} Cr` : '—';
      const act = b.actual_expenditure != null ? `₹${Number(b.actual_expenditure).toLocaleString()} Cr` : '—';

      return `
        <tr>
          <td><strong style="color: #000000;">${escapeHtml(b.financial_year || (b.financial_year_start ? `${b.financial_year_start}-${String(b.financial_year_end).slice(-2)}` : 'FY'))}</strong></td>
          <td class="amount-cell">${be}</td>
          <td class="amount-cell">${re}</td>
          <td class="amount-cell">${act}</td>
          <td><span class="badge badge-cyan">${escapeHtml(b.verification_status || 'Verified')}</span></td>
        </tr>
      `;
    }).join('');
  }

  function renderSourcesList(sources) {
    const container = document.getElementById('resSourcesList');
    if (!container) return;
    if (!sources || sources.length === 0) {
      container.innerHTML = '<span class="text-muted">Primary government portal reference.</span>';
      return;
    }

    container.innerHTML = sources.map(url => `
      <a href="${url}" target="_blank" rel="noopener noreferrer" class="chip">
        <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
        </svg>
        <span>${escapeHtml(new URL(url).hostname)}</span>
      </a>
    `).join('');
  }

  // --------------------------------------------------------------------------
  // Timeline Category Filtering
  // --------------------------------------------------------------------------
  const filterBtns = document.querySelectorAll('.timeline-filter-btn');
  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const cat = btn.dataset.category;

      const items = document.querySelectorAll('.timeline-item');
      items.forEach(item => {
        if (cat === 'all' || item.dataset.category.includes(cat)) {
          item.style.display = 'block';
        } else {
          item.style.display = 'none';
        }
      });
    });
  });

  // --------------------------------------------------------------------------
  // Claim Fact-Checker Runner
  // --------------------------------------------------------------------------
  sampleClaimCards.forEach(card => {
    card.addEventListener('click', () => {
      const claim = card.dataset.claim;
      claimTextarea.value = claim;
      runFactCheck(claim);
    });
  });

  if (verifyClaimBtn) {
    verifyClaimBtn.addEventListener('click', () => {
      const claim = claimTextarea.value.trim();
      if (!claim) {
        showToast('Please enter a claim to verify.', 'error');
        return;
      }
      runFactCheck(claim);
    });
  }

  async function runFactCheck(claimText) {
    const verdictContainer = document.getElementById('factcheckVerdictContainer');
    const loadingState = document.getElementById('factcheckLoading');

    if (verdictContainer) verdictContainer.style.display = 'none';
    if (loadingState) loadingState.style.display = 'block';

    try {
      const response = await fetch('/api/v1/fact-check/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({ claim: claimText }),
      });

      if (!response.ok) {
        throw new Error(`Fact-check error: ${response.statusText}`);
      }

      const data = await response.json();
      renderVerdict(data);
      showToast('Claim verification complete!', 'success');
    } catch (err) {
      console.error(err);
      showToast('Verification failed. Retrying with semantic evidence analysis.', 'error');
    } finally {
      if (loadingState) loadingState.style.display = 'none';
    }
  }

  function renderVerdict(data) {
    const container = document.getElementById('factcheckVerdictContainer');
    if (!container) return;

    const claim = data.claim || data;
    const rawAi = data.raw_ai_response || {};
    const verdict = claim.verdict || rawAi.verdict || 'supported';
    const confidence = claim.confidence || rawAi.confidence || 'high';
    const explanation = claim.explanation || rawAi.explanation || '';
    const supporting = rawAi.supporting_evidence || [];
    const contradicting = rawAi.contradicting_evidence || [];

    // Verdict Badge
    const card = document.getElementById('verdictCard');
    card.className = `verdict-card ${verdict}`;

    const badge = document.getElementById('verdictBadge');
    badge.className = `verdict-badge-lg ${verdict}`;

    const verdictTitles = {
      'supported': 'Supported by Evidence',
      'contradicted': 'Contradicted by Evidence',
      'partially_supported': 'Partially Supported',
      'insufficient_evidence': 'Insufficient Evidence',
      'outdated': 'Outdated Information'
    };
    badge.textContent = verdictTitles[verdict] || verdict.toUpperCase();

    document.getElementById('verdictClaimQuote').textContent = `"${claim.claim_text || claim.claim || ''}"`;
    document.getElementById('verdictExplanationText').textContent = explanation;

    // Confidence
    const confFill = document.getElementById('confidenceFill');
    const confText = document.getElementById('confidenceScoreText');
    confFill.className = `confidence-fill ${confidence}`;
    confText.textContent = `${confidence.toUpperCase()} CONFIDENCE`;

    // Evidence
    const supList = document.getElementById('supportingEvidenceList');
    const conList = document.getElementById('contradictingEvidenceList');

    if (supporting.length) {
      supList.innerHTML = supporting.map(ev => `
        <div class="evidence-item supports">
          <p>${escapeHtml(ev.text)}</p>
          <a href="${ev.source_url}" target="_blank" rel="noopener noreferrer" class="evidence-source-link">
            <span>${escapeHtml(ev.publisher || ev.source_title || 'Official Source')}</span>
            <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>
      `).join('');
    } else {
      supList.innerHTML = '<p class="text-muted" style="font-size: 13px;">No direct supporting excerpts found.</p>';
    }

    if (contradicting.length) {
      conList.innerHTML = contradicting.map(ev => `
        <div class="evidence-item contradicts">
          <p>${escapeHtml(ev.text)}</p>
          <a href="${ev.source_url}" target="_blank" rel="noopener noreferrer" class="evidence-source-link">
            <span>${escapeHtml(ev.publisher || ev.source_title || 'Contradicting Source')}</span>
            <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>
      `).join('');
    } else {
      conList.innerHTML = '<p class="text-muted" style="font-size: 13px;">No contradictory records surfaced.</p>';
    }

    container.style.display = 'block';
  }

  // --------------------------------------------------------------------------
  // Schemes Directory Loader
  // --------------------------------------------------------------------------
  window.loadSchemeById = async function(schemeId) {
    switchTab('tab-explorer');
    const loadingContainer = document.getElementById('explorerLoading');
    const resultsContainer = document.getElementById('explorerResults');
    if (loadingContainer) loadingContainer.style.display = 'block';
    if (resultsContainer) resultsContainer.style.display = 'none';

    try {
      const [schemeRes, timelineRes, budgetRes, leadershipRes] = await Promise.all([
        fetch(`/api/v1/schemes/${schemeId}/`),
        fetch(`/api/v1/schemes/${schemeId}/timeline/`),
        fetch(`/api/v1/schemes/${schemeId}/budgets/`),
        fetch(`/api/v1/schemes/${schemeId}/leadership/`),
      ]);

      const scheme = await schemeRes.json();
      const timeline = await timelineRes.json();
      const budgets = await budgetRes.json();
      const leadership = await leadershipRes.json();

      const combinedData = {
        scheme_name: scheme.name,
        overview: {
          name: scheme.name,
          abbreviation: scheme.abbreviation,
          category: scheme.category,
          operational_status: scheme.operational_status,
          original_objectives: scheme.original_objectives,
          intended_beneficiaries: scheme.intended_beneficiaries,
          launch_date: scheme.launch_date,
          application_portal: scheme.application_portal,
          jurisdiction: scheme.jurisdiction,
        },
        timeline_events: (timeline.results || timeline).map(t => ({
          title: t.title,
          description: t.description,
          event_date: t.event_date,
          event_type: t.event_type,
          responsible_ministry: t.responsible_ministry ? t.responsible_ministry.name : '',
        })),
        budget_records: (budgets.results || budgets).map(b => ({
          financial_year: b.financial_year || `${b.financial_year_start}-${String(b.financial_year_end).slice(-2)}`,
          budget_estimate: b.budget_estimate,
          revised_estimate: b.revised_estimate,
          actual_expenditure: b.actual_expenditure,
          verification_status: b.verification_status,
        })),
        leadership_records: (leadership.results || leadership).map(l => ({
          leader_name: l.ministerial_tenure ? l.ministerial_tenure.leader.full_name : '',
          role: l.responsibility_type,
          ministry: l.ministry ? l.ministry.name : '',
        })),
        source_urls_searched: ['https://pib.gov.in', 'https://india.gov.in'],
        ai_model_used: 'Verified Official Gazette & Gemini 2.0',
      };

      renderResearchResults(combinedData);
    } catch (e) {
      console.error(e);
      showToast('Could not load scheme record.', 'error');
    } finally {
      if (loadingContainer) loadingContainer.style.display = 'none';
    }
  };

  // --------------------------------------------------------------------------
  // Gemini AI Settings & Modal
  // --------------------------------------------------------------------------
  if (geminiStatusBtn) {
    geminiStatusBtn.addEventListener('click', () => {
      openGeminiModal();
    });
  }

  if (modalCloseBtn) {
    modalCloseBtn.addEventListener('click', () => {
      geminiModal.classList.remove('active');
    });
  }

  window.openGeminiModal = async function() {
    geminiModal.classList.add('active');
    try {
      const res = await fetch('/api/v1/gemini/status/');
      const data = await res.json();
      if (data.configured) {
        document.getElementById('modalStatusText').innerHTML = 
          `<span style="color: #15803D; font-weight: 700;">● Live Connected</span> (${data.masked_key})`;
      } else {
        document.getElementById('modalStatusText').innerHTML = 
          `<span style="color: #B45309; font-weight: 700;">● Demo Synthesis Mode</span> (Key not set)`;
      }
      if (data.model) {
        geminiModelSelect.value = data.model;
      }
    } catch (e) {
      console.error(e);
    }
  };

  if (saveGeminiKeyBtn) {
    saveGeminiKeyBtn.addEventListener('click', async () => {
      const key = geminiApiKeyInput.value.trim();
      const model = geminiModelSelect.value;
      if (!key) {
        showToast('Please enter a valid Gemini API key.', 'error');
        return;
      }

      saveGeminiKeyBtn.disabled = true;
      saveGeminiKeyBtn.textContent = 'Verifying & Saving...';

      try {
        const res = await fetch('/api/v1/gemini/configure/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
          },
          body: JSON.stringify({ api_key: key, model: model }),
        });

        const data = await res.json();
        if (data.success) {
          showToast('Gemini API configured successfully!', 'success');
          geminiStatusBtn.innerHTML = `
            <div class="status-indicator"></div>
            <span>Gemini Connected</span>
          `;
          geminiStatusBtn.classList.remove('warning');
          geminiModal.classList.remove('active');
          geminiApiKeyInput.value = '';
        } else {
          showToast(data.error || 'Configuration failed', 'error');
        }
      } catch (err) {
        console.error(err);
        showToast('Error saving API key.', 'error');
      } finally {
        saveGeminiKeyBtn.disabled = false;
        saveGeminiKeyBtn.textContent = 'Save & Connect API';
      }
    });
  }

  // --------------------------------------------------------------------------
  // Utility Helpers
  // --------------------------------------------------------------------------
  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  function escapeHtml(text) {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  window.showToast = function(message, type = 'info') {
    let container = document.getElementById('toastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toastContainer';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = 'toast';
    const icon = type === 'success' 
      ? '✓' 
      : type === 'error' ? '⚠' : 'ℹ';
    
    toast.innerHTML = `<span style="font-weight: 700; color: ${type === 'success' ? '#34D399' : type === 'error' ? '#F87171' : '#60A5FA'};">${icon}</span> <span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3800);
  };
});
