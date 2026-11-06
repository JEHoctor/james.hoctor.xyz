/*
 * Adds a "Copy" button to every code block. Progressive enhancement: without JavaScript the
 * blocks render exactly as before.
 *
 * Pandoc wraps highlighted blocks in div.sourceCode and leaves plain fences as a bare <pre>,
 * so the button is attached to the wrapper when there is one and to a new wrapper otherwise.
 * The button goes above the code, in its own strip, so it never covers a long line. The text
 * is read from the DOM at click time, so anything a script rewrote after page load (for
 * example Cloudflare's email decoding) is copied as the reader sees it.
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

  function addButton(pre, index, total) {
    var code = pre.querySelector("code") || pre;
    var container = containerFor(pre);
    container.classList.add("has-copy");

    // Every button needs a distinct name, or a screen reader says the same thing N times. It
    // starts with the visible word "Copy", as accessibility guidelines ask.
    var position = total > 1 ? " " + (index + 1) + " of " + total : "";
    var idleName = "Copy code block" + position;
    var doneName = "Copied code block" + position;

    var button = document.createElement("button");
    button.type = "button";
    button.className = "copy-code";
    button.textContent = "Copy";
    button.setAttribute("aria-label", idleName);

    var status = document.createElement("span");
    status.className = "copy-code-status";
    status.setAttribute("role", "status");

    var timer;
    function show(label, state, message, name) {
      button.textContent = label;
      button.dataset.state = state;
      button.setAttribute("aria-label", name);
      status.textContent = message;
      clearTimeout(timer);
      timer = setTimeout(function () {
        button.textContent = "Copy";
        delete button.dataset.state;
        button.setAttribute("aria-label", idleName);
        status.textContent = "";
      }, RESET_MS);
    }

    button.addEventListener("click", function () {
      var text = code.textContent.replace(/\n$/, "");
      navigator.clipboard.writeText(text).then(
        function () {
          show("Copied", "done", "Copied to clipboard", doneName);
        },
        function () {
          show(
            "Failed",
            "error",
            "Copy failed. Select the text and copy it by hand.",
            idleName,
          );
        },
      );
    });

    container.insertBefore(button, container.firstChild);
    container.appendChild(status);
  }

  var blocks = document.querySelectorAll("pre");
  blocks.forEach(function (pre, index) {
    addButton(pre, index, blocks.length);
  });
})();
