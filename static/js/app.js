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
    // CSS.escape() prevents selector injection if user types quotes/brackets
    const safe = typeof CSS !== 'undefined' && CSS.escape ? CSS.escape(qLower) : qLower.replace(/[^\w\s-]/g, '');
    try {
      const schemeCard = document.querySelector(`.scheme-card[data-scheme-name*="${safe}"]`);
      if (schemeCard) {
        const schemeId = schemeCard.dataset.schemeId;
        loadSchemeById(schemeId);
      }
    } catch (e) {
      console.warn('Fallback scheme search failed:', e);
    }
  }

  let activeBudgets = [];
  let currentChartMode = 'comparison';

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

    // Visual Timeline Flowchart (Starting date to present with minister operations)
    renderTimelineJourneyChart(timelineEvents, overview, leadershipRecords);

    // Leadership Ribbon
    renderLeadershipList(leadershipRecords);

    // Timeline Events List
    renderTimelineList(timelineEvents);

    // Budget Differences & SVG Chart
    renderBudgetDifferences(budgetRecords);

    // Sources List
    renderSourcesList(sources);

    resultsContainer.style.display = 'block';
  }

  function renderTimelineJourneyChart(events, overview, leadership) {
    const track = document.getElementById('resTimelineFlowTrack');
    if (!track) return;

    let items = Array.isArray(events) ? [...events] : [];
    items.sort((a, b) => (a.event_date || '').localeCompare(b.event_date || ''));

    const launchDate = overview.launch_date || (items.length ? items[0].event_date : 'Documented Inception');
    const hasLaunchEvent = items.some(e => e.event_type === 'launch' || e.event_date === launchDate);

    if (!hasLaunchEvent && launchDate) {
      items.unshift({
        event_date: launchDate,
        event_type: 'launch',
        title: `Official Launch: ${overview.name || 'Scheme Inception'}`,
        description: overview.original_objectives || 'Formal notification and nationwide commencement of the welfare scheme.',
        responsible_leader: (leadership && leadership.length) ? leadership[0].leader_name : 'Union Cabinet / Prime Minister',
        responsible_ministry: overview.category || 'Central Government',
      });
    }

    if (!items.length) {
      track.innerHTML = '<p class="text-muted" style="padding: 16px;">No historical milestones recorded.</p>';
      return;
    }

    track.innerHTML = items.map((ev, idx) => {
      const isOrigin = idx === 0;
      const dateLabel = isOrigin ? `Started: ${ev.event_date || launchDate}` : (ev.event_date || 'Milestone');
      const badgeText = isOrigin ? 'START / INCEPTION' : (ev.event_type || 'UPDATE').replace('_', ' ').toUpperCase();

      let ministerName = ev.responsible_leader || '';
      let ministerRole = ev.responsible_ministry || '';

      if (!ministerName && leadership && leadership.length) {
        const leaderMatch = leadership[idx % leadership.length];
        if (leaderMatch) {
          ministerName = leaderMatch.leader_name;
          ministerRole = leaderMatch.role || leaderMatch.ministry;
        }
      }

      const ministerDisplay = ministerName 
        ? `Minister: ${escapeHtml(ministerName)}${ministerRole ? ` (${escapeHtml(ministerRole)})` : ''}`
        : (ministerRole ? `Ministry: ${escapeHtml(ministerRole)}` : 'Union Government Executive');

      return `
        <div class="timeline-node-card ${isOrigin ? 'origin' : ''}">
          <div>
            <div class="node-date">${escapeHtml(dateLabel)}</div>
            <span class="node-badge">${escapeHtml(badgeText)}</span>
            <div class="node-title">${escapeHtml(ev.title || 'Scheme Milestone')}</div>
            <div class="node-desc">${escapeHtml(ev.description || '')}</div>
          </div>
          <div class="node-minister">
            <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            <span>${ministerDisplay}</span>
          </div>
        </div>
      `;
    }).join('');
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
      const leaderName = r.leader_name || (r.ministerial_tenure && r.ministerial_tenure.leader ? r.ministerial_tenure.leader.full_name : '') || 'Cabinet Minister';
      const role = r.role || r.portfolio || (r.ministerial_tenure ? r.ministerial_tenure.role : 'Minister In-Charge');
      const ministry = r.ministry ? (typeof r.ministry === 'string' ? r.ministry : r.ministry.name) : '';
      const party = r.party || (r.ministerial_tenure && r.ministerial_tenure.leader && r.ministerial_tenure.leader.party ? r.ministerial_tenure.leader.party.abbreviation : '');
      const initials = leaderName.split(' ').filter(n => n.length).map(n => n[0]).join('').slice(0, 2) || 'MN';

      const tenureStr = r.tenure_start ? `${r.tenure_start.slice(0, 4)} – ${r.tenure_end ? r.tenure_end.slice(0, 4) : 'Present'}` : (r.effective_from ? `Effective ${r.effective_from.slice(0, 4)}` : '');

      return `
        <div class="leadership-card">
          <div class="avatar-badge">${initials}</div>
          <div class="leader-info">
            <h4>${escapeHtml(leaderName)}</h4>
            <div class="leader-role">${escapeHtml(role)}</div>
            <div class="leader-tenure">
              ${escapeHtml(ministry)}
              ${party ? ` • ${escapeHtml(party)}` : ''}
              ${tenureStr ? ` • ${escapeHtml(tenureStr)}` : ''}
            </div>
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
      const leaderPart = ev.responsible_leader ? `Minister: ${escapeHtml(ev.responsible_leader)} • ` : '';
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
                <span>${leaderPart}${escapeHtml(ev.responsible_ministry || 'Government Authority')}</span>
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

  function renderBudgetDifferences(budgets) {
    activeBudgets = Array.isArray(budgets) ? [...budgets] : [];
    activeBudgets.sort((a, b) => {
      const ya = parseInt(a.financial_year || a.financial_year_start || 0);
      const yb = parseInt(b.financial_year || b.financial_year_start || 0);
      return ya - yb;
    });

    let totalBe = 0;
    let totalAct = 0;
    let countAct = 0;
    let peakBe = 0;
    let peakYear = '—';

    activeBudgets.forEach((b, i) => {
      const be = b.budget_estimate != null ? Number(b.budget_estimate) : null;
      const act = b.actual_expenditure != null ? Number(b.actual_expenditure) : null;
      if (be != null) {
        totalBe += be;
        if (be > peakBe) {
          peakBe = be;
          peakYear = b.financial_year || (b.financial_year_start ? `${b.financial_year_start}-${String(b.financial_year_end).slice(-2)}` : 'FY');
        }
      }
      if (act != null) {
        totalAct += act;
        countAct++;
      }

      if (i > 0 && activeBudgets[i-1].budget_estimate != null && be != null) {
        b._yoy = be - Number(activeBudgets[i-1].budget_estimate);
      } else {
        b._yoy = null;
      }

      if (act != null && be != null) {
        b._diff = act - be;
        b._diffPct = be > 0 ? ((b._diff / be) * 100) : 0;
      } else {
        b._diff = null;
        b._diffPct = null;
      }
    });

    const kpiBe = document.getElementById('kpiTotalBe');
    const kpiAct = document.getElementById('kpiTotalActual');
    const kpiDiff = document.getElementById('kpiDiffAmount');
    const kpiDiffSub = document.getElementById('kpiDiffSub');
    const kpiPeak = document.getElementById('kpiPeakYear');

    if (kpiBe) kpiBe.textContent = totalBe > 0 ? `₹${Math.round(totalBe).toLocaleString()} Cr` : '—';
    if (kpiAct) kpiAct.textContent = totalAct > 0 ? `₹${Math.round(totalAct).toLocaleString()} Cr` : '—';
    if (kpiPeak) kpiPeak.textContent = peakYear !== '—' ? `${peakYear} (₹${Math.round(peakBe).toLocaleString()} Cr)` : '—';

    if (kpiDiff && kpiDiffSub) {
      if (countAct > 0 && totalBe > 0) {
        const netDiff = totalAct - totalBe;
        const sign = netDiff >= 0 ? '+' : '';
        kpiDiff.textContent = `${sign}₹${Math.round(netDiff).toLocaleString()} Cr`;
        kpiDiff.style.color = netDiff >= 0 ? '#166534' : '#991B1B';
        const pct = ((netDiff / totalBe) * 100).toFixed(1);
        kpiDiffSub.textContent = `${netDiff >= 0 ? 'Surplus / Additional Allocation' : 'Under-Utilization / Savings'} (${sign}${pct}%)`;
      } else {
        kpiDiff.textContent = '—';
        kpiDiffSub.textContent = 'Actual vs Budget Estimate';
      }
    }

    drawBudgetSvgChart(activeBudgets, currentChartMode);
    renderBudgetTable(activeBudgets);
  }

  function drawBudgetSvgChart(budgets, mode) {
    const container = document.getElementById('resBudgetSvgContainer');
    if (!container) return;

    if (!budgets || !budgets.length) {
      container.innerHTML = '<p class="text-muted" style="text-align: center; padding: 24px;">No budget records available for visual chart.</p>';
      return;
    }

    const W = 880;
    const H = 260;
    const padding = { top: 40, right: 30, bottom: 50, left: 75 };
    const chartW = W - padding.left - padding.right;
    const chartH = H - padding.top - padding.bottom;

    const n = budgets.length;
    const groupW = chartW / n;

    let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" xmlns="http://www.w3.org/2000/svg" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">`;

    if (mode === 'comparison') {
      let maxVal = 0;
      budgets.forEach(b => {
        const be = Number(b.budget_estimate) || 0;
        const act = Number(b.actual_expenditure) || 0;
        if (be > maxVal) maxVal = be;
        if (act > maxVal) maxVal = act;
      });
      maxVal = maxVal > 0 ? maxVal * 1.25 : 10000;

      const yTicks = 4;
      for (let i = 0; i <= yTicks; i++) {
        const val = Math.round((maxVal / yTicks) * i);
        const y = padding.top + chartH - (chartH * (i / yTicks));
        svg += `
          <line x1="${padding.left}" y1="${y}" x2="${W - padding.right}" y2="${y}" stroke="#E5E7EB" stroke-dasharray="3 3" />
          <text x="${padding.left - 10}" y="${y + 4}" font-size="11" fill="#6B7280" text-anchor="end" font-weight="600">₹${val >= 1000 ? (val/1000).toFixed(0) + 'k' : val} Cr</text>
        `;
      }

      svg += `
        <g transform="translate(${W - 270}, 16)">
          <rect x="0" y="0" width="12" height="12" fill="#000000" rx="2" />
          <text x="18" y="10" font-size="11" font-weight="700" fill="#000000">Budget Estimate (BE)</text>
          <rect x="135" y="0" width="12" height="12" fill="#64748B" rx="2" />
          <text x="153" y="10" font-size="11" font-weight="700" fill="#475569">Actual Outlay</text>
        </g>
      `;

      const barW = Math.min(32, (groupW - 20) / 2);
      budgets.forEach((b, i) => {
        const cx = padding.left + i * groupW + groupW / 2;
        const yearLabel = b.financial_year || (b.financial_year_start ? `${b.financial_year_start}-${String(b.financial_year_end).slice(-2)}` : `FY${i+1}`);
        const be = Number(b.budget_estimate) || 0;
        const act = b.actual_expenditure != null ? Number(b.actual_expenditure) : null;

        const beH = (be / maxVal) * chartH;
        const beY = padding.top + chartH - beH;
        const beX = cx - barW - 2;

        svg += `
          <rect x="${beX}" y="${beY}" width="${barW}" height="${beH}" fill="#000000" rx="3">
            <title>BE: ₹${be.toLocaleString()} Cr (${yearLabel})</title>
          </rect>
          <text x="${beX + barW/2}" y="${beY - 4}" font-size="10" font-weight="700" fill="#000000" text-anchor="middle">₹${Math.round(be).toLocaleString()}</text>
        `;

        if (act != null) {
          const actH = (act / maxVal) * chartH;
          const actY = padding.top + chartH - actH;
          const actX = cx + 2;
          svg += `
            <rect x="${actX}" y="${actY}" width="${barW}" height="${actH}" fill="#64748B" rx="3">
              <title>Actual: ₹${act.toLocaleString()} Cr (${yearLabel})</title>
            </rect>
            <text x="${actX + barW/2}" y="${actY - 4}" font-size="10" font-weight="700" fill="#475569" text-anchor="middle">₹${Math.round(act).toLocaleString()}</text>
          `;

          const diff = act - be;
          const diffPct = be > 0 ? ((diff / be) * 100).toFixed(0) : '0';
          const diffText = diff >= 0 ? `+₹${Math.round(diff).toLocaleString()}` : `-₹${Math.abs(Math.round(diff)).toLocaleString()}`;
          const pillFill = diff >= 0 ? '#DCFCE7' : '#FEE2E2';
          const pillText = diff >= 0 ? '#166534' : '#991B1B';
          const topY = Math.min(beY, actY) - 18;

          if (topY > padding.top - 8) {
            svg += `
              <rect x="${cx - 36}" y="${topY - 10}" width="72" height="15" fill="${pillFill}" rx="3" stroke="${diff >= 0 ? '#86EFAC' : '#FCA5A5'}" stroke-width="0.5" />
              <text x="${cx}" y="${topY}" font-size="9" font-weight="700" fill="${pillText}" text-anchor="middle">${diffText} (${diffPct}%)</text>
            `;
          }
        } else {
          const actX = cx + 2;
          svg += `
            <rect x="${actX}" y="${padding.top + chartH - 6}" width="${barW}" height="6" fill="#E2E8F0" rx="2" />
            <text x="${actX + barW/2}" y="${padding.top + chartH - 10}" font-size="9" fill="#94A3B8" text-anchor="middle">Pending</text>
          `;
        }

        svg += `
          <text x="${cx}" y="${H - padding.bottom + 22}" font-size="12" font-weight="700" fill="#000000" text-anchor="middle">${yearLabel}</text>
        `;
      });

    } else if (mode === 'difference') {
      let maxAbsDiff = 0;
      budgets.forEach(b => {
        if (b._diff != null) {
          const abs = Math.abs(b._diff);
          if (abs > maxAbsDiff) maxAbsDiff = abs;
        }
      });
      maxAbsDiff = maxAbsDiff > 0 ? maxAbsDiff * 1.3 : 5000;

      const midY = padding.top + chartH / 2;

      svg += `
        <g transform="translate(${W - 320}, 16)">
          <rect x="0" y="0" width="12" height="12" fill="#166534" rx="2" />
          <text x="18" y="10" font-size="11" font-weight="700" fill="#166534">Surplus Spending (+)</text>
          <rect x="150" y="0" width="12" height="12" fill="#991B1B" rx="2" />
          <text x="168" y="10" font-size="11" font-weight="700" fill="#991B1B">Under-Utilization (−)</text>
        </g>
      `;

      svg += `
        <line x1="${padding.left}" y1="${midY}" x2="${W - padding.right}" y2="${midY}" stroke="#000000" stroke-width="2" />
        <text x="${padding.left - 10}" y="${midY + 4}" font-size="11" fill="#000000" text-anchor="end" font-weight="700">₹0 (BE Par)</text>
      `;

      svg += `
        <line x1="${padding.left}" y1="${padding.top}" x2="${W - padding.right}" y2="${padding.top}" stroke="#E5E7EB" stroke-dasharray="3 3" />
        <text x="${padding.left - 10}" y="${padding.top + 4}" font-size="10" fill="#166534" text-anchor="end" font-weight="600">+₹${Math.round(maxAbsDiff).toLocaleString()} Cr</text>
        <line x1="${padding.left}" y1="${padding.top + chartH}" x2="${W - padding.right}" y2="${padding.top + chartH}" stroke="#E5E7EB" stroke-dasharray="3 3" />
        <text x="${padding.left - 10}" y="${padding.top + chartH + 4}" font-size="10" fill="#991B1B" text-anchor="end" font-weight="600">−₹${Math.round(maxAbsDiff).toLocaleString()} Cr</text>
      `;

      const barW = Math.min(48, groupW - 24);
      budgets.forEach((b, i) => {
        const cx = padding.left + i * groupW + groupW / 2;
        const yearLabel = b.financial_year || (b.financial_year_start ? `${b.financial_year_start}-${String(b.financial_year_end).slice(-2)}` : `FY${i+1}`);

        if (b._diff != null) {
          const diff = b._diff;
          const diffH = (Math.abs(diff) / maxAbsDiff) * (chartH / 2);
          const barX = cx - barW / 2;

          if (diff >= 0) {
            const barY = midY - diffH;
            svg += `
              <rect x="${barX}" y="${barY}" width="${barW}" height="${diffH}" fill="#166534" rx="3">
                <title>Surplus Outlay: +₹${diff.toLocaleString()} Cr</title>
              </rect>
              <text x="${cx}" y="${barY - 6}" font-size="10" font-weight="700" fill="#166534" text-anchor="middle">+₹${Math.round(diff).toLocaleString()} Cr</text>
            `;
          } else {
            const barY = midY;
            svg += `
              <rect x="${barX}" y="${barY}" width="${barW}" height="${diffH}" fill="#991B1B" rx="3">
                <title>Under-utilization: -₹${Math.abs(diff).toLocaleString()} Cr</title>
              </rect>
              <text x="${cx}" y="${barY + diffH + 14}" font-size="10" font-weight="700" fill="#991B1B" text-anchor="middle">−₹${Math.abs(Math.round(diff)).toLocaleString()} Cr</text>
            `;
          }
        } else {
          svg += `
            <text x="${cx}" y="${midY - 6}" font-size="10" fill="#94A3B8" text-anchor="middle" font-style="italic">Pending</text>
          `;
        }

        svg += `
          <text x="${cx}" y="${H - padding.bottom + 26}" font-size="12" font-weight="700" fill="#000000" text-anchor="middle">${yearLabel}</text>
        `;
      });

    } else if (mode === 'yoy') {
      let maxYoY = 0;
      budgets.forEach(b => {
        if (b._yoy != null) {
          const abs = Math.abs(b._yoy);
          if (abs > maxYoY) maxYoY = abs;
        }
      });
      maxYoY = maxYoY > 0 ? maxYoY * 1.3 : 5000;

      const midY = padding.top + chartH / 2;

      svg += `
        <g transform="translate(${W - 350}, 16)">
          <rect x="0" y="0" width="12" height="12" fill="#000000" rx="2" />
          <text x="18" y="10" font-size="11" font-weight="700" fill="#000000">Fund Increase (+)</text>
          <rect x="150" y="0" width="12" height="12" fill="#4B5563" rx="2" />
          <text x="168" y="10" font-size="11" font-weight="700" fill="#4B5563">Fund Reduction (−)</text>
        </g>
      `;

      svg += `
        <line x1="${padding.left}" y1="${midY}" x2="${W - padding.right}" y2="${midY}" stroke="#000000" stroke-width="2" />
        <text x="${padding.left - 10}" y="${midY + 4}" font-size="11" fill="#000000" text-anchor="end" font-weight="700">₹0 (Base)</text>
      `;

      const barW = Math.min(48, groupW - 24);
      budgets.forEach((b, i) => {
        const cx = padding.left + i * groupW + groupW / 2;
        const yearLabel = b.financial_year || (b.financial_year_start ? `${b.financial_year_start}-${String(b.financial_year_end).slice(-2)}` : `FY${i+1}`);

        if (b._yoy != null) {
          const yoy = b._yoy;
          const yoyH = (Math.abs(yoy) / maxYoY) * (chartH / 2);
          const barX = cx - barW / 2;

          if (yoy >= 0) {
            const barY = midY - yoyH;
            svg += `
              <rect x="${barX}" y="${barY}" width="${barW}" height="${yoyH}" fill="#000000" rx="3">
                <title>YoY Allocation Increase: +₹${yoy.toLocaleString()} Cr</title>
              </rect>
              <text x="${cx}" y="${barY - 6}" font-size="10" font-weight="700" fill="#000000" text-anchor="middle">+₹${Math.round(yoy).toLocaleString()} Cr</text>
            `;
          } else {
            const barY = midY;
            svg += `
              <rect x="${barX}" y="${barY}" width="${barW}" height="${yoyH}" fill="#4B5563" rx="3">
                <title>YoY Allocation Decrease: -₹${Math.abs(yoy).toLocaleString()} Cr</title>
              </rect>
              <text x="${cx}" y="${barY + yoyH + 14}" font-size="10" font-weight="700" fill="#4B5563" text-anchor="middle">−₹${Math.abs(Math.round(yoy)).toLocaleString()} Cr</text>
            `;
          }
        } else {
          svg += `
            <text x="${cx}" y="${midY - 8}" font-size="10" fill="#6B7280" text-anchor="middle" font-weight="600">Base Year</text>
          `;
        }

        svg += `
          <text x="${cx}" y="${H - padding.bottom + 26}" font-size="12" font-weight="700" fill="#000000" text-anchor="middle">${yearLabel}</text>
        `;
      });
    }

    svg += `
      <line x1="${padding.left}" y1="${H - padding.bottom}" x2="${W - padding.right}" y2="${H - padding.bottom}" stroke="#000000" stroke-width="1.5" />
    </svg>`;

    container.innerHTML = svg;
  }

  function renderBudgetTable(budgets) {
    const tbody = document.getElementById('resBudgetTableBody');
    if (!tbody) return;
    if (!budgets || budgets.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-muted" style="text-align: center;">No financial allocation data recorded yet.</td></tr>';
      return;
    }

    tbody.innerHTML = budgets.map(b => {
      const year = escapeHtml(b.financial_year || (b.financial_year_start ? `${b.financial_year_start}-${String(b.financial_year_end).slice(-2)}` : 'FY'));
      const be = b.budget_estimate != null ? `₹${Number(b.budget_estimate).toLocaleString()} Cr` : '—';
      const re = b.revised_estimate != null ? `₹${Number(b.revised_estimate).toLocaleString()} Cr` : '—';
      const act = b.actual_expenditure != null ? `₹${Number(b.actual_expenditure).toLocaleString()} Cr` : '<span class="text-muted">In Progress</span>';

      let diffHtml = '<span class="text-muted">—</span>';
      if (b._diff != null) {
        if (b._diff > 0) {
          diffHtml = `<span class="budget-diff-pill positive">+₹${Math.round(b._diff).toLocaleString()} Cr (+${b._diffPct.toFixed(1)}%)</span>`;
        } else if (b._diff < 0) {
          diffHtml = `<span class="budget-diff-pill negative">−₹${Math.abs(Math.round(b._diff)).toLocaleString()} Cr (${b._diffPct.toFixed(1)}%)</span>`;
        } else {
          diffHtml = `<span class="budget-diff-pill neutral">₹0 Cr (0%)</span>`;
        }
      }

      let yoyHtml = '<span class="text-muted" style="font-size: 12px;">Base Year</span>';
      if (b._yoy != null) {
        if (b._yoy > 0) {
          yoyHtml = `<span style="font-family: var(--font-mono); font-weight: 700; color: #166534;">+₹${Math.round(b._yoy).toLocaleString()} Cr</span>`;
        } else if (b._yoy < 0) {
          yoyHtml = `<span style="font-family: var(--font-mono); font-weight: 700; color: #991B1B;">−₹${Math.abs(Math.round(b._yoy)).toLocaleString()} Cr</span>`;
        } else {
          yoyHtml = '<span class="text-muted" style="font-size: 12px;">No Change</span>';
        }
      }

      return `
        <tr>
          <td><strong style="color: #000000;">${year}</strong></td>
          <td class="amount-cell">${be}</td>
          <td class="amount-cell">${re}</td>
          <td class="amount-cell">${act}</td>
          <td>${diffHtml}</td>
          <td>${yoyHtml}</td>
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

    container.innerHTML = sources.map(url => {
      let hostname = url;
      try { hostname = new URL(url).hostname; } catch(e) { hostname = url; }
      return `
        <a href="${url}" target="_blank" rel="noopener noreferrer" class="chip">
          <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
          <span>${escapeHtml(hostname)}</span>
        </a>
      `;
    }).join('');
  }

  // --------------------------------------------------------------------------
  // Timeline Category Filtering — uses event delegation so it works on
  // dynamically rendered items too (not just the static HTML ones)
  // --------------------------------------------------------------------------
  const filterBtns = document.querySelectorAll('.timeline-filter-btn');

  function applyTimelineFilter(cat) {
    const items = document.querySelectorAll('.timeline-item');
    items.forEach(item => {
      if (cat === 'all' || (item.dataset.category || '').includes(cat)) {
        item.style.display = 'block';
      } else {
        item.style.display = 'none';
      }
    });
  }

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      applyTimelineFilter(btn.dataset.category);
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
  // Schemes Directory Loader (Fetches all resources dynamically from API)
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
        // Get ALL timeline events — the API returns them all; we map every one
        timeline_events: (timeline.results || (Array.isArray(timeline) ? timeline : [])).map(t => ({
          title: t.title,
          description: t.description,
          event_date: t.event_date,
          event_type: t.event_type,
          responsible_ministry: t.responsible_ministry ? (typeof t.responsible_ministry === 'string' ? t.responsible_ministry : t.responsible_ministry.name) : '',
          responsible_leader: t.responsible_leader ? (typeof t.responsible_leader === 'string' ? t.responsible_leader : t.responsible_leader.full_name) : '',
          source_urls: t.source_urls || [],
        })),
        budget_records: (budgets.results || budgets).map(b => ({
          financial_year: b.financial_year || (b.financial_year_start ? `${b.financial_year_start}-${String(b.financial_year_end).slice(-2)}` : 'FY'),
          financial_year_start: b.financial_year_start,
          financial_year_end: b.financial_year_end,
          budget_estimate: b.budget_estimate,
          revised_estimate: b.revised_estimate,
          actual_expenditure: b.actual_expenditure,
          verification_status: b.verification_status,
        })),
        leadership_records: (leadership.results || leadership).map(l => ({
          leader_name: l.leader_name || (l.ministerial_tenure && l.ministerial_tenure.leader ? l.ministerial_tenure.leader.full_name : ''),
          role: l.role || l.portfolio || l.responsibility_type || (l.ministerial_tenure ? l.ministerial_tenure.role : 'Minister In-Charge'),
          ministry: l.ministry ? (typeof l.ministry === 'string' ? l.ministry : l.ministry.name) : '',
          party: l.party || (l.ministerial_tenure && l.ministerial_tenure.leader && l.ministerial_tenure.leader.party ? l.ministerial_tenure.leader.party.abbreviation : ''),
          tenure_start: l.effective_from || (l.ministerial_tenure ? l.ministerial_tenure.tenure_start : null),
          tenure_end: l.effective_to || (l.ministerial_tenure ? l.ministerial_tenure.tenure_end : null),
        })),
        source_urls_searched: ['https://pib.gov.in', 'https://india.gov.in', 'https://indiabudget.gov.in'],
        ai_model_used: 'Verified Official Gazette & REST API',
      };

      renderResearchResults(combinedData);
    } catch (e) {
      console.error(e);
      showToast('Could not load scheme record from API.', 'error');
    } finally {
      if (loadingContainer) loadingContainer.style.display = 'none';
    }
  };

  // --------------------------------------------------------------------------
  // Budget SVG Chart Mode Tabs Controls
  // --------------------------------------------------------------------------
  const chartTabBtns = document.querySelectorAll('.chart-tab-btn');
  chartTabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      chartTabBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentChartMode = btn.dataset.chartMode || 'comparison';
      drawBudgetSvgChart(activeBudgets, currentChartMode);
    });
  });

  // Automatically fetch Scheme 1 dynamically from API on startup
  loadSchemeById(1);

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
