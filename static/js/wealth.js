(function () {
  var button = document.getElementById('reveal-button');
  if (!button) { return; }
  var box = document.getElementById('reveal-box');
  var timer = null;
  function hide() {
    box.classList.add('d-none');
    document.getElementById('reveal-account').textContent = '';
    document.getElementById('reveal-customer').textContent = '';
    button.disabled = false;
  }
  button.addEventListener('click', function () {
    button.disabled = true;
    fetch(button.dataset.url, {
      method: 'POST',
      headers: { 'X-CSRFToken': button.dataset.csrf },
      credentials: 'same-origin'
    })
      .then(function (response) {
        if (!response.ok) { throw new Error('failed'); }
        return response.json();
      })
      .then(function (data) {
        document.getElementById('reveal-account').textContent = data.account_number || '-';
        document.getElementById('reveal-customer').textContent = data.customer_id || '-';
        box.classList.remove('d-none');
        if (timer) { clearTimeout(timer); }
        timer = setTimeout(hide, 30000);
      })
      .catch(function () {
        button.disabled = false;
        alert('Could not reveal the details. Please sign in again and retry.');
      });
  });
})();
