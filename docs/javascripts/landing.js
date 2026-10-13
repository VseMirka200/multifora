(function() {
  "use strict";
  var root = document.documentElement, key = "multifora-theme", button = document.getElementById("theme");
  try { var saved = localStorage.getItem(key); if(saved === "dark" || saved === "light") root.dataset.theme = saved; } catch(_) {}
  if(!root.dataset.theme) root.dataset.theme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  if(button) {
    button.setAttribute("aria-pressed", String(root.dataset.theme === "dark"));
    button.addEventListener("click", function() {
      root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
      button.setAttribute("aria-pressed", String(root.dataset.theme === "dark"));
      try { localStorage.setItem(key,root.dataset.theme); } catch(_) {}
    });
  }
}());