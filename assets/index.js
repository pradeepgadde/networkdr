// Network Dr index: filter episodes by title.
(function () {
  var q = document.getElementById("q"), grid = document.getElementById("grid"), none = document.getElementById("no-results");
  if (!q || !grid) return;
  var cards = Array.prototype.slice.call(grid.children);
  q.addEventListener("input", function () {
    var terms = q.value.toLowerCase().trim().split(/\s+/).filter(Boolean), shown = 0;
    cards.forEach(function (c) {
      var hit = terms.every(function (t) { return c.dataset.q.indexOf(t) !== -1; });
      c.hidden = !hit; if (hit) shown++;
    });
    none.hidden = shown !== 0;
  });
})();
