/*
 * Adds a "Copy" button to every code block. Progressive enhancement: without JavaScript the
 * blocks render exactly as before.
 *
 * Pandoc wraps highlighted blocks in div.sourceCode and leaves plain fences as a bare <pre>,
 * so the button is attached to the wrapper when there is one and to a new wrapper otherwise.
 * The text is read from the DOM at click time, so anything a script rewrote after page load
 * (for example Cloudflare's email decoding) is copied as the reader sees it.
 */
(function () {
  "use strict";

  if (!navigator.clipboard || !navigator.clipboard.writeText) {
    return;
  }

  var RESET_MS = 1800;

  function containerFor(pre) {
    var parent = pre.parentElement;
    if (parent && parent.classList.contains("sourceCode")) {
      return parent;
    }
    var wrapper = document.createElement("div");
    wrapper.className = "code-block";
    parent.insertBefore(wrapper, pre);
    wrapper.appendChild(pre);
    return wrapper;
  }

  function addButton(pre) {
    var code = pre.querySelector("code") || pre;
    var container = containerFor(pre);
    container.classList.add("has-copy");

    var button = document.createElement("button");
    button.type = "button";
    button.className = "copy-code";
    button.textContent = "Copy";
    button.setAttribute("aria-label", "Copy code to clipboard");

    var status = document.createElement("span");
    status.className = "copy-code-status";
    status.setAttribute("role", "status");

    var timer;
    function show(label, state) {
      button.textContent = label;
      button.dataset.state = state;
      status.textContent = state === "done" ? "Copied to clipboard" : "Copy failed";
      clearTimeout(timer);
      timer = setTimeout(function () {
        button.textContent = "Copy";
        delete button.dataset.state;
        status.textContent = "";
      }, RESET_MS);
    }

    button.addEventListener("click", function () {
      var text = code.textContent.replace(/\n$/, "");
      navigator.clipboard.writeText(text).then(
        function () {
          show("Copied", "done");
        },
        function () {
          show("Copy failed", "error");
        },
      );
    });

    container.appendChild(button);
    container.appendChild(status);
  }

  document.querySelectorAll("pre").forEach(addButton);
})();
