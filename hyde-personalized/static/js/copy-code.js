/*
 * Adds a copy button to every code block. Progressive enhancement: without JavaScript the
 * blocks render exactly as before.
 *
 * Pandoc wraps highlighted blocks in div.sourceCode and leaves plain fences as a bare <pre>,
 * so the button is attached to the wrapper when there is one and to a new wrapper otherwise.
 * The button is an icon (Fork Awesome, already loaded for the sidebar) positioned inside the
 * block's own padding. The text is read from the DOM at click time, so anything a script
 * rewrote after page load (for example Cloudflare's email decoding) is copied as the reader
 * sees it.
 */
(function () {
  "use strict";

  if (!navigator.clipboard || !navigator.clipboard.writeText) {
    return;
  }

  var RESET_MS = 1800;
  // fa-files-o is the outlined "copy" icon, lighter than the solid fa-clipboard.
  var ICONS = { idle: "fa-files-o", done: "fa-check", error: "fa-times" };

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
    // starts with the word "Copy", as accessibility guidelines ask of an icon's name.
    var position = total > 1 ? " " + (index + 1) + " of " + total : "";
    var idleName = "Copy code block" + position;
    var doneName = "Copied code block" + position;

    var icon = document.createElement("i");
    icon.className = "fa " + ICONS.idle;
    icon.setAttribute("aria-hidden", "true");

    var button = document.createElement("button");
    button.type = "button";
    button.className = "copy-code";
    button.title = "Copy";
    button.setAttribute("aria-label", idleName);
    button.appendChild(icon);

    var status = document.createElement("span");
    status.className = "copy-code-status";
    status.setAttribute("role", "status");

    var timer;
    function show(state, message, name) {
      icon.className = "fa " + ICONS[state];
      if (state === "idle") {
        delete button.dataset.state;
      } else {
        button.dataset.state = state;
      }
      button.setAttribute("aria-label", name);
      status.textContent = message;
      clearTimeout(timer);
      if (state !== "idle") {
        timer = setTimeout(function () {
          show("idle", "", idleName);
        }, RESET_MS);
      }
    }

    button.addEventListener("click", function () {
      var text = code.textContent.replace(/\n$/, "");
      navigator.clipboard.writeText(text).then(
        function () {
          show("done", "Copied to clipboard", doneName);
        },
        function () {
          show("error", "Copy failed. Select the text and copy it by hand.", idleName);
        },
      );
    });

    // A strip behind the button that fades a long line out instead of cutting it off.
    var fade = document.createElement("span");
    fade.className = "copy-code-fade";
    fade.setAttribute("aria-hidden", "true");

    container.appendChild(fade);
    container.appendChild(button);
    container.appendChild(status);
  }

  var blocks = document.querySelectorAll("pre");
  blocks.forEach(function (pre, index) {
    addButton(pre, index, blocks.length);
  });
})();
