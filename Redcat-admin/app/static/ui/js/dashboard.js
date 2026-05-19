document.addEventListener('DOMContentLoaded', function () {
  var overlay = document.getElementById('side-panel-overlay');
  var panel = document.getElementById('side-panel');
  var closeButton = document.getElementById('side-panel-close');
  var searchInput = document.getElementById('adminSearchInput');
  var streamItems = Array.from(document.querySelectorAll('.stream-item'));

  function openPanel(developerData) {
    document.getElementById('panel-title').textContent = developerData.name;
    document.getElementById('panel-status').textContent = developerData.statusText;
    document.getElementById('panel-complexes').textContent = developerData.complexes || 'Нет объектов';
    document.getElementById('panel-regions').textContent = developerData.regions || 'Регион не задан';
    document.getElementById('panel-contacts').textContent = developerData.contactsCount + ' контактов';
    document.getElementById('panel-created').textContent = developerData.created;
    document.getElementById('panel-full-link').setAttribute('href', '/admin/client/' + developerData.id);
    document.getElementById('side-panel').setAttribute('aria-hidden', 'false');

    overlay.classList.add('open');
    panel.classList.add('open');
  }

  function closePanel() {
    overlay.classList.remove('open');
    panel.classList.remove('open');
    document.getElementById('side-panel').setAttribute('aria-hidden', 'true');
  }

  function parseDeveloperData(item) {
    return {
      id: item.dataset.devId,
      name: item.dataset.devName,
      created: item.dataset.devCreated,
      regions: item.dataset.devRegions,
      complexes: item.dataset.devComplexes,
      commission: item.dataset.devCommission,
      statusText: item.dataset.devStatusText,
      contactsCount: item.dataset.devContactsCount || '0'
    };
  }

  streamItems.forEach(function (item) {
    item.addEventListener('click', function (event) {
      if (event.target.closest('.stream-actions')) {
        return;
      }
      openPanel(parseDeveloperData(item));
    });
  });

  closeButton.addEventListener('click', closePanel);
  overlay.addEventListener('click', closePanel);

  if (searchInput) {
    searchInput.addEventListener('input', function () {
      var filter = searchInput.value.trim().toLowerCase();
      streamItems.forEach(function (item) {
        var title = item.querySelector('.stream-title').textContent.toLowerCase();
        var regions = item.querySelector('.stream-subtitle').textContent.toLowerCase();
        var matches = title.includes(filter) || regions.includes(filter);
        item.style.display = matches ? '' : 'none';
      });
    });
  }
});
