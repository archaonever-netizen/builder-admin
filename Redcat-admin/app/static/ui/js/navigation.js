document.addEventListener('DOMContentLoaded', function () {
  var railLinks = document.querySelectorAll('#navigation-rail .nav-item');
  if (!railLinks.length) {
    return;
  }

  var currentPath = window.location.pathname.replace(/\/+$/, '');
  if (currentPath === '') {
    currentPath = '/';
  }

  function normalizePath(value) {
    return value.replace(/\/+$/, '') || '/';
  }

  var matched = false;
  railLinks.forEach(function (link) {
    var href = normalizePath(link.getAttribute('href') || '');
    if (href !== '/' && currentPath.indexOf(href) === 0) {
      link.classList.add('active');
      matched = true;
    }
  });

  if (!matched) {
    railLinks.forEach(function (link) {
      var href = normalizePath(link.getAttribute('href') || '');
      if (href === '/') {
        link.classList.add('active');
      }
    });
  }
});
