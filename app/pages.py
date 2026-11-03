"""The technical HTML pages the old framework rendered while DEBUG was on."""

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta http-equiv="content-type" content="text/html; charset=utf-8">
  <title>{title}</title>
  <meta name="robots" content="NONE,NOARCHIVE">
</head>
<body>
  <div id="summary">
    <h1>{heading} <span>({status})</span></h1>
    <table class="meta">
      <tr><th>Request Method:</th><td>{method}</td></tr>
      <tr><th>Request URL:</th><td>{url}</td></tr>
    </table>
  </div>
  <div id="explanation"><p>{explanation}</p></div>
</body>
</html>
"""


def not_found_page(method, url):
    return _TEMPLATE.format(
        title='Page not found at %s' % url, heading='Page not found', status=404,
        method=method, url=url,
        explanation='You are seeing this error because DEBUG is on.')


def bad_request_page(method, url, name='DisallowedHost'):
    return _TEMPLATE.format(
        title='%s at %s' % (name, url), heading=name, status=400, method=method, url=url,
        explanation='You are seeing this error because DEBUG is on.')


def server_error_page(method, url, name='Exception'):
    return _TEMPLATE.format(
        title='%s at %s' % (name, url), heading='Server Error', status=500,
        method=method, url=url,
        explanation='You are seeing this error because DEBUG is on.')
