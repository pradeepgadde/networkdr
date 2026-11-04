// Network Dr episode page: seek from transcript, follow along, copy transcript.
(function () {
  var frame = document.getElementById("yt");
  var tx = document.getElementById("tx");
  var follow = document.getElementById("follow");
  var copyBtn = document.getElementById("copy-tx");
  if (!frame || !tx) return;

  var spans = Array.prototype.slice.call(tx.querySelectorAll("span[data-t]"));
  var times = spans.map(function (s) { return +s.dataset.t; });
  var player = null, current = -1, userScrollUntil = 0;

  function onReady() {}
  function setActive(sec) {
    var i = -1, lo = 0, hi = times.length - 1;
    while (lo <= hi) { var mid = (lo + hi) >> 1; if (times[mid] <= sec) { i = mid; lo = mid + 1; } else hi = mid - 1; }
    if (i === current) return;
    if (current >= 0) spans[current].classList.remove("on");
    current = i;
    if (i < 0) return;
    spans[i].classList.add("on");
    if (follow && follow.checked && Date.now() > userScrollUntil) {
      var box = tx.scrollHeight > tx.clientHeight + 4 ? tx : null;
      var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (box) {
        var top = spans[i].offsetTop - box.offsetTop - box.clientHeight / 3;
        box.scrollTo({ top: top, behavior: reduce ? "auto" : "smooth" });
      }
    }
  }

  tx.addEventListener("wheel", function () { userScrollUntil = Date.now() + 4000; }, { passive: true });
  tx.addEventListener("touchmove", function () { userScrollUntil = Date.now() + 4000; }, { passive: true });

  window.onYouTubeIframeAPIReady = function () {
    player = new YT.Player("yt", { events: { onReady: onReady } });
    setInterval(function () {
      if (player && player.getCurrentTime && player.getPlayerState && player.getPlayerState() === 1) setActive(player.getCurrentTime());
    }, 500);
  };
  var s = document.createElement("script");
  s.src = "https://www.youtube.com/iframe_api";
  document.head.appendChild(s);

  tx.addEventListener("click", function (e) {
    var a = e.target.closest("a[data-seek]");
    var span = e.target.closest("span[data-t]");
    var t = a ? +a.dataset.seek : span ? +span.dataset.t : null;
    if (t === null || !player || !player.seekTo) return;
    e.preventDefault();
    player.seekTo(t, true);
    player.playVideo();
    userScrollUntil = 0;
    setActive(t);
    if (window.innerWidth < 1000) frame.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  if (copyBtn) copyBtn.addEventListener("click", function () {
    var text = Array.prototype.map.call(tx.querySelectorAll("p"), function (p) {
      var stamp = p.querySelector(".stamp");
      var body = Array.prototype.map.call(p.querySelectorAll("span"), function (x) { return x.textContent; }).join(" ");
      return (stamp ? "[" + stamp.textContent + "] " : "") + body;
    }).join("\n\n");
    navigator.clipboard.writeText(text).then(function () {
      copyBtn.textContent = "Copied";
      setTimeout(function () { copyBtn.textContent = "Copy text"; }, 2000);
    }, function () { copyBtn.textContent = "Copy failed"; });
  });
})();
