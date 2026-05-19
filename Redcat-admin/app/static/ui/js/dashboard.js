document.addEventListener('DOMContentLoaded', function () {
  var overlay = document.getElementById('side-panel-overlay');
  var panel = document.getElementById('side-panel');
  var closeButton = document.getElementById('side-panel-close');
  var searchInput = document.getElementById('adminSearchInput');
  var streamItems = Array.from(document.querySelectorAll('.stream-item'));

  function openPanel(developerData) {
    panel.querySelector('.panel-title').textContent = developerData.name;
    panel.querySelector('.panel-status').textContent = developerData.statusText;
    panel.querySelector('.panel-complexes').textContent = developerData.complexes || 'Нет объектов';
    panel.querySelector('.panel-regions').textContent = developerData.regions || 'Регион не задан';
    panel.querySelector('.panel-contacts').textContent = developerData.contactsCount + ' контактов';
    panel.querySelector('.panel-created').textContent = developerData.created;
    panel.querySelector('.panel-full-link').setAttribute('href', '/admin/client/' + developerData.id);

    overlay.classList.add('open');
    panel.classList.add('open');
  }

  function closePanel() {
    overlay.classList.remove('open');
    panel.classList.remove('open');
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
