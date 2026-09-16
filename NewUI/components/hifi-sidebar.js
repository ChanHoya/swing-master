// SwingMaster Hi-Fi · 공통 사이드바 렌더러
// 사용: <aside class="sidebar" data-hifi-sidebar="drill"></aside>
// 그리고 페이지 끝에 <script src="components/hifi-sidebar.js"></script>

(function () {
  const ICONS = {
    home: '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    capture: '<polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2"/>',
    report: '<path d="M9 11H5a2 2 0 0 0-2 2v7h6V11zM15 5h-6v15h6V5zM21 8h-4v12h4V8z"/>',
    progress: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    drill: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',
    chat: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    compare: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  };

  const NAV = [
    { section: 'Practice', items: [
      { key: 'home',     label: '대시보드',         href: 'index.html',    icon: 'home' },
      { key: 'capture',  label: '촬영 / 업로드',    href: 'capture.html',  icon: 'capture' },
      { key: 'report',   label: '분석 리포트',      href: 'detail.html',   icon: 'report' },
      { key: 'progress', label: '진행 기록',        href: 'progress.html', icon: 'progress' },
      { key: 'drill',    label: '드릴 라이브러리',  href: 'drill.html',    icon: 'drill' },
    ]},
    { section: 'Coach', items: [
      { key: 'chat',     label: 'AI 코치 채팅',     href: 'coach.html',    icon: 'chat' },
      { key: 'compare',  label: '프로 비교',        href: 'compare.html',  icon: 'compare' },
    ]},
  ];

  function svgIcon(key) {
    return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${ICONS[key] || ''}</svg>`;
  }

  function render(active) {
    let html = `
      <div class="brand">
        <div class="brand-mark">S</div>
        <div>
          <div class="brand-name">Swing<span class="em">Master</span></div>
          <div style="font-family:'JetBrains Mono',monospace; font-size:9px; color:var(--text-4); letter-spacing:0.08em; margin-top:2px">v2.0 BETA</div>
        </div>
      </div>
    `;
    NAV.forEach(group => {
      html += `<div class="nav-label">${group.section}</div>`;
      group.items.forEach(it => {
        const cls = 'nav-item' + (it.key === active ? ' active' : '');
        html += `<a class="${cls}" href="${it.href}">${svgIcon(it.icon)}${it.label}</a>`;
      });
    });
    html += `
      <div style="flex:1"></div>
      <div class="goal-card">
        <div class="goal-label">금주 목표</div>
        <div class="goal-title">템포 B → A</div>
        <div class="goal-bar"><div class="goal-bar-fill" style="width:65%"></div></div>
        <div class="goal-meta"><span>3 / 5 세션</span><span style="color:var(--accent)">65%</span></div>
      </div>
    `;
    return html;
  }

  function init() {
    document.querySelectorAll('[data-hifi-sidebar]').forEach(el => {
      const active = el.getAttribute('data-hifi-sidebar');
      el.innerHTML = render(active);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
