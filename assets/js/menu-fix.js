/* Menu mobile : se referme quand on clique un lien, en dehors du menu, ou sur Echap. */
(function () {
  var button = document.querySelector('.menu-toggle');
  var menu = document.querySelector('.main-menu');
  if (!button || !menu) return;
  function close() {
    menu.classList.remove('is-open');
    button.setAttribute('aria-expanded', 'false');
  }
  menu.addEventListener('click', function (e) {
    if (e.target.closest('a')) close();
  });
  document.addEventListener('click', function (e) {
    if (menu.classList.contains('is-open') && !menu.contains(e.target) && !button.contains(e.target)) close();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') close();
  });
  window.addEventListener('hashchange', close);
})();
