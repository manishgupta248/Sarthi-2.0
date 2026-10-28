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

  var summaryCanvas = document.getElementById('chart-summary');
  if (summaryCanvas && data.labels && data.labels.length) {
    new Chart(summaryCanvas, {
      type: 'bar',
      data: {
        labels: data.labels,
        datasets: [
          { label: 'Income', data: data.income, backgroundColor: '#59a14f' },
          { label: 'Expenses', data: data.expenses, backgroundColor: '#e15759' },
          { label: 'Invested', data: data.invested, backgroundColor: '#4e79a7' }
        ]
      },
      options: {
        plugins: { tooltip: { callbacks: { label: function (c) { return c.dataset.label + ': Rs ' + money(c.parsed.y); } } } },
        scales: { y: { ticks: { callback: function (v) { return money(v); } } } }
      }
    });
  }

  var categoryCanvas = document.getElementById('chart-categories');
  if (categoryCanvas && data.values && data.values.length) {
    new Chart(categoryCanvas, {
      type: 'doughnut',
      data: { labels: data.labels, datasets: [{ data: data.values, backgroundColor: palette }] },
      options: {
        plugins: { tooltip: { callbacks: { label: function (c) { return c.label + ': Rs ' + money(c.parsed); } } } }
      }
    });
  }
})();
