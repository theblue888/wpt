CONTENT = b"""
<!doctype html>
<script src="/common/PrefixedLocalStorage.js"></script>
<script src="helper.sub.js"></script>
<script>

startRecordingEvents(['visibilitychange', 'pagehide', 'pageshow', 'load']);

runTest(
  () => {
    %s
    location.href = backUrl;
  },
  (isBFCached, observedEvents) => {
    prefixedLocalStorage.setItem(
      'result',
      JSON.stringify({isBFCached, observedEvents}));
  });
</script>
"""

def main(request, response):
    response.status = (200, b"OK")
    response.headers.set(b"Content-Type", b"text/html")
    return CONTENT % request.GET.first(b"script", b"")
