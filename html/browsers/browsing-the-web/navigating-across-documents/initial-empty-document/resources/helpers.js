const url_204 = "/common/blank.html?pipe=status(204)";

window.waitForLoad = (t, iframe, urlRelativeToThisDocument) => {
  return new Promise(resolve => {
    iframe.addEventListener("load", t.step_func(() => {
      assert_equals(iframe.contentWindow.location.href, (new URL(urlRelativeToThisDocument, location.href)).href);

      // Wait a bit longer to ensure all history stuff has settled, e.g. the document is "completely loaded"
      // (which happens from a queued task).
      setTimeout(resolve, 0);
    }), { once: true });
  });
};

window.waitForMessage = (t, message) => {
  return new Promise(resolve => {
    window.addEventListener("message", t.step_func((event) => {
      if (event.data == message)
        resolve();
    }));
  });
};

window.insertIframe = (t) => {
  const iframe = document.createElement("iframe");
  t.add_cleanup(() => iframe.remove());
  document.body.append(iframe);
  return iframe;
};

window.insertIframeWith204Src = (t) => {
  const iframe = document.createElement("iframe");
  iframe.src = url_204;
  t.add_cleanup(() => iframe.remove());
  document.body.append(iframe);
  return iframe;
};

window.insertIframeWithAboutBlankSrc = (t) => {
  const iframe = document.createElement("iframe");
  t.add_cleanup(() => iframe.remove());
  iframe.src = "about:blank";
  document.body.append(iframe);
  return iframe;
};

window.insertIframeWithAboutBlankSrcWaitForLoad = async (t) => {
  const iframe = insertIframeWithAboutBlankSrc(t);
  const aboutBlankLoad = new Promise(resolve => {
    if (iframe.contentDocument.readyState === 'complete') {
      // Wait a bit longer in case the about:blank navigation after the
      // initial empty document is asynchronous.
      t.step_timeout(resolve, 100);
    }
    iframe.onload = () => {
      // Wait a bit longer in case the about:blank navigation after the
      // initial empty document is asynchronous.
      t.step_timeout(resolve, 100);
    };
  });
  await aboutBlankLoad;
  return iframe;
};

window.waitForOpenedWindowLoad = async (t, openedWindow) => {
  return new Promise(resolve => {
    if (openedWindow.document.readyState === 'complete') {
      // Wait a bit longer in case the about:blank navigation after the
      // initial empty document is asynchronous.
      t.step_timeout(resolve, 100);
    }
    openedWindow.onload = () => {
      // Wait a bit longer in case the about:blank navigation after the
      // initial empty document is asynchronous.
      t.step_timeout(resolve, 100);
    };
  });
}

window.windowOpenAboutBlank = (t) => {
  const openedWindow = window.open("about:blank");
  t.add_cleanup(() => openedWindow.close());
  return openedWindow;
};

window.windowOpen204 = async (t) => {
  const openedWindow = window.open(url_204);
  await waitForOpenedWindowLoad(t, openedWindow);
  t.add_cleanup(() => openedWindow.close());
  return openedWindow;
};

window.windowOpenNoURL = async (t) => {
  const openedWindow = window.open();
  await waitForOpenedWindowLoad(t, openedWindow);
  t.add_cleanup(() => openedWindow.close());
  return openedWindow;
};

window.windowOpenAboutBlankWaitForLoad = async (t) => {
  const openedWindow = window.windowOpenAboutBlank(t);
  await waitForOpenedWindowLoad(t, openedWindow);
  return openedWindow;
};
