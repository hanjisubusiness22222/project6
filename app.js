/**
 * AI Public Tender Monitor - Client Logic
 * Team Member 3 (Frontend & DevOps) Implementation
 */

// Global State
let allProjects = [];
let filteredProjects = [];
let activeCategory = 'ALL';
let currentSort = 'closing';
let searchQuery = '';

let categoryChartInstance = null;
let budgetTopChartInstance = null;

// Helper: Format Korean Currency
function formatBudget(amount) {
  if (!amount || isNaN(amount)) return '-';
  const eok = Math.floor(amount / 100000000);
  const remainder = amount % 100000000;
  const man = Math.floor(remainder / 10000);

  if (eok > 0 && man > 0) {
    return `${eok.toLocaleString()}억 ${man.toLocaleString()}만원`;
  } else if (eok > 0) {
    return `${eok.toLocaleString()}억원`;
  } else if (man > 0) {
    return `${man.toLocaleString()}만원`;
  }
  return `${amount.toLocaleString()}원`;
}

// Helper: Calculate D-Day
function calculateDDay(closeDateStr) {
  if (!closeDateStr) return { text: '-', isUrgent: false };
  // Expected format: "2026-10-23 11:00" or ISO
  const targetDate = new Date(closeDateStr.replace(' ', 'T'));
  const now = new Date();
  const diffTime = targetDate - now;
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

  if (diffTime < 0) {
    return { text: '마감됨', isUrgent: false };
  } else if (diffDays === 0) {
    return { text: 'D-Day', isUrgent: true };
  } else if (diffDays <= 7) {
    return { text: `D-${diffDays}`, isUrgent: true };
  } else {
    return { text: `D-${diffDays}`, isUrgent: false };
  }
}

// Helper: Get Category Class
function getCategoryClass(category) {
  switch (category) {
    case '생성형AI/LLM': return 'cat-llm';
    case '지능형CCTV/비전': return 'cat-vision';
    case '데이터구축/학습': return 'cat-data';
    case 'AI챗봇/상담': return 'cat-bot';
    case '빅데이터/예측': return 'cat-pred';
    default: return 'cat-llm';
  }
}

// Initialize Application
document.addEventListener('DOMContentLoaded', async () => {
  setupEventListeners();
  await loadData();
});

// Setup DOM Event Listeners
function setupEventListeners() {
  const searchInput = document.getElementById('searchInput');
  const clearSearchBtn = document.getElementById('clearSearchBtn');
  const sortSelect = document.getElementById('sortSelect');
  const categoryPills = document.getElementById('categoryPills');
  const resetFilterBtn = document.getElementById('resetFilterBtn');

  // Search input with instant reaction
  searchInput.addEventListener('input', (e) => {
    searchQuery = e.target.value.trim().toLowerCase();
    clearSearchBtn.style.display = searchQuery ? 'block' : 'none';
    applyFiltersAndRender();
  });

  clearSearchBtn.addEventListener('click', () => {
    searchInput.value = '';
    searchQuery = '';
    clearSearchBtn.style.display = 'none';
    searchInput.focus();
    applyFiltersAndRender();
  });

  // Sort change
  sortSelect.addEventListener('change', (e) => {
    currentSort = e.target.value;
    applyFiltersAndRender();
  });

  // Category Pills
  categoryPills.addEventListener('click', (e) => {
    const btn = e.target.closest('.pill-btn');
    if (!btn) return;
    
    document.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeCategory = btn.dataset.category;
    applyFiltersAndRender();
  });

  // Reset Filter Button
  resetFilterBtn.addEventListener('click', () => {
    searchInput.value = '';
    searchQuery = '';
    clearSearchBtn.style.display = 'none';
    activeCategory = 'ALL';
    document.querySelectorAll('.pill-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.category === 'ALL');
    });
    currentSort = 'closing';
    sortSelect.value = 'closing';
    applyFiltersAndRender();
  });

  // Modal close handlers
  document.getElementById('modalCloseBtn').addEventListener('click', closeModal);
  document.getElementById('modalSecondaryClose').addEventListener('click', closeModal);
  document.getElementById('projectModal').addEventListener('click', (e) => {
    if (e.target.id === 'projectModal') closeModal();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
  });
}

// Fetch JSON Data
async function loadData() {
  try {
    const res = await fetch('data/ai_projects.json');
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();

    allProjects = data.projects || [];
    renderKPIs(data.summary, data.updated_at);
    initCharts(data);
    applyFiltersAndRender();

  } catch (err) {
    console.warn('Failed to load local data/ai_projects.json, using fallback mock.', err);
    // Display error notification in status pill
    document.getElementById('lastUpdatedText').textContent = '샘플 데이터 로드 완료';
  }
}

// Render Top KPI Cards
function renderKPIs(summary, updatedAt) {
  if (updatedAt) {
    const dateObj = new Date(updatedAt);
    const dateStr = dateObj.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    document.getElementById('lastUpdatedText').textContent = `최근 동기화: ${dateStr}`;
  }

  if (!summary) return;

  document.getElementById('valTotalCount').textContent = `${summary.total_count || allProjects.length}건`;
  document.getElementById('valTotalBudget').textContent = formatBudget(summary.total_budget);
  document.getElementById('valAvgBudget').textContent = formatBudget(summary.avg_budget);
  document.getElementById('valClosingSoon').textContent = `${summary.closing_soon_count || 0}건`;
}

// Initialize Visual Charts
function initCharts(data) {
  const categoryCounts = data.summary?.category_counts || {};
  const categories = Object.keys(categoryCounts);
  const counts = Object.values(categoryCounts);

  // 1. Doughnut Chart: Categories
  const ctxCat = document.getElementById('categoryChart').getContext('2d');
  if (categoryChartInstance) categoryChartInstance.destroy();

  categoryChartInstance = new Chart(ctxCat, {
    type: 'doughnut',
    data: {
      labels: categories,
      datasets: [{
        data: counts,
        backgroundColor: [
          '#6366f1',
          '#06b6d4',
          '#10b981',
          '#f59e0b',
          '#f43f5e'
        ],
        borderColor: '#111625',
        borderWidth: 3,
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: {
            color: '#94a3b8',
            font: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: '500' },
            boxWidth: 12,
            padding: 10
          }
        },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.label}: ${ctx.raw}건 (${Math.round((ctx.raw / data.summary.total_count) * 100)}%)`
          }
        }
      },
      cutout: '68%'
    }
  });

  // 2. Bar Chart: Top 5 Budgets
  const sortedByBudget = [...allProjects].sort((a, b) => b.budget - a.budget).slice(0, 5);
  const topTitles = sortedByBudget.map(p => p.title.length > 15 ? p.title.slice(0, 15) + '...' : p.title);
  const topBudgets = sortedByBudget.map(p => Math.round(p.budget / 100000000)); // 억원 단위

  const ctxBudget = document.getElementById('budgetTopChart').getContext('2d');
  if (budgetTopChartInstance) budgetTopChartInstance.destroy();

  budgetTopChartInstance = new Chart(ctxBudget, {
    type: 'bar',
    data: {
      labels: topTitles,
      datasets: [{
        label: '사업 예산 (억원)',
        data: topBudgets,
        backgroundColor: 'rgba(99, 102, 241, 0.75)',
        hoverBackgroundColor: '#818cf8',
        borderRadius: 6,
        borderSkipped: false
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      scales: {
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: '#64748b', callback: (v) => `${v}억` }
        },
        y: {
          grid: { display: false },
          ticks: { color: '#cbd5e1', font: { size: 11 } }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` 사업비: ${ctx.raw}억원 (${formatBudget(sortedByBudget[ctx.dataIndex].budget)})`
          }
        }
      }
    }
  });
}

// Filter, Sort and Render Project Cards
function applyFiltersAndRender() {
  filteredProjects = allProjects.filter(p => {
    // Category Filter
    if (activeCategory !== 'ALL' && p.category !== activeCategory) {
      return false;
    }
    // Search Query (title, agency, description)
    if (searchQuery) {
      const matchTitle = p.title.toLowerCase().includes(searchQuery);
      const matchAgency = p.agency.toLowerCase().includes(searchQuery);
      const matchDesc = (p.description || '').toLowerCase().includes(searchQuery);
      if (!matchTitle && !matchAgency && !matchDesc) return false;
    }
    return true;
  });

  // Sorting
  filteredProjects.sort((a, b) => {
    if (currentSort === 'closing') {
      return new Date(a.close_date.replace(' ', 'T')) - new Date(b.close_date.replace(' ', 'T'));
    } else if (currentSort === 'budgetDesc') {
      return b.budget - a.budget;
    } else if (currentSort === 'budgetAsc') {
      return a.budget - b.budget;
    } else if (currentSort === 'newest') {
      return new Date(b.notice_date) - new Date(a.notice_date);
    }
    return 0;
  });

  renderProjectGrid();
}

// Render HTML Project Grid
function renderProjectGrid() {
  const grid = document.getElementById('projectsGrid');
  const emptyState = document.getElementById('emptyState');
  const countTag = document.getElementById('filteredCount');

  countTag.textContent = `${filteredProjects.length}건`;

  if (filteredProjects.length === 0) {
    grid.innerHTML = '';
    emptyState.style.display = 'flex';
    return;
  }

  emptyState.style.display = 'none';

  grid.innerHTML = filteredProjects.map(p => {
    const dday = calculateDDay(p.close_date);
    const catClass = getCategoryClass(p.category);
    const ddayClass = dday.isUrgent ? 'dday-urgent' : 'dday-normal';

    return `
      <article class="tender-card" onclick="openModal('${p.id}')" tabindex="0" role="button" aria-label="${p.title} 상세보기">
        <div>
          <div class="tender-header">
            <span class="card-category-badge ${catClass}">${p.category}</span>
            <span class="card-dday-badge ${ddayClass}">${dday.text}</span>
          </div>

          <h4 class="tender-title" title="${p.title}">${p.title}</h4>

          <div class="tender-agency">
            <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path>
            </svg>
            <span>${p.agency}</span>
          </div>
        </div>

        <div class="tender-meta">
          <div class="tender-budget-box">
            <span class="meta-sub-label">추정 사업비</span>
            <span class="tender-budget">${formatBudget(p.budget)}</span>
          </div>
          <div class="tender-closing-box">
            <span class="meta-sub-label">입찰 마감</span>
            <span class="tender-closing-date">${p.close_date}</span>
          </div>
        </div>
      </article>
    `;
  }).join('');
}

// Modal View Handler
window.openModal = function(id) {
  const project = allProjects.find(p => p.id === id);
  if (!project) return;

  document.getElementById('modalCategory').textContent = project.category;
  document.getElementById('modalTitle').textContent = project.title;
  document.getElementById('modalBudget').textContent = formatBudget(project.budget);
  document.getElementById('modalAgency').textContent = project.agency;
  document.getElementById('modalCloseDate').textContent = project.close_date;
  document.getElementById('modalId').textContent = project.id;
  document.getElementById('modalContractMethod').textContent = project.contract_method || '협상에의한계약';
  document.getElementById('modalNoticeDate').textContent = project.notice_date;
  document.getElementById('modalDescription').textContent = project.description || '상세 과업지시서 및 제안요청서(RFP)는 나라장터 공고 페이지에서 내려받으실 수 있습니다.';
  
  const g2bBtn = document.getElementById('modalG2bLink');
  g2bBtn.href = project.link || 'https://www.g2b.go.kr';

  const modal = document.getElementById('projectModal');
  modal.classList.add('active');
  document.body.style.overflow = 'hidden';
};

function closeModal() {
  const modal = document.getElementById('projectModal');
  modal.classList.remove('active');
  document.body.style.overflow = '';
}
