(function () {
  var sidebar = document.getElementById('sarthi-sidebar');
  var backdrop = document.getElementById('sarthi-backdrop');
  var toggle = document.getElementById('sarthi-sidebar-toggle');
  function closeSidebar() {
    if (sidebar) { sidebar.classList.remove('show'); }
    if (backdrop) { backdrop.classList.remove('show'); }
  }
  if (toggle) {
    toggle.addEventListener('click', function () {
      sidebar.classList.toggle('show');
      backdrop.classList.toggle('show');
    });
  }
  if (backdrop) { backdrop.addEventListener('click', closeSidebar); }

  var themeButton = document.getElementById('sarthi-theme-toggle');
  var themeIcon = document.getElementById('sarthi-theme-icon');
  function showThemeIcon() {
    if (!themeIcon) { return; }
    var dark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
    themeIcon.className = dark ? 'bi bi-sun' : 'bi bi-moon-stars';
  }
  if (themeButton) {
    themeButton.addEventListener('click', function () {
      var next = document.documentElement.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-bs-theme', next);
      try { localStorage.setItem('sarthi-theme', next); } catch (e) {}
      showThemeIcon();
    });
  }
  showThemeIcon();
})();
