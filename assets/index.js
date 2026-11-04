// Network Dr "All videos": filter by text and series.
(function () {
  var q = document.getElementById("q"), sel = document.getElementById("series");
  var grid = document.getElementById("grid"), none = document.getElementById("no-results"), count = document.getElementById("count");
  if (!grid) return;
  var cards = Array.prototype.slice.call(grid.children);
  try { var saved = sessionStorage.getItem("ndr-series"); if (sel && saved) sel.value = saved; } catch (e) {}
  if (sel && location.hash.length > 1) sel.value = decodeURIComponent(location.hash.slice(1));
  function run() {
    var terms = (q ? q.value : "").toLowerCase().trim().split(/\s+/).filter(Boolean);
    var s = sel ? sel.value : "", shown = 0;
    cards.forEach(function (c) {
      var hit = (!s || c.dataset.series === s) && terms.every(function (t) { return c.dataset.q.indexOf(t) !== -1; });
      c.hidden = !hit; if (hit) shown++;
    });
    if (none) none.hidden = shown !== 0;
    if (count) count.textContent = shown === cards.length ? "" : "Showing " + shown + " of " + cards.length;
    try { sessionStorage.setItem("ndr-series", s); } catch (e) {}
  }
  if (q) q.addEventListener("input", run);
  if (sel) sel.addEventListener("change", run);
  run();
})();
