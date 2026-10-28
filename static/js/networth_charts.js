(function () {
  var dataElement = document.getElementById('chart-data');
  if (!dataElement || typeof Chart === 'undefined') { return; }
  var data = JSON.parse(dataElement.textContent);
  var style = getComputedStyle(document.body);
  Chart.defaults.color = style.getPropertyValue('--bs-body-color') || '#333';
  Chart.defaults.borderColor = style.getPropertyValue('--bs-border-color') || '#ddd';
  var palette = ['#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f', '#edc948', '#b07aa1', '#ff9da7', '#9c755f', '#bab0ac'];
  function money(value) {
    return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(value);
  }

  var trendCanvas = document.getElementById('chart-networth');
  if (trendCanvas && data.trend.values.length) {
    new Chart(trendCanvas, {
      type: 'line',
      data: { labels: data.trend.labels, datasets: [{ label: 'Net worth', data: data.trend.values, borderColor: palette[4], backgroundColor: 'rgba(89,161,79,0.15)', fill: true, tension: 0.25 }] },
      options: {
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: function (c) { return 'Rs ' + money(c.parsed.y); } } } },
        scales: { y: { ticks: { callback: function (v) { return money(v); } } } }
      }
    });
  }

  var assetsCanvas = document.getElementById('chart-assets');
  if (assetsCanvas && data.assets.values.length) {
    new Chart(assetsCanvas, {
      type: 'doughnut',
      data: { labels: data.assets.labels, datasets: [{ data: data.assets.values, backgroundColor: palette }] },
      options: {
        plugins: { tooltip: { callbacks: { label: function (c) { return c.label + ': Rs ' + money(c.parsed); } } } }
      }
    });
  }
})();
